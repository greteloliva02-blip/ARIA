"""
ARIA — Scheduler de Tareas
Recordatorios automáticos, resumen diario, tareas periódicas.
"""
import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from core.config import Config
from core.memory import MemoryManager
from core.morning_briefing import process_morning_briefing
from core.logger import get_logger

logger = get_logger("scheduler")


class TaskScheduler:
    """Manages periodic tasks: reminder checks, daily summaries, etc."""

    def __init__(self, config: Config, memory: MemoryManager, send_fn=None, agent=None):
        """
        Args:
            config:  Global configuration.
            memory:  Memory manager instance.
            send_fn: Async callable(user_id, message) to send notifications.
            agent:   AriaAgent instance for morning briefing LLM + dispatcher.
        """
        self.config = config
        self.memory = memory
        self.send_fn = send_fn
        self.agent = agent
        self.scheduler = AsyncIOScheduler()

    def _parse_briefing_time(self) -> tuple[int, int]:
        raw = (self.config.MORNING_BRIEFING_TIME or "08:00").strip()
        try:
            hour_str, minute_str = raw.split(":", 1)
            hour = int(hour_str)
            minute = int(minute_str)
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return hour, minute
        except Exception:
            pass
        logger.warning("Invalid MORNING_BRIEFING_TIME '%s', using 08:00", raw)
        return 8, 0

    async def start(self):
        """Start the scheduler with default jobs."""

        # Check reminders every 60 seconds
        self.scheduler.add_job(
            self._check_reminders,
            IntervalTrigger(seconds=60),
            id="check_reminders",
            replace_existing=True,
        )

        if self.config.MORNING_BRIEFING_ENABLED and self.agent is not None:
            hour, minute = self._parse_briefing_time()
            self.scheduler.add_job(
                self._run_morning_briefing,
                CronTrigger(hour=hour, minute=minute),
                id="morning_briefing",
                replace_existing=True,
            )
            logger.info(
                "Morning briefing scheduled daily at %02d:%02d (local time).",
                hour,
                minute,
            )
        else:
            logger.info("Morning briefing scheduler disabled or agent unavailable.")

        self.scheduler.start()
        logger.info("Scheduler started (reminder check every 60s)")

    async def stop(self):
        """Shutdown the scheduler."""
        self.scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")

    async def _check_reminders(self):
        """Check for due reminders and send notifications."""
        try:
            pending = self.memory.get_pending_reminders()
            for r in pending:
                msg = (
                    f"⏰ **¡Recordatorio!**\n\n"
                    f"📌 {r['message']}\n"
                    f"📅 Programado para: {r['remind_at']}"
                )

                if self.send_fn:
                    try:
                        await self.send_fn(r["user_id"], msg)
                        logger.info(f"Reminder #{r['id']} sent to {r['user_id']}")
                    except Exception as e:
                        logger.error(f"Failed to send reminder #{r['id']}: {e}")

                self.memory.complete_reminder(r["id"])

        except Exception as e:
            logger.error(f"Reminder check error: {e}")

    async def _run_morning_briefing(self):
        """Daily automated morning briefing via LLM JSON + dispatcher."""
        try:
            logger.info("Scheduled morning_briefing job started.")
            await process_morning_briefing(self.agent, self.memory, self.config)
            logger.info("Scheduled morning_briefing job completed.")
        except Exception as e:
            logger.error("Morning briefing job failed (non-fatal): %s", e, exc_info=True)
