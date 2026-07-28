# Bot de Telegram

Estrutura inicial de um bot em Python usando [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot).

## Como usar

1. Crie um bot com o [@BotFather](https://t.me/BotFather) no Telegram e copie o token gerado.
2. Instale as dependencias:

   ```bash
   pip install -r requirements.txt
   ```

3. Copie `.env.example` para `.env` e cole seu token:

   ```bash
   cp .env.example .env
   ```

4. Rode o bot:

   ```bash
   python main.py
   ```

## Comandos disponiveis

- `/start` - inicia a conversa
- `/help` - lista os comandos
- `/status` - verifica se o bot esta ativo

Qualquer outra mensagem de texto e repetida de volta (echo), servindo como ponto de partida para novas funcionalidades (integracao com APIs, scraping, agendamento de tarefas, etc.).
