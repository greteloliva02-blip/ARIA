"""
ARIA — Scheduled morning briefing automation.
Scheduler -> process_morning_briefing -> LLM JSON -> dispatcher -> Telegram
"""
import asyncio
import json
import re
from datetime import datetime

import httpx
from langchain_core.messages import HumanMessage, SystemMessage

from core.config import Config
from core.logger import get_logger
from core.memory import MemoryManager
from tools.calendar_tool import list_calendar_events
from tools.web_tool import web_news

logger = get_logger("morning_briefing")

MORNING_BRIEFING_PROMPT = """\
Eres ARIA generando el briefing matutino automatizado.
Debes devolver SOLO un objeto JSON valido, sin markdown ni texto extra.

Formato obligatorio:
{
  "action": "send_telegram_message",
  "data": {
    "message": "texto completo del briefing"
  }
}

Reglas:
- action debe ser exactamente "send_telegram_message"
- message debe seguir esta estructura:

🌅 Morning Briefing

🌤 Weather:
- ...

📰 News:
- ...

📅 Today:
- ...

✅ Tasks:
- ...

🔔 Reminders:
- ...

💡 Focus:
- ...

- Usa los datos provistos; si una seccion no tiene datos, escribe "No data available"
- Noticias: 3-5 bullets cortos
- Focus: 1 sugerencia breve y practica (sin cliches)
- Responde en espanol
"""


