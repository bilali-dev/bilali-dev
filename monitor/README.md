# monitor/ — Monitor de vagas da VFS Global

`vfs_monitor.py` verifica periodicamente se ha vagas de agendamento
disponiveis no portal da VFS Global e avisa voce no Telegram assim que
encontrar uma.

**O que este script faz:**
- Faz login com as suas proprias credenciais.
- Verifica a pagina de agendamento em busca de vagas.
- Envia uma mensagem no Telegram com um link quando encontra algo.

**O que ele NAO faz (de proposito):**
- Nao preenche nem confirma o agendamento automaticamente.
- Nao tenta resolver ou contornar captcha — se um captcha aparecer, o
  script para e apenas te avisa para resolver manualmente.

Isso existe porque os Termos de Uso da VFS Global proibem bots que
automatizem o agendamento em si, e o proprio site usa captcha e
rate-limiting para impedir isso. O monitor te da a vantagem de
velocidade (ser avisado na hora) sem cruzar essa linha — voce sempre
finaliza o agendamento manualmente.

## Configuracao

1. Instale as dependencias e os navegadores do Playwright (veja o
   [README principal](../README.md)):

   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. Preencha em `.env`: `TELEGRAM_CHAT_ID`, `VFS_EMAIL`, `VFS_PASSWORD`,
   `VFS_LOGIN_URL` e `VFS_APPOINTMENT_URL` (especificos do seu
   pais/missao — veja os comentarios em `.env.example`).

3. **Ajuste os seletores CSS** em `monitor/config.py`
   (`email_selector`, `password_selector`, `login_button_selector`,
   `no_slots_text`, `slot_selector`). Os valores incluidos sao apenas
   um ponto de partida generico — inspecione a pagina real do seu
   pais (botao direito -> Inspecionar) para obter os seletores
   corretos, pois cada missao da VFS tem uma pagina diferente.

4. Rode o monitor:

   ```bash
   python -m monitor.vfs_monitor
   ```

## Uso responsavel

- Use apenas para o seu proprio agendamento (ou de familiares
  diretos) — nunca para revenda ou uso comercial de vagas.
- Mantenha o intervalo de checagem (`VFS_CHECK_INTERVAL_MINUTES`) em
  10 minutos ou mais para nao sobrecarregar o site nem arriscar
  bloqueio da sua conta/IP.
- Nunca compartilhe seu arquivo `.env` — ele contem sua senha da VFS
  Global e o token do bot.
