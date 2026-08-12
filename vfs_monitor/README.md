# VFS Monitor — Bot de monitorização e alerta

Verifica periodicamente se há vagas disponíveis para marcação de **visto
nacional** no portal VFS Global (Guiné-Bissau, `visa.vfsglobal.com/gnb/pt/prt/login`),
para as categorias configuradas em `VISA_CATEGORY_TEXTS` — por omissão,
**visto de tratamento médico** e **visto de estudo** — e envia um alerta via
Telegram para cada categoria com vagas. Este bot **não** avança a marcação,
**não** faz upload de documentos e **não** submete nenhum formulário —
apenas lê o estado da página, categoria a categoria.

## Instalação

```bash
cd vfs_monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edita o `.env` com as tuas credenciais VFS e os dados do teu bot Telegram.

## Como criar o bot do Telegram

1. Fala com [@BotFather](https://t.me/BotFather) no Telegram, envia `/newbot`
   e segue as instruções. Vais receber um `TELEGRAM_BOT_TOKEN`.
2. Envia qualquer mensagem ao teu novo bot.
3. Abre `https://api.telegram.org/bot<TOKEN>/getUpdates` no browser e
   procura o campo `"chat":{"id": ...}` — esse número é o `TELEGRAM_CHAT_ID`.

## Executar localmente (contínuo)

```bash
python vfs_monitor.py
```

O script corre em ciclo (mínimo 3 minutos entre verificações, configurável em
`CHECK_INTERVAL_SECONDS`), regista tudo em `vfs_monitor.log` e envia um alerta
Telegram sempre que deteta que já não há a mensagem de "sem vagas" — mas
nunca mais do que uma vez a cada `ALERT_COOLDOWN_SECONDS`. O estado dos
cooldowns fica em `state.json`.

## Correr na nuvem (GitHub Actions) — não depende do teu computador estar ligado

Já existe um workflow em `.github/workflows/vfs_monitor.yml` que corre uma
verificação (`python vfs_monitor.py --once`) de 15 em 15 minutos, 24/7,
incluindo de madrugada, sem precisares de deixar nada aberto localmente.

### 1. Configurar segredos (dados sensíveis)

No repositório GitHub: **Settings → Secrets and variables → Actions → Secrets**,
cria:

| Nome | Valor |
|---|---|
| `VFS_EMAIL` | o teu email de login VFS |
| `VFS_PASSWORD` | a tua password VFS |
| `TELEGRAM_BOT_TOKEN` | token do bot Telegram |
| `TELEGRAM_CHAT_ID` | o teu chat id do Telegram |

### 2. Configurar variáveis (dados não sensíveis, opcional)

Na mesma página, separador **Variables**, podes opcionalmente definir:

| Nome | Exemplo | Default se não definires |
|---|---|---|
| `VFS_URL` | `https://visa.vfsglobal.com/gnb/pt/prt/login` | já é este o valor por omissão |
| `VISA_CATEGORY_TEXTS` | `tratamento médico,estudo` | já é este o valor por omissão |
| `ALERT_COOLDOWN_SECONDS` | `1800` | 1800 (30 min) |

### 3. Ativar

O workflow já corre automaticamente por agendamento assim que estiver na
branch principal (`main`). Podes testar manualmente em **Actions → VFS Visa
Monitor → Run workflow**, e ver os logs de cada execução aí.

### Notas sobre o modo cloud

- Cada execução é um browser novo (sem sessão persistente) — por isso faz
  sempre login com email/password. O `state.json` (cooldown de alertas) é
  atualizado e enviado de volta (`git push`) pelo próprio workflow no fim de
  cada execução.
- O GitHub **desativa automaticamente workflows agendados após 60 dias sem
  atividade no repositório** — se isso acontecer, volta a ativar manualmente
  em Actions, ou faz um commit qualquer no repositório de vez em quando.
- Repositórios de perfil (`utilizador/utilizador`) têm de ser públicos, o que
  dá minutos de Actions gratuitos e ilimitados nos runners padrão. Se algum
  dia tornares o repo privado, verifica o limite gratuito de minutos/mês.

## Importante

- Ajusta os seletores em `verificar_disponibilidade()` depois de inspecionar
  a página real (DevTools do browser), pois a estrutura do portal pode mudar.
- Mantém o intervalo de verificação razoável — verificações demasiado
  frequentes podem sobrecarregar o servidor ou ser tratadas como abuso.
- Assim que receberes o alerta, vais tu manualmente ao portal completar a
  marcação (upload de passaporte, dados pessoais, etc.).