def _extract_json_payload(raw_content: str) -> dict | None:
    text = (raw_content or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    return None


def _fetch_weather(location: str) -> str:
    loc = (location or "").strip() or "auto"
    try:
        url = f"https://wttr.in/{loc}?format=3"
        resp = httpx.get(url, timeout=12.0)
        resp.raise_for_status()
        line = resp.text.strip()
        return line if line else "No data available"
    except Exception as e:
        logger.warning("Weather fetch failed: %s", e)
        return "No data available"


def _fetch_news(topics: list[str], max_per_topic: int = 3) -> str:
    lines = []
    try:
        general = web_news.invoke({"topic": "world news", "max_results": max_per_topic})
        if general and not general.startswith("❌"):
            lines.append("General:")
            for ln in general.splitlines():
                if ln.strip().startswith(("**", "📅", "🔗", "-")):
                    lines.append(ln.strip()[:200])
        else:
            lines.append("- No data available")
    except Exception as e:
        logger.warning("General news failed: %s", e)
        lines.append("- No data available")

    for topic in topics[:2]:
        topic = topic.strip()
        if not topic:
            continue
        try:
            part = web_news.invoke({"topic": topic, "max_results": 2})
            if part and not part.startswith("❌"):
                lines.append(f"Interes ({topic}):")
                for ln in part.splitlines()[:6]:
                    if ln.strip().startswith(("**", "📅")):
                        lines.append(ln.strip()[:180])
        except Exception as e:
            logger.warning("Topic news failed (%s): %s", topic, e)
    return "\n".join(lines) if lines else "No data available"


def _fetch_calendar_today() -> str:
    try:
        raw = list_calendar_events.invoke({"days_ahead": 1, "max_results": 20})
        if not raw or raw.startswith("Error"):
            return "No data available"
        today = datetime.now().date()
        lines = []
        for ln in raw.splitlines():
            if "|" not in ln:
                continue
            if str(today) in ln or today.strftime("%Y-%m-%d") in ln:
                lines.append(ln.strip())
        if not lines and "Próximos eventos" in raw:
            # Include upcoming if date filter misses timezone formatting
            for ln in raw.splitlines():
                if ln.strip().startswith("-"):
                    lines.append(ln.strip())
        return "\n".join(lines[:12]) if lines else "No data available"
    except Exception as e:
        logger.warning("Calendar briefing failed: %s", e)
        return "No data available"


def _fetch_reminders(memory: MemoryManager, user_id: str) -> str:
    try:
        reminders = memory.get_all_reminders(user_id)
        if not reminders:
            return "No data available"
        lines = []
        for r in reminders[:10]:
            lines.append(f"- #{r['id']} {r['message']} ({r['remind_at']})")
        return "\n".join(lines)
    except Exception as e:
        logger.warning("Reminders briefing failed: %s", e)
        return "No data available"


def _fetch_tasks_placeholder(memory: MemoryManager, user_id: str) -> str:
    """Tasks table may not exist; use pending reminders + facts as proxy."""
    try:
        facts = memory.get_facts(user_id)
        task_like = [f"- {k}: {v}" for k, v in facts.items() if "task" in k.lower() or "tarea" in k.lower()]
        if task_like:
            return "\n".join(task_like[:10])
        return "No data available (usa recordatorios como pendientes)"
    except Exception as e:
        logger.warning("Tasks briefing failed: %s", e)
        return "No data available"


def gather_briefing_context(memory: MemoryManager, config: Config, user_id: str) -> str:
    facts = memory.get_facts(user_id)
    location = facts.get("ubicación") or facts.get("ubicacion") or facts.get("ciudad") or config.MORNING_BRIEFING_LOCATION
    interest_raw = facts.get("intereses") or facts.get("interests") or ""
    topics = [t.strip() for t in interest_raw.split(",") if t.strip()]

    weather = _fetch_weather(location)
    news = _fetch_news(topics)
    calendar = _fetch_calendar_today()
    tasks = _fetch_tasks_placeholder(memory, user_id)
    reminders = _fetch_reminders(memory, user_id)

    return (
        f"Fecha: {datetime.now().strftime('%A %d/%m/%Y %H:%M')}\n"
        f"Usuario: {user_id}\n\n"
        f"[WEATHER]\n{weather}\n\n"
        f"[NEWS]\n{news}\n\n"
        f"[CALENDAR_TODAY]\n{calendar}\n\n"
        f"[TASKS]\n{tasks}\n\n"
        f"[REMINDERS]\n{reminders}\n"
    )


def build_fallback_message(context: str) -> str:
    """Deterministic briefing if LLM JSON fails."""
    def section(name: str) -> str:
        marker = f"[{name}]"
        if marker not in context:
            return "No data available"
        part = context.split(marker, 1)[1]
        for other in ["[WEATHER]", "[NEWS]", "[CALENDAR_TODAY]", "[TASKS]", "[REMINDERS]"]:
            if other != marker and other in part:
                part = part.split(other, 1)[0]
        return part.strip() or "No data available"

    return (
        "🌅 Morning Briefing\n\n"
        f"🌤 Weather:\n{section('WEATHER')}\n\n"
        f"📰 News:\n{section('NEWS')}\n\n"
        f"📅 Today:\n{section('CALENDAR_TODAY')}\n\n"
        f"✅ Tasks:\n{section('TASKS')}\n\n"
        f"🔔 Reminders:\n{section('REMINDERS')}\n\n"
        "💡 Focus:\n- Prioriza una sola tarea importante antes del mediodia."
    )


async def process_morning_briefing(agent, memory: MemoryManager, config: Config) -> str:
    """
    Generate morning briefing via LLM JSON intent and dispatch send_telegram_message.
    Never raises; always attempts delivery.
    """
    logger.info("Morning briefing scheduled trigger fired.")
    user_id = str(config.TELEGRAM_USER_ID or "default")
    context = await asyncio.to_thread(gather_briefing_context, memory, config, user_id)
    logger.info("Morning briefing context gathered (%d chars).", len(context))

    message_text = build_fallback_message(context)
    intent = None

    try:
        messages = [
            SystemMessage(content=MORNING_BRIEFING_PROMPT),
            HumanMessage(
                content=(
                    "Genera el JSON de envio Telegram usando estos datos:\n\n"
                    f"{context}"
                )
            ),
        ]
        response = await agent.llm.ainvoke(messages)
        raw = response.content if hasattr(response, "content") else str(response)
        intent = _extract_json_payload(raw)
        if isinstance(intent, dict):
            action = intent.get("action", "")
            data = intent.get("data", {})
            if action == "send_telegram_message" and isinstance(data, dict) and data.get("message"):
                message_text = str(data["message"])
                logger.info("Morning briefing LLM JSON parsed successfully.")
            else:
                logger.warning("Morning briefing LLM JSON invalid action/data; using fallback message.")
        else:
            logger.warning("Morning briefing LLM did not return JSON; using fallback message.")
    except Exception as e:
        logger.warning("Morning briefing LLM failed: %s", e)

    if not agent.dispatcher.is_registered_action("send_telegram_message"):
        logger.error("send_telegram_message not registered in dispatcher.")
        return "Error: send_telegram_message no registrada."

    dispatch_data = {"message": message_text, "user_id": user_id}
    try:
        result = await agent.dispatcher.dispatch("send_telegram_message", dispatch_data)
        logger.info("Morning briefing dispatch result: %s", result[:120])
        return result
    except Exception as e:
        logger.error("Morning briefing dispatch failed: %s", e)
        return f"Error dispatching morning briefing: {e}"
