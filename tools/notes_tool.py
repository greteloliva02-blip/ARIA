"""
ARIA — Herramientas de Notas y Recordatorios
Crear, listar, buscar notas y recordatorios.
"""
from datetime import datetime, timedelta
import json
import re
from pathlib import Path

from langchain_core.tools import tool

from core.config import Config
from core.logger import get_logger

logger = get_logger("tools.notes")
_config = Config()
_notes_dir = _config.PROJECT_ROOT / "data" / "notes"
_notes_dir.mkdir(parents=True, exist_ok=True)


@tool
def create_note(title: str, content: str) -> str:
    """Crea una nota nueva y la guarda en disco.

    Args:
        title: Título de la nota (se usa como nombre de archivo).
        content: Contenido de la nota.
    """
    safe_name = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{safe_name}.md"
    filepath = _notes_dir / filename

    note_content = (
        f"# {title}\n"
        f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        f"{content}\n"
    )

    filepath.write_text(note_content, encoding="utf-8")
    logger.info(f"Note created: {filename}")
    return f"📝 Nota creada: **{title}**\n📁 Guardada en: {filepath}"


@tool
def list_notes() -> str:
    """Lista todas las notas guardadas."""
    notes = sorted(_notes_dir.glob("*.md"), reverse=True)
    if not notes:
        return "📝 No hay notas guardadas aún."

    output = "📝 **Notas guardadas:**\n\n"
    for n in notes[:20]:
        # Extract title from first line
        first_line = n.read_text(encoding="utf-8").splitlines()[0]
        title = first_line.replace("# ", "").strip()
        date = n.stem[:8]
        try:
            formatted_date = datetime.strptime(date, "%Y%m%d").strftime("%d/%m/%Y")
        except ValueError:
            formatted_date = "?"
        output += f"• **{title}** ({formatted_date})\n"

    return output


@tool
def read_note(search_term: str) -> str:
    """Busca y lee una nota por su título o contenido.

    Args:
        search_term: Texto a buscar en el título o contenido de las notas.
    """
    notes = list(_notes_dir.glob("*.md"))
    for n in notes:
        content = n.read_text(encoding="utf-8")
        if search_term.lower() in content.lower() or search_term.lower() in n.name.lower():
            return f"📝 **Nota encontrada:**\n\n{content}"

    return f"🔍 No se encontró ninguna nota con '{search_term}'"


@tool
def create_reminder(message: str, when: str) -> str:
    """Crea un recordatorio. El sistema notificará al usuario a la hora indicada.

    Args:
        message: Mensaje del recordatorio (ej: 'Llamar a Marta').
        when: Cuándo recordar. Formatos aceptados:
              - 'en 30 minutos', 'en 2 horas', 'en 1 dia'
              - '2024-12-25 15:00' (fecha y hora exacta)
              - 'mañana a las 9', 'hoy a las 17'
    """
    # Import here to avoid circular
    from core.memory import MemoryManager
    from core.config import Config

    config = Config()
    memory = MemoryManager(config)

    now = datetime.now()
    remind_at = None

    when_lower = when.lower().strip()

    # Parse relative time: "en X minutos/horas/dias"
    match = re.search(r'en\s+(\d+)\s+(minuto|hora|dia|día|min|h)', when_lower)
    if match:
        amount = int(match.group(1))
        unit = match.group(2)
        if unit in ("minuto", "min"):
            remind_at = now + timedelta(minutes=amount)
        elif unit in ("hora", "h"):
            remind_at = now + timedelta(hours=amount)
        elif unit in ("dia", "día"):
            remind_at = now + timedelta(days=amount)

    # Parse "mañana a las X"
    if not remind_at:
        match = re.search(r'mañana\s+a\s+las?\s+(\d{1,2})(?::(\d{2}))?', when_lower)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            tomorrow = now + timedelta(days=1)
            remind_at = tomorrow.replace(hour=hour, minute=minute, second=0)

    # Parse "hoy a las X"
    if not remind_at:
        match = re.search(r'hoy\s+a\s+las?\s+(\d{1,2})(?::(\d{2}))?', when_lower)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            remind_at = now.replace(hour=hour, minute=minute, second=0)

    # Parse exact datetime
    if not remind_at:
        for fmt in ["%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M", "%Y-%m-%d"]:
            try:
                remind_at = datetime.strptime(when_lower, fmt)
                break
            except ValueError:
                continue

    if not remind_at:
        return (
            f"❌ No pude entender la fecha: '{when}'\n"
            f"Formatos válidos:\n"
            f"• 'en 30 minutos'\n"
            f"• 'mañana a las 9'\n"
            f"• '2024-12-25 15:00'"
        )

    rid = memory.add_reminder("default", message, remind_at)
    formatted = remind_at.strftime("%d/%m/%Y a las %H:%M")
    return f"⏰ Recordatorio #{rid} creado:\n📌 **{message}**\n📅 {formatted}"


@tool
def list_reminders() -> str:
    """Lista todos los recordatorios pendientes."""
    from core.memory import MemoryManager
    from core.config import Config

    config = Config()
    memory = MemoryManager(config)
    reminders = memory.get_all_reminders("default")

    if not reminders:
        return "⏰ No hay recordatorios pendientes."

    output = "⏰ **Recordatorios pendientes:**\n\n"
    for r in reminders:
        try:
            dt = datetime.fromisoformat(r["remind_at"])
            formatted = dt.strftime("%d/%m/%Y %H:%M")
        except (ValueError, TypeError):
            formatted = r["remind_at"]
        output += f"• #{r['id']} — **{r['message']}** → {formatted}\n"

    return output


@tool
def get_current_datetime() -> str:
    """Obtiene la fecha y hora actual del sistema."""
    now = datetime.now()
    days_es = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado",
        "Sunday": "Domingo"
    }
    day_name = days_es.get(now.strftime("%A"), now.strftime("%A"))
    return (
        f"📅 **{day_name}, {now.strftime('%d/%m/%Y')}**\n"
        f"🕐 {now.strftime('%H:%M:%S')}"
    )


def get_notes_tools() -> list:
    """Return all notes & reminder tools."""
    return [
        create_note,
        list_notes,
        read_note,
        create_reminder,
        list_reminders,
        get_current_datetime,
    ]
