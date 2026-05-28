"""
ARIA - Gmail Service
Full Gmail API integration: list, read, send, search emails.
"""
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from googleapiclient.discovery import build
from services.google.auth import get_google_credentials
from core.logger import get_logger

logger = get_logger("gmail_service")


class GmailService:
    """Manages Gmail operations via the Gmail API."""

    def __init__(self, config=None):
        self.config = config
        self._service = None

    def _get_service(self):
        """Lazy-load the Gmail API service."""
        if self._service is None:
            creds = get_google_credentials(self.config)
            if creds is None:
                raise Exception(
                    "No Google credentials available. "
                    "Run the auth flow first."
                )
            self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def is_ready(self) -> bool:
        """Check if the service can be initialized."""
        try:
            self._get_service()
            return True
        except Exception:
            return False

    def list_messages(self, max_results: int = 10, query: str = "") -> list[dict]:
        """
        List recent emails from inbox.
        query: Gmail search query (e.g., 'is:unread', 'from:someone@gmail.com')
        Returns list of dicts with id, subject, from, date, snippet.
        """
        try:
            service = self._get_service()
            q = query if query else "in:inbox"
            results = (
                service.users()
                .messages()
                .list(userId="me", maxResults=max_results, q=q)
                .execute()
            )

            messages = results.get("messages", [])
            if not messages:
                return []

            email_list = []
            for msg_ref in messages:
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_ref["id"], format="metadata",
                         metadataHeaders=["From", "Subject", "Date"])
                    .execute()
                )

                headers = {
                    h["name"]: h["value"]
                    for h in msg.get("payload", {}).get("headers", [])
                }

                email_list.append({
                    "id": msg["id"],
                    "subject": headers.get("Subject", "(Sin asunto)"),
                    "from": headers.get("From", "Desconocido"),
                    "date": headers.get("Date", ""),
                    "snippet": msg.get("snippet", ""),
                })

            return email_list

        except Exception as e:
            logger.error(f"Error listing messages: {e}")
            return [{"error": str(e)}]

    def read_message(self, message_id: str) -> dict:
        """Read the full content of an email by ID."""
        try:
            service = self._get_service()
            msg = (
                service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            headers = {
                h["name"]: h["value"]
                for h in msg.get("payload", {}).get("headers", [])
            }

            # Extract body
            body = self._extract_body(msg.get("payload", {}))

            return {
                "id": msg["id"],
                "subject": headers.get("Subject", "(Sin asunto)"),
                "from": headers.get("From", "Desconocido"),
                "to": headers.get("To", ""),
                "date": headers.get("Date", ""),
                "body": body,
                "labels": msg.get("labelIds", []),
            }

        except Exception as e:
            logger.error(f"Error reading message {message_id}: {e}")
            return {"error": str(e)}

    def _extract_body(self, payload: dict) -> str:
        """Recursively extract plain text body from email payload."""
        if payload.get("mimeType") == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        parts = payload.get("parts", [])
        for part in parts:
            result = self._extract_body(part)
            if result:
                return result

        return "(Sin contenido de texto)"

    def send_message(
        self, to: str, subject: str, body: str, cc: str = "", bcc: str = ""
    ) -> dict:
        """Send an email."""
        try:
            service = self._get_service()
            message = MIMEMultipart()
            message["to"] = to
            message["subject"] = subject
            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc
            message.attach(MIMEText(body, "plain"))

            raw = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode("utf-8")

            sent = (
                service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )
            logger.info(f"Email sent to {to}: {sent.get('id')}")
            return {"success": True, "message_id": sent.get("id")}

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {"success": False, "error": str(e)}

    def search_messages(self, query: str, max_results: int = 5) -> list[dict]:
        """Search emails using Gmail query syntax."""
        return self.list_messages(max_results=max_results, query=query)
