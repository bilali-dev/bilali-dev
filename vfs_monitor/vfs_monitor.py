"""
VFS Global - Monitor de disponibilidade de vagas (SEM marcação automática)

O que este script FAZ:
  - Faz login no portal VFS Global usando as credenciais fornecidas em .env
  - Navega até à página de seleção de categoria de visto e verifica se existem
    vagas/datas disponíveis para marcação
  - Envia um alerta via Telegram quando deteta que há vagas disponíveis

O que este script NÃO faz (de propósito):
  - Não clica em "Continuar" para avançar na marcação
  - Não faz upload de passaporte nem preenche dados pessoais
  - Não usa modos de evasão de deteção de bots (undetected-chromedriver / uc mode)
  - Não marca nem confirma nenhuma consulta sozinho

Ajusta a secção CONFIG e os seletores em `verificar_disponibilidade()` depois
de inspecionares a página real no teu browser (DevTools -> Inspecionar),
porque a estrutura exata do DOM do portal pode mudar.
"""

import logging
import os
import random
import sys
import time
from datetime import datetime

import requests
from dotenv import load_dotenv
from selenium.webdriver.common.by import By

load_dotenv()

# ===================== CONFIG =====================

VFS_URL = os.getenv("VFS_URL", "https://visa.vfsglobal.com/gnb/pt/prt/login")
VFS_EMAIL = os.getenv("VFS_EMAIL")
VFS_PASSWORD = os.getenv("VFS_PASSWORD")

# Lista de categorias de visto nacional a monitorizar, separadas por vírgula.
# O texto de cada categoria tem de corresponder (parcialmente) ao que aparece
# na dropdown de categorias do portal.
VISA_CATEGORY_TEXTS = [
    c.strip()
    for c in os.getenv("VISA_CATEGORY_TEXTS", "tratamento médico,estudo").split(",")
    if c.strip()
]

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Intervalo entre verificações. Mantém um valor razoável (mínimo 3 min) para
# não sobrecarregar o servidor do VFS nem parecer tráfego abusivo.
CHECK_INTERVAL_SECONDS = max(int(os.getenv("CHECK_INTERVAL_SECONDS", "300")), 180)

# Depois de um alerta, espera este tempo antes de poder alertar outra vez
# (evita spam de mensagens enquanto o estado se mantém "disponível").
ALERT_COOLDOWN_SECONDS = int(os.getenv("ALERT_COOLDOWN_SECONDS", "1800"))

HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"

PROFILE_DIR = os.path.abspath("vfs_monitor_profile")
LOG_FILE = os.path.abspath("vfs_monitor.log")

# Frases que indicam que NÃO há vagas (em PT e EN). Ajusta conforme o texto
# real que vires na página.
FRASES_INDISPONIVEL = [
    "no appointment slots are available",
    "não há vagas",
    "nenhuma vaga disponível",
    "sem vagas disponíveis",
    "no slots available",
    "não existem vagas",
]

# ===================== LOGGING =====================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("vfs_monitor")


def validar_config():
    faltam = []
    if not VFS_EMAIL:
        faltam.append("VFS_EMAIL")
    if not VFS_PASSWORD:
        faltam.append("VFS_PASSWORD")
    if not TELEGRAM_BOT_TOKEN:
        faltam.append("TELEGRAM_BOT_TOKEN")
    if not TELEGRAM_CHAT_ID:
        faltam.append("TELEGRAM_CHAT_ID")
    if faltam:
        log.error("Faltam variáveis no .env: %s (ver .env.example)", ", ".join(faltam))
        sys.exit(1)


def delay(min_s=2.0, max_s=4.5):
    time.sleep(random.uniform(min_s, max_s))


