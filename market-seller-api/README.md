# Marketplace Seller API

MVP de uma API que transforma a página de produto de um marketplace em dados
estruturados sobre o produto e o vendedor. A primeira integração cobre a
ERLI; a arquitetura foi pensada para adicionar outros marketplaces através de
novos adaptadores.

Fluxo da versão atual:

```text
uma página HTML guardada -> um parser testado -> um resultado JSON correto
```

Banco de dados, pagamentos, dashboard, monitorização e autenticação ficam
para etapas seguintes (ver etapas 11 e 12 do guia de desenvolvimento).

## Estrutura

```text
market-seller-api/
├── app/
│   ├── main.py            # endpoints FastAPI
│   ├── cli.py              # interface de linha de comando
│   ├── config.py           # configuração via variáveis de ambiente
│   ├── errors.py           # exceções do domínio
│   ├── models.py           # modelos Pydantic
│   ├── adapters/
│   │   ├── base.py         # contrato MarketplaceAdapter
│   │   └── erli.py         # adaptador da ERLI
│   └── services/
│       ├── fetcher.py      # download de HTML
│       ├── extractor.py    # coordenação do fluxo
│       └── export.py       # exportação JSON/CSV
├── scripts/save_page.py    # baixa uma página real para estudo local
├── tests/                  # testes automatizados (sem depender de rede)
└── output/                 # resultados exportados (ignorado pelo Git)
```

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

## Testes

```bash
pytest -q
```

## Uso pela linha de comando

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

## API REST

```bash
uvicorn app.main:app --reload
```

- `GET /health` — verifica se o processo está ativo.
- `POST /v1/extract` — recebe `{"url": "..."}` e devolve o `ExtractionResult`.

Documentação interativa em `http://127.0.0.1:8000/docs`.

## Docker

```bash
docker build -t market-seller-api .
docker run --rm -p 8000:8000 market-seller-api
```

## Aviso legal

Antes de usar em produção, confirme os termos de utilização do marketplace,
diretivas robots, licitude do tratamento de dados pessoais/empresariais e a
finalidade legítima da recolha. Não contorne autenticação, CAPTCHA ou
controlos de acesso.
