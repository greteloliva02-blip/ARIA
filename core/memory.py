"""
ARIA — Persistent memory (SQLite). Chroma/Firebase optional and lazy.
"""
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from core.config import Config
from core.logger import get_logger

logger = get_logger("memory")


class MemoryManager:
    def __init__(self, config: Config):
        self.config = config
        self.db_path = Path(config.DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._chroma_collection = False  # disabled by default in cloud
        self._init_db()

    def _init_db(self):
        conn = self._conn()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, key)
            )
        """)
        conn.commit()
        conn.close()
        logger.info("Database initialized at %s", self.db_path)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    def save_message(self, user_id: str, role: str, content: str):
        conn = self._conn()
        conn.execute(
            "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
            (str(user_id), role, content),
        )
        conn.commit()
        conn.close()
        self._try_firebase_save(user_id, role, content)

    def _try_firebase_save(self, user_id: str, role: str, content: str):
        try:
            from services.firebase.firebase_client import save_message
            save_message(str(user_id), role, content, datetime.now(timezone.utc))
        except Exception as e:
            logger.debug("Firebase save skipped: %s", e)

    def get_history(self, user_id: str, limit: int = 20) -> list[dict]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT role, content, timestamp FROM conversations "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (str(user_id), limit),
        ).fetchall()
        conn.close()
        return [
            {"role": r[0], "content": r[1], "timestamp": r[2]}
            for r in reversed(rows)
        ]

    def search_memory(self, query: str, k: int = 5) -> list[str]:
        return []

    def save_fact(self, user_id: str, key: str, value: str):
        conn = self._conn()
        conn.execute(
            "INSERT OR REPLACE INTO facts (user_id, key, value, timestamp) "
            "VALUES (?, ?, ?, ?)",
            (str(user_id), key, value, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()

    def get_facts(self, user_id: str) -> dict[str, str]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT key, value FROM facts WHERE user_id = ?",
            (str(user_id),),
        ).fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}
