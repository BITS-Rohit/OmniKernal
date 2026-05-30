"""
MockAdapter — In-Memory Testing Adapter

A zero-dependency adapter for smoke tests and CI.
Implements the full PlatformAdapter contract using in-memory event-driven asyncio queues.
No SDK, no browser, no network — purely synthetic.
"""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from omnikernal.packet.contracts.intent_packet import IntentPacket
from omnikernal.packet.contracts.message import Message
from omnikernal.packet.contracts.user import ROLE, User
from omnikernal.plugin.interfaces import PlatformAdapter


class MockAdapter(PlatformAdapter):
    """
    Mock adapter for testing the Core lifecycle without any platform SDK.

    Preload messages into the queue via `inject_message()`,
    then let the Core poll them through `fetch_new_messages()`.
    Sent replies are stored in `sent_messages` for assertion.
    """

    def __init__(self, **kwargs: Any) -> None:
        self._platform_name = "console"
        self._message_queue: asyncio.Queue[Message] = asyncio.Queue()
        self.sent_messages: list[str] = []
        self._connected = False
        self._shutdown_event = asyncio.Event()

    @property
    def platform_name(self) -> str:
        return self._platform_name

    async def connect(self) -> bool:
        self._connected = True
        print("[MockAdapter] Connected to virtual console.")
        return True

    async def is_connected(self) -> bool:
        return self._connected

    async def disconnect(self) -> bool:
        self._connected = False
        self._shutdown_event.set()
        print("[MockAdapter] Disconnected.")
        return True

    async def fetch_new_messages(self) -> AsyncIterator[Message]:
        """Yields messages from the queue natively without polling."""
        try:
            while not self._shutdown_event.is_set():
                msg = await self._message_queue.get()
                yield msg
                self._message_queue.task_done()
        except asyncio.CancelledError:
            pass

    async def send_message(self, packet: IntentPacket) -> bool:
        if packet.result is None or packet.result.reply is None:
            return False

        reply = packet.result.reply
        print(f"\n[OUTPUT to {packet.user.display_name}] -> {reply}\n")
        self.sent_messages.append(reply)
        return True

    def inject_message(self, raw_text: str, user_id: str = "test_user") -> None:
        """
        Injects a synthetic message into the adapter's queue for testing.

        Args:
            raw_text: The command string (e.g. "!echo hello").
            user_id: The simulated user ID.
        """
        msg = Message(
            id=f"mock_{self._message_queue.qsize()}",
            raw_text=raw_text,
            user=User(id=user_id, display_name="TestUser", platform="console", role=ROLE.ADMIN),
            timestamp=datetime.now(UTC),
            platform="console",
            adapter=self,
        )
        self._message_queue.put_nowait(msg)
