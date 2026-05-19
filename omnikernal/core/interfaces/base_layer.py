"""
Base Layer for every Layer from Received Message State --- Done Message State.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnikernal.core.contracts import IntentPacket


class BaseLayer:
    async def process(self, packet: "IntentPacket") -> "IntentPacket":
        """Process a packet and return it.

        All layers must be async. Sync layers simply return packet without
        any await. This ensures the broker can uniformly await every layer
        without per-packet inspect overhead.

        Args:
            packet: The IntentPacket to process.

        Returns:
            The processed IntentPacket.
        """
        raise NotImplementedError("Subclasses must implement this method")
