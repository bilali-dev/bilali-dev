# Marketplace Seller API

SaaS completo que transforma a página de produto de um marketplace em dados
estruturados sobre o produto e o vendedor. A primeira integração cobre a
ERLI; a arquitetura foi pensada para adicionar outros marketplaces através de
novos adaptadores.

Fluxo de extração:

```text
uma página HTML guardada ou uma URL real -> um parser testado -> um resultado JSON correto
```

Por cima desse fluxo, o projeto inclui a camada comercial completa (etapas
11 e 12 do guia de desenvolvimento): contas e chaves de API, cotas por
plano, monitorização de produtos com webhooks e cobrança via Stripe.

## Estrutura

```text
market-seller-api/
├── app/
│   ├── main.py               # app FastAPI, middleware e routers
│   ├── cli.py                 # interface de linha de comando (uso local, sem SaaS)
│   ├── config.py              # configuração via variáveis de ambiente
│   ├── errors.py              # exceções do domínio de extração
│   ├── models.py              # modelos Pydantic do resultado de extração
│   ├── db.py                  # engine/sessão SQLModel
│   ├── db_models.py           # tabelas: Customer, ApiKey, Monitor, MonitorEvent, UsageEvent
│   ├── auth.py                 # autenticação por API key (hash + prefixo)
│   ├── plans.py                 # planos, limites e contagem de uso mensal
│   ├── rate_limit.py             # limite de requisições por chave (em memória)
│   ├── worker.py                  # processo separado que executa os monitores vencidos
│   ├── adapters/
│   │   ├── base.py             # contrato MarketplaceAdapter
│   │   └── erli.py             # adaptador da ERLI
│   ├── services/
│   │   ├── fetcher.py          # download de HTML
│   │   ├── extractor.py        # coordenação do fluxo de extração
│   │   ├── export.py           # exportação JSON/CSV (CLI)
│   │   ├── webhooks.py         # assinatura HMAC e envio de webhooks
│   │   └── monitor_runner.py   # comparação de resultados e geração de eventos
│   └── routers/
│       ├── signup.py           # POST /v1/signup
│       ├── extract.py          # POST /v1/extract (autenticado, com cota)
│       ├── usage.py            # GET /v1/usage
│       ├── monitors.py         # CRUD de monitores
│       └── billing.py          # checkout e webhook do Stripe
├── scripts/save_page.py       # baixa uma página real para estudo local
├── tests/                     # testes automatizados (sem depender de rede/Stripe reais)
├── docker-compose.yml         # api + worker + Postgres
└── output/                    # resultados exportados pela CLI (ignorado pelo Git)
```

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
cp .env.example .env             # ajuste os valores conforme necessário
```

Por padrão a aplicação usa SQLite (`DATABASE_URL=sqlite:///./market_seller_api.db`),
suficiente para desenvolvimento local e para os testes. Em produção, aponte
`DATABASE_URL` para PostgreSQL (veja `docker-compose.yml`).

## Testes

```bash
pytest -q
```

Os testes usam um banco SQLite isolado (`tests/conftest.py`) e não dependem
de rede nem de credenciais reais do Stripe.

## Uso pela linha de comando (sem camada SaaS)

Extração local, sem internet, usando a fixture de exemplo:

```bash
python -m app.cli \
  --url "https://erli.pl/produkt/demo,123" \
  --file tests/fixtures/erli_product_sample.html
```

Extração de uma URL real:

```bash
python -m app.cli --url "https://erli.pl/produkt/exemplo"
```

Lote pequeno de URLs com exportação CSV:

```bash
python -m app.cli --urls-file urls.txt --csv-output output/resultados.csv
```

## API REST (SaaS)

```bash
uvicorn app.main:app --reload
```

Documentação interativa em `http://127.0.0.1:8000/docs`.

### 1. Criar uma conta e obter uma chave de API

```bash
curl -X POST http://127.0.0.1:8000/v1/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"cliente@example.com"}'
```

A resposta traz `api_key` uma única vez (`sk_live_...`). Apenas o hash é
guardado no servidor — se a chave for perdida, é preciso gerar outra conta ou
(numa evolução futura) um endpoint de rotação de chaves.

### 2. Extrair dados de um produto

