"""
ARIA — Main entrypoint (minimal cloud-ready).
Telegram polling + Mistral + optional SQLite/Firebase memory.
"""
import asyncio
import os
import signal
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent))

from core.config import Config
from core.memory import MemoryManager
from core.agent import AriaAgent
from core.logger import get_logger
from interfaces.telegram_bot import TelegramBot

logger = get_logger("main")


async def main():
    logger.info("Starting ARIA...")
    config = Config()

    if not config.TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is required.")
        sys.exit(1)
    if not config.MISTRAL_API_KEY:
        logger.error("MISTRAL_API_KEY is required.")
        sys.exit(1)

    # Optional health endpoint when platform sets PORT (e.g. Railway web service)
    port = os.getenv("PORT")
    if port:
        from core.health_server import start_health_server
        start_health_server(int(port))
        logger.info("Health server on port %s", port)

    memory = MemoryManager(config)
    agent = AriaAgent(config, memory)
    bot = TelegramBot(agent, config)

    await bot.start()

    logger.info("ARIA is running (Telegram polling, single instance).")
    logger.info("Model: %s | Minimal mode: %s", config.MISTRAL_MODEL, config.MINIMAL_MODE)

    stop_event = asyncio.Event()

    def _signal_handler(*_):
        logger.info("Shutdown signal received.")
        stop_event.set()

    if sys.platform != "win32":
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except NotImplementedError:
                signal.signal(sig, _signal_handler)
    else:
        signal.signal(signal.SIGINT, _signal_handler)

    await stop_event.wait()

    logger.info("Shutting down...")
    await bot.stop()
    logger.info("ARIA stopped.")


def run_forever():
    """Restart on crash so the bot recovers without manual intervention."""
    while True:
        try:
            asyncio.run(main())
            break
        except KeyboardInterrupt:
            logger.info("Interrupted by user.")
            break
        except SystemExit:
            raise
        except Exception as e:
            logger.error("ARIA crashed: %s", e, exc_info=True)
            logger.info("Restarting in 15 seconds...")
            time.sleep(15)


if __name__ == "__main__":
    run_forever()
