"""
src/core/contracts — Typed Data Contracts

Frozen dataclasses and structured objects passed between Core, adapters,
and plugins. These are immutable data shapes — no logic lives here.
"""

from .command_manifest import CommandManifest
from .command_result import CommandResult
from .intent_packet import IntentPacket
from .message import Message
from .packet_state import PacketState
from .plugin_manifest import PluginManifest
from .route_cache import RouteCache
from .user import ROLE, User

__all__ = [
    # User based
    "User",
    "ROLE",
    # Message based
    "Message",
    # Plugin Based
    "PluginManifest",
    "CommandManifest",
    "RouteCache",
    # Packet & Result based
    "CommandResult",
    "IntentPacket",
    "PacketState",
]
