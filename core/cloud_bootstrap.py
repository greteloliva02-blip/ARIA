"""
Bootstrap secrets and paths when running in cloud (Fly.io).
"""
import json
import os
from pathlib import Path

from core.logger import get_logger

logger = get_logger("cloud")


def bootstrap_cloud_environment(project_root: Path) -> None:
    """Write credential files from env vars into persistent /data when needed."""
    if not _is_cloud():
        return

    data_root = Path(os.getenv("ARIA_DATA_DIR", "/data"))
    data_root.mkdir(parents=True, exist_ok=True)

    google_dir = Path(os.getenv("GOOGLE_CREDENTIALS_DIR", str(data_root / "google_credentials")))
    google_dir.mkdir(parents=True, exist_ok=True)

    token_json = os.getenv("GOOGLE_TOKEN_JSON", "").strip()
    if token_json:
        (google_dir / "token.json").write_text(token_json, encoding="utf-8")
        logger.info("Google token.json written from GOOGLE_TOKEN_JSON secret.")

    client_json = os.getenv("GOOGLE_CLIENT_SECRET_JSON", "").strip()
    if client_json:
        (google_dir / "client_secret.json").write_text(client_json, encoding="utf-8")
        logger.info("Google client_secret.json written from GOOGLE_CLIENT_SECRET_JSON secret.")

    firebase_json = os.getenv("FIREBASE_CRED_JSON", "").strip()
    if firebase_json:
        fb_path = data_root / "firebase_service_account.json"
        # Validate JSON
        json.loads(firebase_json)
        fb_path.write_text(firebase_json, encoding="utf-8")
        os.environ.setdefault("FIREBASE_CRED_PATH", str(fb_path))
        logger.info("Firebase credentials written from FIREBASE_CRED_JSON secret.")


def _is_cloud() -> bool:
    return os.getenv("ARIA_CLOUD", "").lower() in ("1", "true", "yes", "on") or bool(
        os.getenv("FLY_APP_NAME")
    )
