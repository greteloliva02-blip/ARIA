import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage

from core.config import Config
from core.memory import MemoryManager
from core.logger import get_logger
from core.dispatcher import ToolDispatcher
from tools.web_tool import get_web_tools

logger = get_logger("agent")

_SYSTEM_TEMPLATE = """\
Eres ARIA, asistente personal por Telegram.

Responde SIEMPRE con un JSON valido (sin markdown, sin texto extra).

Acciones permitidas (solo estas): {action_list}

Ejemplos:

{action_examples}

Reglas:
- usa solo acciones de la lista
- para charla normal usa action "none" con "response"
- para herramientas usa "action" + "data" (sin "response")
- se amable, breve y util

Hechos del usuario:
{user_facts}

Historial reciente:
{memory_context}

Fecha y hora: {current_time}
"""

_ACTION_EXAMPLES = {
    "none": """{
  "action": "none",
  "response": "tu respuesta al usuario en espanol"
}""",
    "web_search": """{
  "action": "web_search",
  "data": { "query": "texto de busqueda", "max_results": 3 }
}""",
    "read_emails": """{
  "action": "read_emails",
  "data": { "query": "is:unread", "max_results": 5 }
}""",
    "send_email": """{
  "action": "send_email",
  "data": { "to": "correo@ejemplo.com", "subject": "Asunto", "body": "Mensaje" }
}""",
    "list_calendar_events": """{
  "action": "list_calendar_events",
  "data": { "days_ahead": 7, "max_results": 10 }
}""",
    "create_calendar_event": """{
  "action": "create_calendar_event",
  "data": {
    "summary": "Reunion",
    "start_time": "2026-05-28T10:00:00",
    "end_time": "2026-05-28T11:00:00",
    "description": ""
  }
}""",
}


def _build_system_prompt(
    registered_tools: list[str],
    user_facts: str,
    memory_context: str,
    current_time: str,
) -> str:
    """Fill prompt placeholders without str.format (JSON braces break .format)."""
    tool_actions = [a for a in registered_tools if a != "none"]
    action_list = ", ".join(['"none"'] + [f'"{a}"' for a in tool_actions])

    example_keys = ["none"] + tool_actions
    blocks = [_ACTION_EXAMPLES[k] for k in example_keys if k in _ACTION_EXAMPLES]
    action_examples = "\n\n".join(blocks) if blocks else _ACTION_EXAMPLES["none"]

    return (
        _SYSTEM_TEMPLATE.replace("{action_list}", action_list)
        .replace("{action_examples}", action_examples)
        .replace("{user_facts}", user_facts)
        .replace("{memory_context}", memory_context)
        .replace("{current_time}", current_time)
    )


