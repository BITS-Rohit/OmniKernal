"""
1. check if cmd even exist in the cache.
2. Map the command to its handlers.
"""

from omnikernal.core.contracts import IntentPacket, PacketState, RouteCache
from omnikernal.core.interfaces import BaseLayer
from omnikernal.core.layers.permissions import PermissionValidator


class MappingLayer(BaseLayer):
    """
    1. Check if cmd even exist in the cache.
    2. Map the command to its handlers.
    """

    __slots__ = ("cache",)

    def __init__(self, cache: dict[str, RouteCache]):
        self.cache = cache

    async def process(self, packet: IntentPacket) -> IntentPacket:

        word = self._extract_word(packet.message.raw_text)
        route = self.cache.get(word)

        if route is None :
            packet.logger.debug("No command Found, dropping...")
            packet.state = PacketState.DROPPED
            return packet

        if not PermissionValidator.resolve_permission(
            required=route.required_role,actual=packet.user.role
            ):
            packet.logger.debug("Permission Denied, dropping...")
            packet.state = PacketState.DROPPED
            return packet

        packet.mapped_handler = route.handler_path
        packet.required_role = route.required_role
        packet.state = PacketState.MAPPED
        packet.logger.debug(f"Mapped command '{word}' -> {route.handler_path}")
        return packet

    def _extract_word(self, text: str) -> str:
        """Returns the first word (usually the command trigger) optimally."""
        text = text.lstrip(" !")
        space_idx = text.find(" ")
        return text[:space_idx] if space_idx != -1 else text
