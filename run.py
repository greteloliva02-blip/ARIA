"""
ARIA — Main entrypoint for local and Railway.
Telegram polling + Mistral API.
"""
import asyncio
import os
import sys
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

_REQUIRED_ENV = ("TELEGRAM_TOKEN", "MISTRAL_API_KEY")


def missing_env_vars() -> list[str]:
    return [n for n in _REQUIRED_ENV if not (os.getenv(n) or "").strip()]


def validate_env() -> None:
    missing = missing_env_vars()
    if not missing:
        return
    print(
        "FATAL missing env: " + ", ".join(missing),
        file=sys.stderr,
        flush=True,
    )
    sys.exit(1)


def start_health_if_needed() -> None:
    port = (os.getenv("PORT") or "").strip()
    if not port:
        return
    try:
        from core.health_server import start_health_server

        start_health_server(int(port))
        print(f"Health server listening on 0.0.0.0:{port}", flush=True)
    except Exception as e:
        print(f"Health server error: {e}", file=sys.stderr, flush=True)


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
                    "GOOGLE_CLIENT_SECRET_PATH", str(gdir / "client_secret.json")
                )
    except Exception as e:
        print(f"Google bootstrap skipped: {e}", file=sys.stderr, flush=True)


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
        raise RuntimeError("TELEGRAM_TOKEN is required")
    if not config.MISTRAL_API_KEY:
        raise RuntimeError("MISTRAL_API_KEY is required")

    memory = await asyncio.to_thread(MemoryManager, config)
    agent = await asyncio.to_thread(AriaAgent, config, memory)
    bot = TelegramBot(agent, config)

    await bot.start()
    logger.info("ARIA running — Telegram polling active (single instance).")

    await asyncio.Event().wait()


def start_app() -> None:
    validate_env()
    if (
        os.getenv("RAILWAY_ENVIRONMENT")
        or os.getenv("RAILWAY_SERVICE_NAME")
        or os.getenv("PORT")
    ):
        bootstrap_google_credentials()
        start_health_if_needed()
    asyncio.run(main())


if __name__ == "__main__":
    start_app()
