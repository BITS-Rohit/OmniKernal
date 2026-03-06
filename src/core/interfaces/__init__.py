"""
src/core/interfaces — Abstract Base Classes (Hook Contracts)

These ABCs define the contracts every implementation must satisfy.
The Core only calls these — it never imports SDK or plugin code directly.
"""

from .base_command import BaseCommand
from .base_plugin import BasePlugin
from .platform_adapter import PlatformAdapter

__all__ = ["PlatformAdapter", "BasePlugin", "BaseCommand"]
