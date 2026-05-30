"""
PlatformAdapter — Abstract Base Class (Hook Contract)

The Core calls ONLY these 4 methods. Adapter implementations subclass this.
The Core never imports any platform SDK (playwright, baileys, etc.) directly.

Adapters are registered with AdapterLoader and instantiated on demand.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from omnikernal.packet.contracts.message import Message
    from omnikernal.core.packet import IntentPacket


class PlatformAdapter(ABC):
    """
    Hook contract between the Core and a platform.

    The Core boots by calling connect(), polls via fetch_new_messages(),
    pipes replies through send_message(), and shuts down with disconnect().
    The Core never sees the underlying SDK — only this interface.
    """

    @abstractmethod
    def __init__(self, **kwargs: Any) -> None: ...

    @abstractmethod
    async def connect(self) -> bool:
        """
        Start the platform session.

        Open a browser, connect a WebSocket, authenticate via API —
        whatever the platform requires. Core calls this once on boot.

        return : True if connection is successful , False otherwise.
        """
        ...

    @abstractmethod
    async def is_connected(self) -> bool:
        """
        Check if the platform session is connected.

        Required for Monitor Health over Adapter for Advance WatchDog.
        """
        ...

    @abstractmethod
    async def fetch_new_messages(self) -> AsyncIterator[Message]:
        """
        Async generator that yields inbound messages.

        Implement using `async def` + `yield`. The AdapterManager polls
        this indefinitely while the adapter is connected.

        Example:
            async def fetch_new_messages(self) -> AsyncIterator[Message]:
                while self._connected:
                    for msg in await self.platform.get_messages():
                        yield msg
                    await asyncio.sleep(0.1)
        """
        # Required to make this an abstract async generator
        return
        yield  # noqa: unreachable — makes mypy treat this as AsyncIterator

    @abstractmethod
    async def send_message(self, packet: IntentPacket) -> bool:
        """
        Send a reply to a user.

        Core calls this when a handler returns CommandResult.reply.
        Implementation types into a chat box, emits to a socket,
        POSTs to an API — whatever the platform requires.

        Args:
            packet : IntentPacket , full obj access mutation , gives more flexible options.

        returns : True if message is sent successfully , False otherwise.
        """
        ...

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Tear down the session cleanly.

        Close the browser, disconnect the WebSocket, release resources.
        Core calls this on shutdown.

        return : True if session is disconnected successfully , False otherwise.
        """
        ...

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """
        Return the platform identifier string.

        Examples: 'whatsapp', 'telegram', 'discord'.
        Used by the Core for logging and adapter registry lookup.
        """
        raise NotImplementedError
