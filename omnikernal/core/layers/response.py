"""
Layer 7: Response Delivery
Sends execution result back to user using the appropriate platform adapter.
Ignores dropped packets or packets without a reply payload.
"""

from omnikernal.core.contracts import IntentPacket, PacketState
from omnikernal.core.interfaces import BaseLayer


class ResponseLayer(BaseLayer):
    """
    Delivers command result replies to the originating platform.
    Requires a dictionary of active PlatformAdapters injected at startup.
    """

    async def process(self, packet: IntentPacket) -> IntentPacket:
        """Send reply based on command result.

        Args:
            packet: IntentPacket containing the result to send.

        Returns:
            The same packet instance.
        """

        # Only respond if there is a successful or failed result with reply text
        if packet.result and packet.result.reply:
            adapter = packet.message.adapter
            if adapter:
                try:
                    await adapter.send_message(packet)
                    packet.logger.info(f"Reply sent to {packet.user.id} via {packet.platform}")
                except Exception as e:
                    packet.logger.error(f"Failed to send reply: {e}", exc_info=True)
            else:
                packet.logger.error(
                    f"No adapter found for platform: {packet.platform} , Packet Content : {packet!r} "
                )
        packet.state = PacketState.DONE

        return packet
