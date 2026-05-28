"""
ARIA — Interfaz Base Abstracta
Para soportar Telegram, WhatsApp y futuras interfaces.
"""
from abc import ABC, abstractmethod


class BaseInterface(ABC):
    """Abstract base class for all messaging interfaces."""

    @abstractmethod
    async def start(self):
        """Start the interface (connect, begin polling, etc.)."""
        ...

    @abstractmethod
    async def stop(self):
        """Gracefully stop the interface."""
        ...

    @abstractmethod
    async def send_message(self, user_id: str, message: str):
        """Send a proactive message to a user."""
        ...
