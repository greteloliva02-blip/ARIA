"""
ARIA — Telegram messaging tool (dispatcher-only execution).
"""
from typing import Awaitable, Callable, Optional

from langchain_core.tools import tool

from core.config import Config
from core.logger import get_logger

logger = get_logger("tools.telegram")

_sender: Optional[Callable[[str, str], Awaitable[None]]] = None


def register_telegram_sender(sender: Callable[[str, str], Awaitable[None]]):
    """Register async sender from TelegramBot.send_message."""
    global _sender
    _sender = sender
    logger.info("Telegram sender registered for dispatcher tool.")


@tool
async def send_telegram_message(message: str, user_id: str = "") -> str:
    """
    Envía un mensaje al usuario por Telegram.
    Usado por automatizaciones como morning_briefing.
    """
    cfg = Config()
    target = (user_id or "").strip() or str(cfg.TELEGRAM_USER_ID or "")
    if not target:
        return "Error: TELEGRAM_USER_ID no configurado."
    if cfg.TELEGRAM_USER_ID and target != str(cfg.TELEGRAM_USER_ID):
        return "Error: destino no autorizado."

    if _sender is None:
        logger.error("Telegram sender not registered.")
        return "Error: Telegram sender no disponible."

    try:
        await _sender(target, message)
        logger.info("send_telegram_message delivered to user_id=%s", target)
        return f"Mensaje enviado a {target}."
    except Exception as e:
        logger.error("send_telegram_message failed: %s", e)
        return f"Error enviando mensaje: {e}"


def get_telegram_tools() -> list:
    return [send_telegram_message]
