"""
It is Layer 6, execute the mapped func and update the result field in the packet.
"""

import asyncio
import importlib
import inspect

from src.packet.contracts import IntentPacket, PacketState
from src.packet.contracts.command_result import CommandResult
from src.packet.interfaces import BaseLayer


class ExecutionLayer(BaseLayer):
    """
    Executes the mapped handler and updates the result field in the packet.
    steps:
        1. resolve mapped func.
        2. run that func into its own async mode.
        3. catch execptions.
        4. route to history or watchdog if any execption.
        5. update the result field in the packet.
        6. update state based on result.
    """

    async def process(self, packet: IntentPacket) -> IntentPacket:
        packet.state = PacketState.EXECUTION

        if not packet.mapped_handler:
            packet.fail("No execution handler mapped.")
            return packet

        try:
            # 1. Resolve and import the handler function dynamically
            parts = packet.mapped_handler.split(".")
            module_path = ".".join(parts[:-1])
            func_name = parts[-1]

            module = importlib.import_module(module_path)
            func = getattr(module, func_name)

            # 2. Inspect if handler is async or sync
            is_async = inspect.iscoroutinefunction(func)
            if not is_async and callable(func):
                is_async = inspect.iscoroutinefunction(func.__call__)

            # 3. Execute safely without blocking event loop
            if is_async:
                res = await func(packet)
            else:
                res = await asyncio.to_thread(func, packet)

            # 4. Hybrid parsing of handler output
            if packet.result is None:
                if isinstance(res, CommandResult):
                    packet.result = res
                    packet.state = PacketState.DONE if res.ok else PacketState.FAILED
                elif isinstance(res, str):
                    packet.resolve(res)
                elif res is None:
                    packet.resolve(None)

        except Exception as e:
            packet.logger.error(f"Execution failed: {e}", exc_info=True)
            packet.fail(f"Execution crashed: {str(e)}")
            packet.state = PacketState.FAILED

        return packet