```bash
curl -X POST http://127.0.0.1:8000/v1/extract \
  -H "Authorization: Bearer sk_live_..." \
  -H "Content-Type: application/json" \
  -d '{"url":"https://erli.pl/produkt/exemplo"}'
```

| Código | Significado |
|---|---|
| 200 | extração concluída |
| 400 | marketplace não suportado ou URL com esquema inválido |
| 401 | chave de API ausente ou inválida |
| 402 | cota mensal do plano esgotada |
| 422 | corpo da requisição não respeita o modelo |
| 429 | limite de requisições por minuto excedido |
| 502 | falha ao obter ou interpretar a página do marketplace |

### 3. Consultar uso do mês

```bash
curl http://127.0.0.1:8000/v1/usage -H "Authorization: Bearer sk_live_..."
```

### 4. Monitorizar um produto (planos Starter/Pro)

```bash
curl -X POST http://127.0.0.1:8000/v1/monitors \
  -H "Authorization: Bearer sk_live_..." \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://erli.pl/produkt/exemplo",
    "frequency_minutes": 1440,
    "webhook_url": "https://seu-servidor.com/webhooks/marketplace"
  }'
```

O `app/worker.py` roda em processo separado, procura monitores vencidos,
compara o resultado novo com o anterior (preço, disponibilidade, avaliação,
número de opiniões, nome do vendedor) e envia um webhook assinado por
`WEBHOOK_SECRET` (cabeçalho `X-Signature-256`, HMAC-SHA256) para cada campo
alterado. `GET/DELETE /v1/monitors/{id}` e `GET /v1/monitors` completam o CRUD.

### 5. Planos

| Plano | Resultados/mês | Monitores | Frequência mínima |
|---|---:|---:|---|
| Free | 50 | 0 | — |
| Starter | 1.000 | 10 | diária (1440 min) |
| Pro | 10.000 | 100 | horária (60 min) |

Novas contas começam no plano `free`. A mudança de plano é feita pelo fluxo
de cobrança (Stripe) descrito abaixo, ou manualmente no banco de dados
durante a fase de validação comercial.

### 6. Cobrança (Stripe)

Os endpoints `POST /v1/billing/checkout` e `POST /v1/billing/webhook` ficam
inativos (HTTP 501) até que `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` e
os preços (`STRIPE_PRICE_STARTER`, `STRIPE_PRICE_PRO`) sejam configurados.
Isso permite rodar a API e a monitorização sem depender de uma conta Stripe
real durante o desenvolvimento.

```bash
curl -X POST http://127.0.0.1:8000/v1/billing/checkout \
  -H "Authorization: Bearer sk_live_..." \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "starter",
    "success_url": "https://seu-site.com/sucesso",
    "cancel_url": "https://seu-site.com/cancelado"
  }'
```

O webhook (`checkout.session.completed`, `customer.subscription.deleted`)
atualiza o plano do cliente no banco de dados.

## Segurança e limites aplicados

- URLs restritas a `http`/`https` e a domínios suportados pelos adaptadores
  (mitiga SSRF: o servidor nunca busca uma URL arbitrária).
- Tamanho do corpo da requisição limitado por `MAX_BODY_SIZE_BYTES`.
- Chaves de API nunca são guardadas em texto simples (apenas hash + prefixo).
- Limite de requisições por minuto por cliente (`RATE_LIMIT_PER_MINUTE`),
  em memória — para múltiplas instâncias, substitua por um limitador
  centralizado (ex.: Redis).
- Contentor Docker executa com utilizador não privilegiado.

## Docker

```bash
docker build -t market-seller-api .
docker run --rm -p 8000:8000 market-seller-api
```

## Docker Compose (API + worker + PostgreSQL)

```bash
docker compose up --build
```

Sobe três serviços: `db` (PostgreSQL), `api` (`uvicorn`, porta 8000) e
`worker` (`python -m app.worker`, processa monitores vencidos). Configure
`WEBHOOK_SECRET` e as variáveis `STRIPE_*` num `.env` na raiz do projeto
antes de subir em produção.

## Aviso legal

Antes de usar em produção, confirme os termos de utilização do marketplace,
diretivas robots, licitude do tratamento de dados pessoais/empresariais e a
finalidade legítima da recolha. Não contorne autenticação, CAPTCHA ou
controlos de acesso.
