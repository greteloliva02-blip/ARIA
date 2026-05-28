"""
ARIA — Central configuration (environment variables only).
"""
import os
from pathlib import Path

from dotenv import load_dotenv


def _env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in ("1", "true", "yes", "on")


class Config:
    """Singleton configuration loaded from environment."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def __init__(self):
        if self._loaded:
            return

        env_path = Path(__file__).parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
        else:
            load_dotenv()

        self.PROJECT_ROOT = Path(__file__).parent.parent.resolve()
        self.IS_CLOUD = bool(
            os.getenv("RAILWAY_ENVIRONMENT")
            or os.getenv("RAILWAY_SERVICE_NAME")
            or os.getenv("RENDER")
            or os.getenv("FLY_APP_NAME")
            or _env_bool("ARIA_CLOUD")
        )

        self.MINIMAL_MODE = _env_bool("ARIA_MINIMAL", default=True)

        # Required secrets (read from env only)
        self.TELEGRAM_TOKEN: str = (os.getenv("TELEGRAM_TOKEN") or "").strip()
        self.TELEGRAM_USER_ID: str = (os.getenv("TELEGRAM_USER_ID") or "").strip()
        self.MISTRAL_API_KEY: str = (os.getenv("MISTRAL_API_KEY") or "").strip()
        self.MISTRAL_MODEL: str = (os.getenv("MISTRAL_MODEL") or "mistral-small-latest").strip()

        # Writable data dir: use app folder on Railway (no /data volume required)
        default_data = self.PROJECT_ROOT / "memory"
        if self.IS_CLOUD:
            default_data = Path(os.getenv("ARIA_DATA_DIR", str(self.PROJECT_ROOT / "memory")))

        self.DB_PATH: str = os.getenv("DB_PATH", str(default_data / "aria.db"))
        self.CHROMA_PATH: str = os.getenv("CHROMA_PATH", str(default_data / "chroma_db"))
        self.DISABLE_CHROMA: bool = _env_bool("DISABLE_CHROMA", default=True)

        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

        Path(self.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR = Path(os.getenv("LOG_DIR", str(self.PROJECT_ROOT / "logs")))
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)

        self._loaded = True

    def is_authorized(self, user_id: int) -> bool:
        if not self.TELEGRAM_USER_ID:
            return True
        return str(user_id) == str(self.TELEGRAM_USER_ID)


def validate_required_env() -> list[str]:
    """Return list of missing required environment variable names."""
    missing = []
    if not (os.getenv("TELEGRAM_TOKEN") or "").strip():
        missing.append("TELEGRAM_TOKEN")
    if not (os.getenv("MISTRAL_API_KEY") or "").strip():
        missing.append("MISTRAL_API_KEY")
    return missing
