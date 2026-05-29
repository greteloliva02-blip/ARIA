# Firebase integration for ARIA
# This module initializes Firebase Admin SDK and provides a simple API to store conversation messages.

import json
import os
import logging
from datetime import datetime

from firebase_admin import credentials, firestore, initialize_app, _apps

logger = logging.getLogger("firebase")


def _load_credentials():
    """Load Firebase credentials from environment.
    Priority:
    1. FIREBASE_CRED_JSON (JSON string, Railway secret)
    2. FIREBASE_CRED_PATH (path to JSON file)
    3. service_account.json in this directory (fallback for local dev)
    Returns a credentials.Certificate instance or ``None`` if not found.
    """
    cred_json = os.getenv("FIREBASE_CRED_JSON", "").strip()
    cred_path = os.getenv("FIREBASE_CRED_PATH")

    # 1️⃣ JSON string (Railway secret)
    if cred_json:
        try:
            cred_dict = json.loads(cred_json)
            return credentials.Certificate(cred_dict)
        except Exception as e:
            logger.error(f"Failed to parse FIREBASE_CRED_JSON: {e}")
            return None

    # 2️⃣ File path
    if cred_path and os.path.exists(cred_path):
        try:
            return credentials.Certificate(cred_path)
        except Exception as e:
            logger.error(f"Failed to load credentials from FIREBASE_CRED_PATH: {e}")
            return None

    # 3️⃣ Default file next to this module
    default_path = os.path.join(os.path.dirname(__file__), "service_account.json")
    if os.path.exists(default_path):
        try:
            return credentials.Certificate(default_path)
        except Exception as e:
            logger.error(f"Failed to load default service_account.json: {e}")
            return None

    # No credentials available
    print("Firebase credentials not provided")
    logger.warning("Firebase credentials not provided; skipping Firebase integration.")
    return None


def _extract_project_id(cred_json: str, cred_path: str, default_path: str) -> str | None:
    """Extract the project_id from the available credential source.
    If FIREBASE_PROJECT_ID env var is set, it is used directly. Otherwise we try to
    read the project_id from the JSON payload used to create the credentials.
    """
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    if project_id:
        return project_id

    try:
        if cred_json:
            payload = json.loads(cred_json)
        elif cred_path and os.path.exists(cred_path):
            with open(cred_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        else:
            with open(default_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        return payload.get("project_id")
    except Exception as e:
        logger.debug(f"Unable to extract project_id from credentials: {e}")
        return None


def init_firebase():
    """Initialize Firebase Admin SDK and return a Firestore client.
    Returns ``None`` if initialization fails or credentials are missing.
    """
    cred = _load_credentials()
    if cred is None:
        return None

    # Determine project_id (may be missing from env)
    cred_json = os.getenv("FIREBASE_CRED_JSON", "").strip()
    cred_path = os.getenv("FIREBASE_CRED_PATH")
    default_path = os.path.join(os.path.dirname(__file__), "service_account.json")
    project_id = _extract_project_id(cred_json, cred_path, default_path)

    try:
        # Initialise the app only once – ``_apps`` is a list of initialized apps
        if not _apps:
            initialize_app(cred, {"projectId": project_id})
        db = firestore.client()
        logger.info("Firebase initialized successfully.")
        return db
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return None

# Lazy singleton Firestore client
_DB_CLIENT = None


def get_db():
    global _DB_CLIENT
    if _DB_CLIENT is None:
        _DB_CLIENT = init_firebase()
    return _DB_CLIENT


def save_message(user_id: str, role: str, content: str, timestamp: datetime) -> bool:
    """Persist a conversation message to Firestore under collection ``conversations``.
    Returns ``True`` on success, ``False`` otherwise.
    """
    db = get_db()
    if db is None:
        return False
    try:
        doc_ref = db.collection("conversations").document()
        doc_ref.set({
            "user_id": user_id,
            "role": role,
            "content": content,
            "timestamp": timestamp.isoformat(),
        })
        logger.info("Message saved to Firebase.")
        return True
    except Exception as e:
        logger.error(f"Error saving message to Firebase: {e}")
        return False
