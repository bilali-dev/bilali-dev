"""
Monitor de vagas no portal da VFS Global.

Este script NAO realiza agendamento automatico e NAO tenta contornar
captcha ou qualquer outra protecao anti-bot do site. Ele apenas:

  1. Faz login com as SUAS proprias credenciais.
  2. Abre a pagina de agendamento configurada.
  3. Verifica se ha vagas visiveis.
  4. Se encontrar, envia um alerta no Telegram com um link para voce
     finalizar o agendamento manualmente (resolvendo o captcha voce
     mesmo, dentro do prazo).
  5. Se um captcha aparecer durante a checagem, o script para o ciclo
     atual e apenas avisa que ha um captcha pendente para voce resolver
     manualmente -- ele nunca tenta resolve-lo.

IMPORTANTE:
  - Use isso apenas para o seu proprio agendamento (ou de familiares
    diretos), nunca para revenda ou uso comercial de vagas.
  - Respeite um intervalo de checagem razoavel (recomendado: >= 10
    minutos) para nao sobrecarregar o site nem arriscar bloqueio da
    sua conta/IP.
  - Os seletores CSS abaixo sao um ponto de partida generico. Cada
    pais/missao da VFS Global tem uma pagina diferente -- inspecione o
    site real (botao direito -> Inspecionar) e ajuste
    bot/monitor/config.py antes de usar.
"""

import asyncio
import logging

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError, async_playwright
from telegram import Bot

from monitor.config import VfsConfig, load_config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


class CaptchaDetected(Exception):
    pass


async def login(page: Page, config: VfsConfig) -> None:
    await page.goto(config.login_url)
    await page.fill(config.email_selector, config.email)
    await page.fill(config.password_selector, config.password)

    if await page.locator("iframe[src*='captcha']").count() > 0:
        raise CaptchaDetected("Captcha detectado na tela de login.")

    await page.click(config.login_button_selector)
    await page.wait_for_load_state("networkidle")


async def check_for_slots(page: Page, config: VfsConfig) -> list[str]:
    await page.goto(config.appointment_url)
    await page.wait_for_load_state("networkidle")

    if await page.locator("iframe[src*='captcha']").count() > 0:
        raise CaptchaDetected("Captcha detectado na pagina de agendamento.")

    page_text = await page.content()
    if config.no_slots_text.lower() in page_text.lower():
        return []

    slots = page.locator(config.slot_selector)
    count = await slots.count()
    results = []
    for i in range(count):
        text = await slots.nth(i).inner_text()
        results.append(text.strip())
    return results


async def send_telegram_message(config: VfsConfig, text: str) -> None:
    bot = Bot(token=config.telegram_bot_token)
    await bot.send_message(chat_id=config.telegram_chat_id, text=text)


async def run_once(config: VfsConfig) -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await login(page, config)
            slots = await check_for_slots(page, config)

            if slots:
                message = (
                    "Vaga(s) encontrada(s) na VFS Global!\n\n"
                    + "\n".join(f"- {slot}" for slot in slots)
                    + f"\n\nAcesse agora para finalizar o agendamento:\n{config.appointment_url}"
                )
                logger.info("Vagas encontradas: %s", slots)
                await send_telegram_message(config, message)
            else:
                logger.info("Nenhuma vaga disponivel neste momento.")

        except CaptchaDetected as exc:
            logger.warning("Captcha detectado, parando este ciclo: %s", exc)
            await send_telegram_message(
                config,
                "Captcha detectado no site da VFS Global. "
                "Acesse manualmente para verificar e resolver: " + config.appointment_url,
            )
        except PlaywrightTimeoutError as exc:
            logger.error("Timeout ao acessar o site da VFS Global: %s", exc)
        finally:
            await browser.close()


async def monitor_loop(config: VfsConfig) -> None:
    interval_seconds = config.check_interval_minutes * 60
    logger.info(
        "Monitor iniciado. Verificando a cada %s minutos. Pressione Ctrl+C para parar.",
        config.check_interval_minutes,
    )
    while True:
        try:
            await run_once(config)
        except Exception:
            logger.exception("Erro inesperado durante a checagem.")
        await asyncio.sleep(interval_seconds)


def main() -> None:
    config = load_config()
    asyncio.run(monitor_loop(config))


if __name__ == "__main__":
    main()