class AriaAgent:
    def __init__(self, config: Config, memory: MemoryManager):
        self.config = config
        self.memory = memory
        self.dispatcher = ToolDispatcher()
        self.llm = None
        self.tools = []

        self._init_llm()
        self._load_tools()
        logger.info("Agent ready with %s tool(s).", len(self.tools))

    def _init_llm(self):
        if not self.config.MISTRAL_API_KEY:
            raise RuntimeError("MISTRAL_API_KEY is required.")

        try:
            from langchain_mistralai import ChatMistralAI
            self.llm = ChatMistralAI(
                api_key=self.config.MISTRAL_API_KEY,
                model=self.config.MISTRAL_MODEL,
            )
            logger.info("Mistral LLM ready: %s", self.config.MISTRAL_MODEL)
        except Exception as e:
            logger.error("Failed to init Mistral: %s", e)
            raise RuntimeError(
                "Could not initialize Mistral. Check MISTRAL_API_KEY and MISTRAL_MODEL."
            ) from e

    def _load_tools(self):
        self.tools = []
        try:
            self.tools.append(get_web_tools()[0])
        except Exception as e:
            logger.warning("web_search not loaded: %s", e)

        self.tools.extend(self._load_google_tools_if_ready())
        self.dispatcher.register_tools(self.tools)
        logger.info("Loaded tools: %s", [t.name for t in self.tools])

    def _has_google_credentials(self) -> bool:
        if (os.getenv("GOOGLE_TOKEN_JSON") or "").strip():
            return True
        cred_dir = Path(
            os.getenv(
                "GOOGLE_CREDENTIALS_DIR",
                str(self.config.PROJECT_ROOT / "google_credentials"),
            )
        )
        return (cred_dir / "token.json").exists()

    def _load_google_tools_if_ready(self) -> list:
        if os.getenv("DISABLE_GOOGLE", "").lower() in ("1", "true", "yes", "on"):
            logger.info("Google tools disabled (DISABLE_GOOGLE).")
            return []
        if not self._has_google_credentials():
            logger.info("No Google token; Gmail/Calendar disabled.")
            return []
        try:
            from tools.gmail_tool import get_gmail_tools
            from tools.calendar_tool import get_calendar_tools
        except ImportError:
            logger.warning(
                "Google API packages missing. Install: pip install -r requirements.txt"
            )
            return []

        tools = get_gmail_tools() + get_calendar_tools()
        logger.info("Google OK — Gmail + Calendar enabled.")
        return tools

    async def process_message(self, user_id: str, message: str) -> str:
        try:
            await asyncio.to_thread(self.memory.save_message, user_id, "human", message)

            history = await asyncio.to_thread(self.memory.get_history, user_id, 10)
            facts = await asyncio.to_thread(self.memory.get_facts, user_id)
            facts_str = (
                "\n".join(f"- {k}: {v}" for k, v in facts.items())
                if facts
                else "Sin datos guardados."
            )
            memory_ctx = "\n".join(
                f"{h['role']}: {h['content'][:200]}" for h in history[-6:]
            ) or "Sin historial."

            now = datetime.now()
            days = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
            current_time = f"{days[now.weekday()]}, {now.strftime('%d/%m/%Y %H:%M')}"

            messages = [
                SystemMessage(
                    content=_build_system_prompt(
                        self.dispatcher.get_registered_actions(),
                        facts_str,
                        memory_ctx,
                        current_time,
                    )
                ),
                HumanMessage(content=message),
            ]

            raw = await self._call_llm(messages)
            reply = await self._handle_llm_output(raw)

            await asyncio.to_thread(self.memory.save_message, user_id, "assistant", reply)
            await asyncio.to_thread(self._extract_facts, user_id, message)
            return reply
        except Exception as e:
            logger.error("Agent error: %s", e, exc_info=True)
            return "Hubo un error procesando tu mensaje. Intenta de nuevo."

    async def _call_llm(self, messages) -> str:
        try:
            response = await self.llm.ainvoke(messages)
            return self._normalize_llm_content(response)
        except Exception as e:
            logger.error("LLM error: %s", e)
            return json.dumps(
                {
                    "action": "none",
                    "response": "No pude conectar con Mistral en este momento. Intenta de nuevo en unos segundos.",
                },
                ensure_ascii=False,
            )

    def _normalize_llm_content(self, response) -> str:
        content = getattr(response, "content", response)
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
                else:
                    parts.append(str(block))
            content = "".join(parts)
        return (content or "").strip() or json.dumps(
            {"action": "none", "response": "Sin respuesta"}, ensure_ascii=False
        )

    async def _handle_llm_output(self, raw: str) -> str:
        intent = self._parse_json(raw)
        if not isinstance(intent, dict):
            return raw

        action = str(intent.get("action", "none")).strip()
        if action == "none":
            return str(intent.get("response", raw)).strip() or raw

        registered = self.dispatcher.get_registered_actions()
        if action in registered:
            data = intent.get("data", {})
            if not isinstance(data, dict):
                data = {}
            return await self.dispatcher.dispatch(action, data)

        logger.warning("Unknown action '%s', using text fallback.", action)
        return str(intent.get("response", raw)).strip() or raw

    def _parse_json(self, raw: str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
        return None

    def _extract_facts(self, user_id: str, message: str):
        for indicator, key in [("me llamo", "nombre"), ("mi nombre es", "nombre"), ("vivo en", "ubicacion")]:
            lower = message.lower()
            if indicator in lower:
                idx = lower.index(indicator) + len(indicator)
                value = message[idx:].strip().split(".")[0].split(",")[0][:80]
                if value:
                    self.memory.save_fact(user_id, key, value)
