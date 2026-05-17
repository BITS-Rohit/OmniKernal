# src/core — OmniKernal Core Engine package


import asyncio
from logging import Logger, LoggerAdapter

from omnikernal.core.contracts import IntentPacket, Message, PacketState
from omnikernal.core.interfaces import BaseLayer
from omnikernal.omni_logger import omni_looger


class GlobalBroker:
    # Todo , implement a singleton pattern
    # Todo, add cache for queue dropped without processing , from task_done() and put() rejection.

    __slots__ = ('queue' , 'dispatcher', 'logger', 'routing_cache')

    def __init__(self, routing_cache: dict, max_queue_size: int = 10000, logger: Logger | LoggerAdapter | None = None):
        self.routing_cache = routing_cache
        self.queue: asyncio.Queue[IntentPacket] = asyncio.Queue(maxsize=max_queue_size)
        self.dispatcher: list[BaseLayer] = self._create_layers()
        self.logger = logger or omni_looger

    async def push(self, message: Message, logger: Logger | LoggerAdapter | None = None) -> None:
        if logger is None:
            logger = self.logger
        packet = IntentPacket(message=message, logger=logger)
        await self.queue.put(packet)

    async def start(self):
        return asyncio.create_task(self._consumer())

    async def _consumer(self) -> None:
        while True:
            packet = await self.queue.get()

            for _layer in self.dispatcher:
                # packet = await _layer.process(packet)
                if packet.state in (PacketState.DROPPED, PacketState.DONE):
                    break
            self.queue.task_done()

    def _create_layers(self) -> list[BaseLayer]:
        from omnikernal.core.layers.mapping import MappingLayer

        return [
            MappingLayer(self.routing_cache)
        ]

    async def stop(self, wait_for_all_taks : bool = False)-> None:
        """Stopping the queue by processing its all task"""
        if wait_for_all_taks:
            await self.queue.join()
        else:
            while True :
                await self.queue.get()
                self.queue.task_done()

