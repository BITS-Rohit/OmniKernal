"""
Global Broker is Packet Processing's global Queue...
"""

import asyncio
from logging import Logger, LoggerAdapter
from typing import Any

from omnikernal.omni_logger import omni_logger
from omnikernal.packet.contracts import IntentPacket, Message, PacketState
from omnikernal.packet.interfaces import BaseLayer


class GlobalBroker:
    # Todo , implement a singleton pattern
    # Todo, add cache for queue dropped without processing , from task_done() and put() rejection.

    __slots__ = ("queue", "dispatcher", "logger", "routing_cache")

    def __init__(
        self,
        routing_cache: dict[str, Any],
        max_queue_size: int = 10000,
        logger: Logger | LoggerAdapter[Any] | None = None,
    ):
        self.routing_cache = routing_cache
        self.queue: asyncio.Queue[IntentPacket] = asyncio.Queue(maxsize=max_queue_size)
        self.dispatcher: list[BaseLayer] = self._create_layers()
        self.logger = logger or omni_logger

    async def push(
        self,
        message: Message,
        flags: dict[str, Any] | None = None,
        logger: Logger | LoggerAdapter[Any] | None = None,
    ) -> None:
        if logger is None:
            logger = self.logger
        packet = IntentPacket(
            message=message,
            logger=logger,
            flags=dict(flags) if flags else {},
        )
        await self.queue.put(packet)

    async def start(self) -> asyncio.Task:  # type: ignore[type-arg]
        return asyncio.create_task(self._consumer())

    async def _consumer(self) -> None:
        while True:
            packet = await self.queue.get()
            try:
                for layer in self.dispatcher:
                    # Short-circuit: no further processing for terminal states
                    if packet.state == PacketState.DROPPED:
                        break
                    packet = await layer.process(packet)
            except Exception as e:
                self.logger.error(f"Unhandled broker error: {e}", exc_info=True)
            finally:
                self.queue.task_done()

    def _create_layers(self) -> list[BaseLayer]:
        from omnikernal.packet.layers import ExecutionLayer, MappingLayer, Parser
        from omnikernal.packet.layers.response import ResponseLayer
        from omnikernal.packet.layers.sanitizer import CommandSanitizer

        return [
            MappingLayer(self.routing_cache),  # Layer 1+2: route + permissions
            CommandSanitizer(),  # Layer 4: sanitize
            Parser(),  # Layer 5: parse CLI args
            ExecutionLayer(),  # Layer 6: execute handler
            ResponseLayer(),  # Layer 7: reply to user
        ]

    async def stop(self, wait_for_all_tasks: bool = False) -> None:
        """Stopping the queue by processing all its tasks cleanly."""
        if wait_for_all_tasks:
            await self.queue.join()
        else:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                except asyncio.QueueEmpty:
                    break
