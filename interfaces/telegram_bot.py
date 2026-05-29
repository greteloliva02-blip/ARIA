import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from interfaces.base_interface import BaseInterface
from core.agent import AriaAgent
from core.config import Config
from core.logger import get_logger

logger = get_logger("telegram")


class TelegramBot(BaseInterface):
    """Telegram bot interface for ARIA (stable polling version)."""

    # ✅ CONSTRUCTOR CORRECTO
    def __init__(self, agent: AriaAgent, config: Config):
        self.agent = agent
        self.config = config

        self.app = (
            Application.builder()
            .token(config.TELEGRAM_TOKEN)
            .connect_timeout(30.0)
            .read_timeout(30.0)
            .write_timeout(30.0)
            .pool_timeout(30.0)
            .build()
        )

        self._setup_handlers()

    def _setup_handlers(self):
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("help", self._cmd_help))
        self.app.add_handler(CommandHandler("memory", self._cmd_memory))
        self.app.add_handler(CommandHandler("status", self._cmd_status))

        self.app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._handle_message,
            )
        )

        self.app.add_error_handler(self._error_handler)

    # ───────────────────────── AUTH ─────────────────────────

    def _is_authorized(self, update: Update) -> bool:
        uid = update.effective_user.id

        if not self.config.TELEGRAM_USER_ID:
            self.config.TELEGRAM_USER_ID = str(uid)
            logger.info(f"Auto-registered user: {uid}")
            return True

        return self.config.is_authorized(uid)

    # ───────────────────────── COMMANDS ─────────────────────────

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ No autorizado.")
            return

        user = update.effective_user

        await update.message.reply_text(
            f"🤖 Hola {user.first_name}, ARIA está activa.\nEscribe lo que necesites."
        )

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return

        await update.message.reply_text(
            "/start - iniciar\n"
            "/help - ayuda\n"
            "/memory - memoria\n"
            "/status - estado"
        )

    async def _cmd_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return

        uid = str(update.effective_user.id)
        facts = self.agent.memory.get_facts(uid)

        if not facts:
            await update.message.reply_text("No hay memoria todavía.")
            return

        text = "🧠 Memoria:\n"

        for k, v in facts.items():
            text += f"- {k}: {v}\n"

        await update.message.reply_text(text)

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return

        await update.message.reply_text(
            f"Modelo: {self.config.MISTRAL_MODEL}\n"
            f"Tools: {len(self.agent.tools)}"
        )

    # ───────────────────────── MENSAJES ─────────────────────────

    async def _handle_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ No autorizado.")
            return

        user_id = str(update.effective_user.id)
        message = update.message.text

        logger.info("[%s] %s", user_id, message)

        try:
            await update.message.chat.send_action("typing")
        except Exception:
            pass

        try:
            response = await self.agent.process_message(user_id, message)
        except Exception as e:logger.error(f"Agent error: {e}", exc_info=True)
            response = "⚠️ Error interno procesando el mensaje."

        await update.message.reply_text(response)

    # ───────────────────────── ERROR HANDLER ─────────────────────────

    async def _error_handler(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
    ):
        logger.error(
            f"Telegram error: {context.error}",
            exc_info=context.error,
        )

    # ───────────────────────── START / STOP ─────────────────────────

    async def start(self):
        logger.info("Starting Telegram bot (polling mode)...")

        await self.app.initialize()
        await self.app.start()

        # ✅ SOLO POLLING
        await self.app.run_polling()

    async def stop(self):
        logger.info("Stopping Telegram bot...")

        try:
            await self.app.stop()
        except Exception:
            pass

        try:
            await self.app.shutdown()
        except Exception:
            pass

    # ───────────────────────── SEND MESSAGE ─────────────────────────

    async def send_message(self, user_id: str, message: str):
        try:
            await self.app.bot.send_message(
                chat_id=int(user_id),
                text=message,
            )
        except Exception as e:
            logger.error(f"Failed to send message: {e}")