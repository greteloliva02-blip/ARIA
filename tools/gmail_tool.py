"""
ARIA - Gmail Tools
LangChain tool wrappers for GmailService.
"""
from langchain_core.tools import tool
from services.google.gmail import GmailService
from core.config import Config

_gmail_service = None

def _get_service():
    global _gmail_service
    if _gmail_service is None:
        _gmail_service = GmailService(Config())
    return _gmail_service

@tool
def read_emails(query: str = "in:inbox", max_results: int = 5) -> str:
    """
    Lista y lee los correos electronicos recientes de Gmail.
    Usa 'query' para buscar correos (ej: 'is:unread', 'from:jefe@empresa.com').
    Retorna un resumen de los correos encontrados o un error.
    """
    try:
        svc = _get_service()
        if not svc.is_ready():
            return "Error: Servicio de Gmail no autenticado. Inicia el flujo OAuth primero."
        
        emails = svc.list_messages(max_results=max_results, query=query)
        if not emails:
            return "No se encontraron correos."
        
        if "error" in emails[0]:
            return f"Error leyendo correos: {emails[0]['error']}"
            
        result = "Correos encontrados:\n"
        for email in emails:
            result += f"- ID: {email['id']} | De: {email['from']} | Asunto: {email['subject']}\n"
        return result
    except Exception as e:
        return f"Error: {e}"

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """
    Envia un correo electronico mediante Gmail.
    Requiere destinatario (to), asunto (subject) y cuerpo (body).
    """
    try:
        svc = _get_service()
        if not svc.is_ready():
            return "Error: Servicio de Gmail no autenticado. Inicia el flujo OAuth primero."
            
        # IMPORTANT: in a real bot, we might want user confirmation before sending.
        # For now, it sends directly.
        res = svc.send_message(to, subject, body)
        if res.get("success"):
            return f"Correo enviado exitosamente (ID: {res.get('message_id')})."
        else:
            return f"Error enviando correo: {res.get('error')}"
    except Exception as e:
        return f"Error: {e}"

def get_gmail_tools():
    """Return all Gmail tools."""
    return [read_emails, send_email]
