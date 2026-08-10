import os
from dataclasses import dataclass


@dataclass(frozen=True)
class VfsConfig:
    login_url: str
    appointment_url: str
    email: str
    password: str
    check_interval_minutes: int
    telegram_bot_token: str
    telegram_chat_id: str

    # CSS selectors, specific to the VFS portal of your country/mission.
    # You MUST verify these yourself by inspecting the real site
    # (right-click -> Inspect) before running the monitor. Placeholders
    # below are best-effort guesses and are very likely to need adjusting.
    email_selector: str = "input[type='email']"
    password_selector: str = "input[type='password']"
    login_button_selector: str = "button[type='submit']"
    no_slots_text: str = "No appointment slots are available"
    slot_selector: str = ".appointment-slot"


def load_config() -> VfsConfig:
    required = [
        "VFS_LOGIN_URL",
        "VFS_APPOINTMENT_URL",
        "VFS_EMAIL",
        "VFS_PASSWORD",
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(
            "Variaveis de ambiente ausentes: "
            + ", ".join(missing)
            + ". Copie bot/.env.example para bot/.env e preencha os valores."
        )

    return VfsConfig(
        login_url=os.environ["VFS_LOGIN_URL"],
        appointment_url=os.environ["VFS_APPOINTMENT_URL"],
        email=os.environ["VFS_EMAIL"],
        password=os.environ["VFS_PASSWORD"],
        check_interval_minutes=int(os.getenv("VFS_CHECK_INTERVAL_MINUTES", "15")),
        telegram_bot_token=os.environ["TELEGRAM_BOT_TOKEN"],
        telegram_chat_id=os.environ["TELEGRAM_CHAT_ID"],
    )
