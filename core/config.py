"""
ARIA — Central configuration (env vars only, no hardcoded secrets).
"""
import os
from pathlib import Path
from dotenv import load_dotenv


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

        self.PROJECT_ROOT = Path(__file__).parent.parent
        self.IS_CLOUD = bool(
            os.getenv("RAILWAY_ENVIRONMENT")
            or os.getenv("RENDER")
            or os.getenv("FLY_APP_NAME")
            or os.getenv("ARIA_CLOUD", "").lower() in ("1", "true", "yes", "on")
        )

        # Minimal mode: Telegram + Mistral + web tool only (default ON for stability)
        self.MINIMAL_MODE = os.getenv("ARIA_MINIMAL", "true").lower() in (
            "1", "true", "yes", "on"
        )

        self.MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
        self.MISTRAL_MODEL: str = os.getenv("MISTRAL_MODEL", "mistral-small-latest")
        self.TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
        self.TELEGRAM_USER_ID: str = os.getenv("TELEGRAM_USER_ID", "")

        data_dir = Path(
            os.getenv(
                "ARIA_DATA_DIR",
                "/data" if self.IS_CLOUD else str(self.PROJECT_ROOT / "memory"),
            )
        )

        self.DB_PATH: str = os.getenv(
            "DB_PATH",
            str(data_dir / "aria.db") if self.IS_CLOUD else str(self.PROJECT_ROOT / "memory" / "aria.db"),
        )
        self.CHROMA_PATH: str = os.getenv("CHROMA_PATH", str(data_dir / "chroma_db"))
        self.DISABLE_CHROMA: bool = self.MINIMAL_MODE or os.getenv(
            "DISABLE_CHROMA", ""
        ).lower() in ("1", "true", "yes", "on")

        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

        Path(self.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        log_dir = Path(os.getenv("LOG_DIR", str(self.PROJECT_ROOT / "logs")))
        log_dir.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR = log_dir

        self._loaded = True

    def is_authorized(self, user_id: int) -> bool:
        if not self.TELEGRAM_USER_ID:
            return True
        return str(user_id) == str(self.TELEGRAM_USER_ID)
