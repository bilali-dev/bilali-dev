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

## Executar

```bash
python vfs_monitor.py
```

O script corre em ciclo (mínimo 3 minutos entre verificações, configurável em
`CHECK_INTERVAL_SECONDS`), regista tudo em `vfs_monitor.log` e envia um alerta
Telegram sempre que deteta que já não há a mensagem de "sem vagas" — mas
nunca mais do que uma vez a cada `ALERT_COOLDOWN_SECONDS`.

## Importante

- Ajusta os seletores em `verificar_disponibilidade()` depois de inspecionar
  a página real (DevTools do browser), pois a estrutura do portal pode mudar.
- Mantém o intervalo de verificação razoável — verificações demasiado
  frequentes podem sobrecarregar o servidor ou ser tratadas como abuso.
- Assim que receberes o alerta, vais tu manualmente ao portal completar a
  marcação (upload de passaporte, dados pessoais, etc.).
