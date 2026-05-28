import json
import os
from datetime import datetime

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from core.config import Config
from core.memory import MemoryManager
from core.logger import get_logger
from core.dispatcher import ToolDispatcher

from tools.web_tool import get_web_tools

logger = get_logger("agent")

MINIMAL_SYSTEM_PROMPT = """\
Eres ARIA, asistente personal por Telegram.

Responde SIEMPRE con un JSON valido (sin markdown, sin texto extra):

{
  "action": "none",
  "response": "tu respuesta al usuario en espanol"
}

Si necesitas buscar en internet usa:

{
  "action": "web_search",
  "data": { "query": "texto de busqueda", "max_results": 3 }
}

Reglas:
- action solo puede ser "none" o "web_search"
- nunca inventes otras acciones
- se amable, breve y util

Hechos del usuario:
{user_facts}

Historial reciente:
{memory_context}

Fecha y hora: {current_time}
"""


class AriaAgent:
    """Minimal agent: Mistral + manual JSON dispatch."""

    def __init__(self, config: Config, memory: MemoryManager):
        self.config = config
        self.memory = memory
        self.dispatcher = ToolDispatcher()
        self.tools = []

        if not config.MISTRAL_API_KEY:
            raise RuntimeError("MISTRAL_API_KEY is required.")

        from langchain_mistralai import ChatMistralAI

        self.llm = ChatMistralAI(
            api_key=config.MISTRAL_API_KEY,
            model=config.MISTRAL_MODEL,
        )
        logger.info("Using Mistral model: %s", config.MISTRAL_MODEL)

        self._load_tools()
        logger.info("Agent ready with %s tool(s).", len(self.tools))

    def _load_tools(self):
        try:
            self.tools = get_web_tools()
            logger.info("Loaded web tools: %s", [t.name for t in self.tools])
        except Exception as e:
            logger.warning("Web tools not loaded: %s", e)
            self.tools = []
        self.dispatcher.register_tools(self.tools)

    async def process_message(self, user_id: str, message: str) -> str:
        try:
            self.memory.save_message(user_id, "human", message)

            history = self.memory.get_history(user_id, limit=10)
            facts = self.memory.get_facts(user_id)
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

            system = SystemMessage(
                content=MINIMAL_SYSTEM_PROMPT.format(
                    user_facts=facts_str,
                    memory_context=memory_ctx,
                    current_time=current_time,
                )
            )
            messages = [system, HumanMessage(content=message)]

            try:
                response = await self.llm.ainvoke(messages)
                raw = response.content if hasattr(response, "content") else str(response)
            except Exception as e:
                logger.error("LLM error: %s", e)
                return "No pude conectar con el modelo. Intenta de nuevo en un momento."

            raw = (raw or "").strip() or '{"action":"none","response":"Sin respuesta"}'
            reply = await self._handle_llm_output(raw)

            self.memory.save_message(user_id, "assistant", reply)
            self._extract_facts(user_id, message)
            return reply
        except Exception as e:
            logger.error("Agent error: %s", e, exc_info=True)
            return "Hubo un error procesando tu mensaje. Intenta de nuevo."

    async def _handle_llm_output(self, raw: str) -> str:
        intent = self._parse_json(raw)
        if not isinstance(intent, dict):
            return raw

        action = str(intent.get("action", "none")).strip()
        if action == "none":
            return str(intent.get("response", raw)).strip() or raw

        if action == "web_search" and action in self.dispatcher.get_registered_actions():
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
        import re
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
        return None

    def _extract_facts(self, user_id: str, message: str):
        indicators = {
            "me llamo": "nombre",
            "mi nombre es": "nombre",
            "vivo en": "ubicacion",
        }
        lower = message.lower()
        for indicator, key in indicators.items():
            if indicator in lower:
                idx = lower.index(indicator) + len(indicator)
                value = message[idx:].strip().split(".")[0].split(",")[0][:80]
                if value:
                    self.memory.save_fact(user_id, key, value)