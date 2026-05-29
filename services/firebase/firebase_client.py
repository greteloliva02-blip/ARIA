# Firebase integration for ARIA
# This module initializes Firebase Admin SDK and provides a simple API to store conversation messages.

import json
import os
import logging
from datetime import datetime

from firebase_admin import credentials, firestore, initialize_app, get_app, _apps

logger = logging.getLogger("firebase")

def init_firebase():
    """Initialize Firebase app using service account credentials.
    Reads env vars FIREBASE_CRED_PATH, FIREBASE_CRED_JSON, and FIREBASE_PROJECT_ID.
    Returns a Firestore client or None if initialization fails.
    """
    cred_path = os.getenv("FIREBASE_CRED_PATH")
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    cred_json = os.getenv("FIREBASE_CRED_JSON", "").strip()

    try:
        # 1️⃣ Prefer JSON string (useful for Railway secrets)
        if cred_json:
            # The env var may contain literal newlines escaped as \n; json.loads handles this.
            cred = credentials.Certificate(json.loads(cred_json))
        # 2️⃣ Fallback to a file path
        elif cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
        else:
            print("Firebase credentials not provided")
            return None

        # 3️⃣ Ensure we have a project_id – try to pull it from the credential payload if missing
        if not project_id:
            try:
                if cred_json:
                    payload = json.loads(cred_json)
                else:
                    with open(cred_path, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                project_id = payload.get("project_id")
            except Exception as e:
                logger.debug(f"Unable to extract project_id from credentials: {e}")

        # 4️⃣ Initialise the Firebase app only once (avoid duplicate app errors)
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

def save_message(user_id: str, role: str, content: str, timestamp: datetime):
    """Persist a conversation message to Firestore under collection 'conversations'.
    Document structure: {user_id, role, content, timestamp}
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
