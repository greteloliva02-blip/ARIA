"""
ARIA — Main entrypoint for local and Railway.
Telegram polling + Mistral API.
"""

import asyncio
import os
import signal
import sys
import time
from pathlib import Path

# ───────────────────────── UTF-8 FIX (Windows) ─────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ───────────────────────── PROJECT ROOT ─────────────────────────
ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT))

# ───────────────────────── ENV REQUIREMENTS ─────────────────────────
_REQUIRED_ENV = ("TELEGRAM_TOKEN", "MISTRAL_API_KEY")


def missing_env_vars() -> list[str]:
    return [name for name in _REQUIRED_ENV if not (os.getenv(name) or "").strip()]


def validate_env() -> None:
    missing = missing_env_vars()
    if not missing:
        return

    cloud = bool(
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("RAILWAY_SERVICE_NAME")
        or os.getenv("PORT")
    )

    hint = (
        "Add them in Railway: Project → Variables → Raw Editor, then Redeploy."
        if cloud
        else "Add them to your local .env file."
    )

    print(
        "FATAL: Missing environment variables: "
        + ", ".join(missing)
        + ". "
        + hint,
        file=sys.stderr,
        flush=True,
    )
    sys.exit(1)


# ───────────────────────── HEALTH SERVER ─────────────────────────
def start_health_if_needed() -> None:
    port = (os.getenv("PORT") or "").strip()
    if not port:
        return

    try:
        from core.health_server import start_health_server

        start_health_server(int(port))
        print(f"Health server listening on 0.0.0.0:{port}", flush=True)
    except Exception as e:
        print(f"WARNING: Health server failed: {e}", file=sys.stderr, flush=True)


# ───────────────────────── MAIN APP ─────────────────────────
async def main() -> None:
    from core.config import Config
    from core.memory import MemoryManager
    from core.agent import AriaAgent
    from core.logger import get_logger
    from interfaces.telegram_bot import TelegramBot

    logger = get_logger("main")
    logger.info("Starting ARIA...")

    config = Config()

    if not config.TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN is required.")
        sys.exit(1)

    if not config.MISTRAL_API_KEY:
        logger.error("MISTRAL_API_KEY is required.")
        sys.exit(1)

    logger.info(
        "ARIA starting (cloud=%s, model=%s)",
        config.IS_CLOUD,
        config.MISTRAL_MODEL,
    )

    memory = MemoryManager(config)
    agent = AriaAgent(config, memory)
    bot = TelegramBot(agent, config)

    await bot.start()

    logger.info("ARIA is running — Telegram active.")

    stop_event = asyncio.Event()

    def _on_stop(*_):
        logger.info("Shutdown signal received.")
        stop_event.set()

    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _on_stop)
            except Exception:
                signal.signal(sig, lambda *_: _on_stop())
    else:
        signal.signal(signal.SIGINT, lambda *_: _on_stop())

    await stop_event.wait()

    await bot.stop()
    logger.info("ARIA stopped.")


# ───────────────────────── GOOGLE BOOTSTRAP ─────────────────────────
def bootstrap_google_credentials() -> None:
    try:
        from core.cloud_bootstrap import bootstrap_cloud_environment

        bootstrap_cloud_environment(ROOT)

        if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_SERVICE_NAME"):
            data = Path(os.getenv("ARIA_DATA_DIR", str(ROOT / "memory")))
            gdir = data / "google_credentials"

            if (gdir / "token.json").exists():
                os.environ.setdefault("GOOGLE_CREDENTIALS_DIR", str(gdir))
                os.environ.setdefault("GOOGLE_TOKEN_PATH", str(gdir / "token.json"))
                os.environ.setdefault(
                    "GOOGLE_CLIENT_SECRET_PATH",
                    str(gdir / "client_secret.json"),
                )

    except Exception as e:
        print(f"WARNING: Google bootstrap skipped: {e}", file=sys.stderr, flush=True)


# ───────────────────────── RUN LOOP (FIX REAL) ─────────────────────────
def run_forever() -> None:
    validate_env()

    if not os.getenv("RAILWAY_ENVIRONMENT"):
        from core.logger import get_logger

        logger = get_logger("main")
        logger.info("Non-Railway environment detected – ARIA will not start.")
        return

    if os.getenv("ARIA_DISABLE"):
        from core.logger import get_logger

        logger = get_logger("main")
        logger.info("ARIA disabled via ARIA_DISABLE, exiting.")
        return

    bootstrap_google_credentials()
    start_health_if_needed()

    from core.logger import get_logger

    logger = get_logger("main")

    while True:
        try:
            # ✅ FIX: no asyncio.run (Railway-safe loop)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                loop.run_until_complete(main())

            finally:
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception:
                    pass

                try:
                    loop.close()
                except Exception:
                    pass

            break

        except KeyboardInterrupt:
            logger.info("Stopped by user.")
            break

        except SystemExit:
            raise

        except Exception as e:
            if missing_env_vars():
                validate_env()

            logger.error("ARIA crashed: %s", e, exc_info=True)
            logger.info("Restarting in 15 seconds...")
            time.sleep(15)


# ───────────────────────── ENTRYPOINT ─────────────────────────
if __name__ == "__main__":
    run_forever()