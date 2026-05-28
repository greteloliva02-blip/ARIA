"""
ARIA — Sistema de Memoria Persistente
SQLite para historial + hechos + recordatorios
ChromaDB para búsqueda semántica (opcional)
"""
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.config import Config
from core.logger import get_logger
from services.firebase.firebase_client import save_message as firebase_save_message

logger = get_logger("memory")


class MemoryManager:
    """Persistent memory with structured (SQLite) and semantic (ChromaDB) storage."""

    def __init__(self, config: Config):
        self.config = config
        self.db_path = Path(config.DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._chroma_collection = None
        self._init_db()

    # ══════════════════════════════════════════════════════════
    #  SQLite Initialization
    # ══════════════════════════════════════════════════════════
    def _init_db(self):
        conn = self._conn()
        c = conn.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   TEXT     NOT NULL,
                role      TEXT     NOT NULL,
                content   TEXT     NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id   TEXT     NOT NULL,
                key       TEXT     NOT NULL,
                value     TEXT     NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, key)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT     NOT NULL,
                message    TEXT     NOT NULL,
                remind_at  DATETIME NOT NULL,
                completed  BOOLEAN  DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))

    # ══════════════════════════════════════════════════════════
    #  ChromaDB (lazy init)
    # ══════════════════════════════════════════════════════════
    def _get_chroma(self):
        if getattr(self.config, "DISABLE_CHROMA", False):
            return None
        if self._chroma_collection is not None:
            return self._chroma_collection
        try:
            import chromadb

            chroma_path = Path(self.config.CHROMA_PATH)
            chroma_path.mkdir(parents=True, exist_ok=True)
            client = chromadb.PersistentClient(path=str(chroma_path))
            self._chroma_collection = client.get_or_create_collection(
                name="aria_memory",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info("ChromaDB semantic memory ready")
        except Exception as e:
            logger.warning(f"ChromaDB unavailable ({e}). Semantic search disabled.")
            self._chroma_collection = None
        return self._chroma_collection

    # ══════════════════════════════════════════════════════════
    #  Conversations
    # ══════════════════════════════════════════════════════════
    def save_message(self, user_id: str, role: str, content: str):
        """Persist a conversation message."""
        conn = self._conn()
        conn.execute(
            "INSERT INTO conversations (user_id, role, content) VALUES (?, ?, ?)",
            (str(user_id), role, content),
        )
        conn.commit()
        conn.close()

        # Also store in ChromaDB for semantic retrieval
        collection = self._get_chroma()
        if collection is not None:
            try:
                doc_id = f"{user_id}_{datetime.now().timestamp()}"
                collection.add(
                    documents=[f"{role}: {content}"],
                    ids=[doc_id],
                    metadatas=[{
                        "user_id": str(user_id),
                        "role": role,
                        "timestamp": datetime.now().isoformat(),
                    }],
                )
            except Exception as e:
                logger.debug(f"ChromaDB insert skipped: {e}")

        # Save to Firebase for cloud backup (optional)
        try:
            firebase_save_message(str(user_id), role, content, datetime.utcnow())
        except Exception as e:
            logger.debug("Firebase save skipped: %s", e)

    def get_history(self, user_id: str, limit: int = 20) -> list[dict]:
        """Get recent conversation history (oldest-first)."""
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

    # ══════════════════════════════════════════════════════════
    #  Semantic Search
    # ══════════════════════════════════════════════════════════
    def search_memory(self, query: str, k: int = 5) -> list[str]:
        """Search conversation history by meaning."""
        collection = self._get_chroma()
        if collection is None:
            return []
        try:
            results = collection.query(query_texts=[query], n_results=k)
            return results["documents"][0] if results["documents"] else []
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []

    # ══════════════════════════════════════════════════════════
    #  Personal Facts
    # ══════════════════════════════════════════════════════════
    def save_fact(self, user_id: str, key: str, value: str):
        """Store / update a personal fact."""
        conn = self._conn()
        conn.execute(
            "INSERT OR REPLACE INTO facts (user_id, key, value, timestamp) "
            "VALUES (?, ?, ?, ?)",
            (str(user_id), key, value, datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
        logger.info(f"Fact saved: {key} = {value}")

    def get_facts(self, user_id: str) -> dict[str, str]:
        """Retrieve all known facts for a user."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT key, value FROM facts WHERE user_id = ?",
            (str(user_id),),
        ).fetchall()
        conn.close()
        return {r[0]: r[1] for r in rows}

    # ══════════════════════════════════════════════════════════
    #  Reminders
    # ══════════════════════════════════════════════════════════
    def add_reminder(
        self, user_id: str, message: str, remind_at: datetime
    ) -> int:
        """Create a new reminder, returns its id."""
        conn = self._conn()
        cur = conn.execute(
            "INSERT INTO reminders (user_id, message, remind_at) VALUES (?, ?, ?)",
            (str(user_id), message, remind_at.isoformat()),
        )
        rid = cur.lastrowid
        conn.commit()
        conn.close()
        logger.info(f"Reminder #{rid} → {remind_at}")
        return rid

    def get_pending_reminders(self) -> list[dict]:
        """Get all reminders that are due now."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT id, user_id, message, remind_at FROM reminders "
            "WHERE completed = 0 AND remind_at <= ?",
            (datetime.now().isoformat(),),
        ).fetchall()
        conn.close()
        return [
            {"id": r[0], "user_id": r[1], "message": r[2], "remind_at": r[3]}
            for r in rows
        ]

    def complete_reminder(self, reminder_id: int):
        """Mark a reminder as done."""
        conn = self._conn()
        conn.execute(
            "UPDATE reminders SET completed = 1 WHERE id = ?", (reminder_id,)
        )
        conn.commit()
        conn.close()

    def get_all_reminders(self, user_id: str) -> list[dict]:
        """Get all pending reminders for a user."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT id, message, remind_at, completed FROM reminders "
            "WHERE user_id = ? AND completed = 0 ORDER BY remind_at",
            (str(user_id),),
        ).fetchall()
        conn.close()
        return [
            {"id": r[0], "message": r[1], "remind_at": r[2], "completed": r[3]}
            for r in rows
        ]
