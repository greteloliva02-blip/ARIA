"""
ARIA - Google OAuth2 Authentication
Manages credentials for Gmail and Calendar APIs.
"""
import os
import json
from pathlib import Path
from core.logger import get_logger

logger = get_logger("google_auth")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]


def get_google_credentials(config=None):
    """
    Load or generate Google OAuth2 credentials.
    First run will open a browser window for authorization.
    Subsequent runs use the saved token.
    """
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request

    if config is not None and hasattr(config, "PROJECT_ROOT"):
        default_dir = config.PROJECT_ROOT / "google_credentials"
    else:
        default_dir = Path(__file__).resolve().parents[2] / "google_credentials"

    creds_dir = Path(os.getenv("GOOGLE_CREDENTIALS_DIR", str(default_dir)))
    creds_dir.mkdir(parents=True, exist_ok=True)

    token_path = Path(os.getenv("GOOGLE_TOKEN_PATH", str(creds_dir / "token.json")))
    client_secret_path = Path(
        os.getenv("GOOGLE_CLIENT_SECRET_PATH", str(creds_dir / "client_secret.json"))
    )

    creds = None

    # Load existing token
    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
            logger.info("Google token loaded from disk.")
        except Exception as e:
            logger.warning(f"Could not load token: {e}")

    # Refresh or create new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.info("Google token refreshed successfully.")
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}. Re-authenticating...")
                creds = None

        if not creds:
            if not client_secret_path.exists():
                logger.error(
                    f"Google Client Secret not found at: {client_secret_path}"
                )
                return None

            if os.getenv("ARIA_CLOUD", "").lower() in ("1", "true", "yes", "on") or os.getenv("FLY_APP_NAME"):
                logger.error(
                    "Google OAuth browser flow unavailable in cloud. "
                    "Set GOOGLE_TOKEN_JSON secret with a pre-authorized token."
                )
                return None

            logger.info("Starting Google OAuth2 flow (browser will open)...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret_path), SCOPES
            )
            creds = flow.run_local_server(port=0)
            logger.info("Google OAuth2 authorization completed!")

        # Save token for future use
        with open(token_path, "w") as f:
            f.write(creds.to_json())
        logger.info(f"Token saved to {token_path}")

    return creds
