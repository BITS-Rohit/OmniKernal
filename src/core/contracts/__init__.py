"""
src/core/contracts — Typed Data Contracts

Frozen dataclasses and structured objects passed between Core, adapters,
and plugins. These are immutable data shapes — no logic lives here.
"""

from .command_context import CommandContext
from .command_result import CommandResult
from .message import Message
from .plugin_manifest import PluginManifest
from .user import User

__all__ = [
    "User",
    "Message",
    "PluginManifest",
    "CommandResult",
    "CommandContext",
]
