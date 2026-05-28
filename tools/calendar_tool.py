"""
ARIA - Calendar Tools
LangChain tool wrappers for CalendarService.
"""
from langchain_core.tools import tool
from services.google.calendar import CalendarService
from core.config import Config

_calendar_service = None

def _get_service():
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = CalendarService(Config())
    return _calendar_service

@tool
def list_calendar_events(days_ahead: int = 7, max_results: int = 10) -> str:
    """
    Lista los próximos eventos en Google Calendar.
    days_ahead especifica cuántos días a futuro buscar.
    """
    try:
        svc = _get_service()
        if not svc.is_ready():
            return "Error: Servicio de Calendar no autenticado. Inicia el flujo OAuth primero."
            
        events = svc.list_events(max_results=max_results, days_ahead=days_ahead)
        if not events:
            return "No hay próximos eventos programados."
            
        if "error" in events[0]:
            return f"Error leyendo calendario: {events[0]['error']}"
            
        result = "Próximos eventos:\n"
        for ev in events:
            result += f"- {ev['start']} | {ev['summary']}\n"
        return result
    except Exception as e:
        return f"Error: {e}"

@tool
def create_calendar_event(summary: str, start_time: str, end_time: str, description: str = "") -> str:
    """
    Crea un evento en Google Calendar.
    start_time y end_time deben estar en formato ISO 8601 (ej: '2026-05-27T10:00:00').
    summary es el título del evento.
    """
    try:
        svc = _get_service()
        if not svc.is_ready():
            return "Error: Servicio de Calendar no autenticado."
            
        res = svc.create_event(summary, start_time, end_time, description)
        if res.get("success"):
            return f"Evento creado exitosamente. Enlace: {res.get('link')}"
        else:
            return f"Error creando evento: {res.get('error')}"
    except Exception as e:
        return f"Error: {e}"

def get_calendar_tools():
    """Return all Calendar tools."""
    return [list_calendar_events, create_calendar_event]