def enviar_alerta_telegram(mensagem: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": mensagem}, timeout=15)
        resp.raise_for_status()
        log.info("Alerta enviado via Telegram.")
    except requests.RequestException as exc:
        log.error("Falha ao enviar alerta Telegram: %s", exc)


def criar_driver():
    from seleniumbase import Driver

    # uc=False (padrão): sem modo de evasão de deteção de bots.
    return Driver(headless=HEADLESS, user_data_dir=PROFILE_DIR)


def esta_na_pagina_login(driver) -> bool:
    return "login" in driver.get_current_url().lower()


def fazer_login(driver) -> bool:
    log.info("A tentar fazer login...")
    driver.get(VFS_URL)
    delay(3, 5)

    if not esta_na_pagina_login(driver):
        log.info("Sessão já ativa (perfil persistente).")
        return True

    try:
        campo_email = driver.find_element(By.CSS_SELECTOR, "input[type='email'], input[formcontrolname*='email' i]")
        campo_email.clear()
        campo_email.send_keys(VFS_EMAIL)
        delay(1, 2)

        campo_pass = driver.find_element(By.CSS_SELECTOR, "input[type='password']")
        campo_pass.clear()
        campo_pass.send_keys(VFS_PASSWORD)
        delay(1, 2)

        driver.execute_script("""
            var btns = document.querySelectorAll('button');
            for (var b of btns) {
                var t = b.innerText.toLowerCase();
                if (t.includes('login') || t.includes('entrar') || t.includes('iniciar sess')) {
                    b.click();
                    return;
                }
            }
        """)
        delay(5, 8)
    except Exception as exc:
        log.error("Não foi possível preencher o formulário de login: %s", exc)
        return False

    if esta_na_pagina_login(driver):
        log.warning(
            "Ainda na página de login após submeter (pode haver CAPTCHA ou credenciais "
            "inválidas). Verifica manualmente."
        )
        return False

    log.info("Login efetuado com sucesso.")
    return True


def verificar_disponibilidade(driver, categoria_texto: str) -> tuple[bool, str]:
    """
    Navega até à seleção de uma categoria de visto nacional específica e
    verifica o texto da página. Devolve (disponivel: bool, detalhe: str).
    NÃO avança além desta verificação (não clica em "Continuar").
    """
    driver.get(VFS_URL)
    delay(3, 5)

    driver.execute_script("""
        var elementos = document.querySelectorAll('button, a, div, span');
        for (var i = 0; i < elementos.length; i++) {
            var txt = elementos[i].innerText.toLowerCase().trim();
            if (txt.includes('iniciar nova reserva')) {
                elementos[i].click();
                return;
            }
        }
    """)
    delay(3, 5)

    driver.execute_script("""
        var els = document.querySelectorAll('mat-select, .ng-select-container, div[role="combobox"], span');
        for (var e of els) {
            var t = e.innerText.toLowerCase();
            if (t.includes('selecione') || t.includes('categoria')) {
                e.click();
                break;
            }
        }
    """)
    delay(2, 3)

    categoria_encontrada = driver.execute_script("""
        var alvo = arguments[0];
        var ops = document.querySelectorAll('mat-option, .ng-option, li, span');
        for (var o of ops) {
            if (o.innerText.trim().toLowerCase().includes(alvo)) {
                o.click();
                return true;
            }
        }
        return false;
    """, categoria_texto.lower())
    delay(2, 4)

    if not categoria_encontrada:
        return False, f"Categoria '{categoria_texto}' não encontrada na dropdown (ajusta VISA_CATEGORY_TEXTS)"

    texto_pagina = driver.execute_script("return document.body.innerText.toLowerCase();") or ""

    for frase in FRASES_INDISPONIVEL:
        if frase in texto_pagina:
            return False, f"Indisponível (encontrado: '{frase}')"

    return True, "Nenhuma frase de indisponibilidade encontrada — possíveis vagas!"


def executar():
    validar_config()
    log.info(
        "Bot de monitorização VFS iniciado. Categorias: %s | Intervalo: %ss",
        ", ".join(VISA_CATEGORY_TEXTS),
        CHECK_INTERVAL_SECONDS,
    )

    ultimo_alerta_ts = {categoria: 0.0 for categoria in VISA_CATEGORY_TEXTS}

    while True:
        driver = None
        try:
            driver = criar_driver()

            if not fazer_login(driver):
                log.error("Login falhou nesta tentativa. A tentar novamente no próximo ciclo.")
            else:
                for categoria in VISA_CATEGORY_TEXTS:
                    disponivel, detalhe = verificar_disponibilidade(driver, categoria)
                    log.info("[%s] Resultado da verificação: %s", categoria, detalhe)

                    if disponivel:
                        agora = time.time()
                        if agora - ultimo_alerta_ts[categoria] >= ALERT_COOLDOWN_SECONDS:
                            mensagem = (
                                f"🎉 Possível vaga disponível para visto nacional de '{categoria}' "
                                f"no VFS Global!\nDetetado às {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}.\n"
                                "Vai ao portal e marca manualmente: " + VFS_URL
                            )
                            enviar_alerta_telegram(mensagem)
                            ultimo_alerta_ts[categoria] = agora
                        else:
                            log.info(
                                "[%s] Vaga ainda detetada, mas dentro do cooldown de alerta — sem novo envio.",
                                categoria,
                            )

                    delay(2, 4)

        except Exception as exc:
            log.error("Erro durante o ciclo de verificação: %s", exc)
        finally:
            if driver is not None:
                driver.quit()

        espera = CHECK_INTERVAL_SECONDS + random.uniform(0, 30)
        log.info("Próxima verificação em ~%.0fs.", espera)
        time.sleep(espera)


if __name__ == "__main__":
    try:
        executar()
    except KeyboardInterrupt:
        log.info("Bot interrompido pelo utilizador.")
