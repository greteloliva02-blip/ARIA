import unittest
from unittest.mock import AsyncMock, MagicMock

from core.config import Config
from core.memory import MemoryManager
from core.morning_briefing import (
    build_fallback_message,
    gather_briefing_context,
    process_morning_briefing,
)


class MorningBriefingTests(unittest.IsolatedAsyncioTestCase):
    async def test_process_morning_briefing_dispatches_send_telegram(self):
        config = Config()
        memory = MemoryManager(config)

        agent = MagicMock()
        agent.llm = AsyncMock()
        agent.llm.ainvoke.return_value = MagicMock(
            content='{"action":"send_telegram_message","data":{"message":"🌅 Morning Briefing\\n\\nTest"}}'
        )
        agent.dispatcher = MagicMock()
        agent.dispatcher.is_registered_action.return_value = True
        agent.dispatcher.dispatch = AsyncMock(return_value="Mensaje enviado.")

        result = await process_morning_briefing(agent, memory, config)
        self.assertIn("enviado", result.lower())
        agent.dispatcher.dispatch.assert_awaited_once()
        args = agent.dispatcher.dispatch.await_args.args
        self.assertEqual(args[0], "send_telegram_message")
        self.assertIn("message", args[1])

    def test_fallback_message_structure(self):
        ctx = (
            "[WEATHER]\nSoleado\n\n"
            "[NEWS]\n- Noticia 1\n\n"
            "[CALENDAR_TODAY]\n- 10:00 Reunion\n\n"
            "[TASKS]\nNo data available\n\n"
            "[REMINDERS]\n- Recordatorio\n"
        )
        msg = build_fallback_message(ctx)
        self.assertIn("Morning Briefing", msg)
        self.assertIn("Weather", msg)
        self.assertIn("News", msg)


if __name__ == "__main__":
    unittest.main()
