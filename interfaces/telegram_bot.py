import os

"""
ARIA — Bot de Telegram
Interfaz principal de comunicación con el usuario.
Solo responde al usuario autorizado (auto-registro del primero).
"""
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
    """Telegram bot interface for ARIA."""

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
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )
        self.app.add_error_handler(self._error_handler)

    # ── Authorization ──────────────────────────────────────
    def _is_authorized(self, update: Update) -> bool:
        uid = update.effective_user.id
        if not self.config.TELEGRAM_USER_ID:
            # Auto-register first user
            self.config.TELEGRAM_USER_ID = str(uid)
            self._persist_user_id(uid)
            logger.info(f"✅ Auto-registered user: {uid}")
            return True
        return self.config.is_authorized(uid)

    def _persist_user_id(self, uid: int):
        """Write TELEGRAM_USER_ID back to .env so it persists (local only)."""
        if getattr(self.config, "IS_CLOUD", False) or os.getenv("RAILWAY_ENVIRONMENT"):
            logger.info(
                "Cloud mode: set TELEGRAM_USER_ID=%s in Fly secrets (not writing .env).",
                uid,
            )
            return
        env_path = self.config.PROJECT_ROOT / ".env"
        try:
            text = env_path.read_text(encoding="utf-8")
            if "TELEGRAM_USER_ID=" in text:
                lines = text.splitlines()
                for i, line in enumerate(lines):
                    if line.startswith("TELEGRAM_USER_ID="):
                        lines[i] = f"TELEGRAM_USER_ID={uid}"
                text = "\n".join(lines)
            else:
                text += f"\nTELEGRAM_USER_ID={uid}"
            env_path.write_text(text, encoding="utf-8")
        except Exception as e:
            logger.error(f"Could not persist user ID: {e}")

    # ── Commands ───────────────────────────────────────────
    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            await update.message.reply_text("⛔ No autorizado.")
            return

        user = update.effective_user
        tools_count = len(self.agent.tools)
        welcome = (
            f"🤖 *¡Hola {user.first_name}! Soy ARIA*\n\n"
            f"Tu asistente personal ejecutivo inteligente, "
            f"corriendo en la nube.\n\n"
            f"🔧 *{tools_count} herramientas* activas:\n"
            f"• 📁 Gestión de archivos\n"
            f"• 🌐 Búsqueda en internet\n"
            f"• 💻 Automatización del PC\n"
            f"• 📝 Notas y recordatorios\n"
            f"• 📄 Lectura/creación de PDFs\n\n"
            f"🔑 Tu ID: `{user.id}` ✅\n\n"
            f"Escríbeme lo que necesites 👇"
        )
        await update.message.reply_text(welcome, parse_mode="Markdown")

    async def _cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return

        text = (
            "📖 *Guía de ARIA*\n\n"
            "*Comandos:*\n"
            "/start — Bienvenida\n"
            "/help — Esta ayuda\n"
            "/memory — Ver qué recuerdo de ti\n"
            "/status — Estado del sistema\n\n"
            "*Ejemplos de uso:*\n"
            '• _"¿Qué archivos hay en D:\\?"_\n'
            '• _"Busca noticias sobre IA"_\n'
            '• _"Abre el Bloc de Notas"_\n'
            '• _"Recuérdame en 30 minutos hacer café"_\n'
            '• _"Crea una nota con la lista de compras"_\n'
            '• _"Lee el PDF C:\\docs\\reporte.pdf"_\n'
            '• _"¿Cómo está la RAM de mi PC?"_\n'
            '• _"Busca laptops RTX 4060 baratas"_\n'
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    async def _cmd_memory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return

        uid = str(update.effective_user.id)
        facts = self.agent.memory.get_facts(uid)

        if facts:
            text = "🧠 *Lo que recuerdo de ti:*\n\n"
            for k, v in facts.items():
                text += f"• *{k}*: {v}\n"
        else:
            text = "🧠 Aún no tengo datos guardados. ¡Cuéntame sobre ti!"

        await update.message.reply_text(text, parse_mode="Markdown")

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            return

        tools_list = ", ".join(t.name for t in self.agent.tools)
        text = (
            "📊 *Estado de ARIA*\n\n"
            f"• 🤖 Modelo: `{self.config.MISTRAL_MODEL}`\n"
            f"• 🔧 Herramientas: {len(self.agent.tools)}\n"
            f"• 📦 Tools: _{tools_list}_\n"
            f"• Memoria: SQLite\n"
            f"• ✅ Sistema operativo\n"
        )
        await update.message.reply_text(text, parse_mode="Markdown")

    # ── Message Handler ────────────────────────────────────
    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self._is_authorized(update):
            uid = update.effective_user.id
            await update.message.reply_text(
                f"⛔ No autorizado. Tu ID: `{uid}`", parse_mode="Markdown"
            )
            return

        user_id = str(update.effective_user.id)
        message = update.message.text

        try:
            await update.message.chat.send_action("typing")
        except Exception as e:
            logger.warning("Typing indicator failed: %s", e)
        logger.info("[%s] %s", user_id, message[:80])

        # Process with ARIA agent
        response = await self.agent.process_message(user_id, message)

        # Send response (split if too long for Telegram's 4096 limit)
        await self._send_response(update, response)

    async def _send_response(self, update: Update, text: str):
        """Send response, splitting if necessary."""
        max_len = 4000

        if len(text) <= max_len:
            try:
                await update.message.reply_text(text, parse_mode="Markdown")
            except Exception:
                # Fallback: send without Markdown if parsing fails
                await update.message.reply_text(text)
            return

        # Split into chunks
        chunks = []
        while text:
            if len(text) <= max_len:
                chunks.append(text)
                break
            # Find a good split point
            split_at = text.rfind("\n", 0, max_len)
            if split_at < max_len // 2:
                split_at = max_len
            chunks.append(text[:split_at])
            text = text[split_at:].lstrip()

        for chunk in chunks:
            try:
                await update.message.reply_text(chunk, parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(chunk)

    # ── Error Handler ──────────────────────────────────────
    async def _error_handler(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ):
        logger.error(f"Telegram error: {context.error}", exc_info=context.error)

    # ── Interface Methods ──────────────────────────────────
    async def start(self):
        logger.info("Starting Telegram bot...")
        await self.app.initialize()
        await self.app.start()
        # Polling only — remove webhook to prevent 409 conflicts
        await self.app.bot.delete_webhook(drop_pending_updates=True)
        if self.app.updater.running:
            logger.warning("Updater already running; skipping second start.")
            return
        await self.app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            bootstrap_retries=-1,
        )
        logger.info("Telegram polling active (single instance).")

    async def stop(self):
        logger.info("🛑 Stopping Telegram Bot...")
        await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()

    async def send_message(self, user_id: str, message: str):
        """Send a proactive message (e.g., reminders)."""
        try:
            await self.app.bot.send_message(
                chat_id=int(user_id),
                text=message,
                parse_mode="Markdown",
            )
        except Exception:
            try:
                await self.app.bot.send_message(
                    chat_id=int(user_id),
                    text=message,
                )
            except Exception as e:
                logger.error(f"Failed to send proactive message: {e}")
