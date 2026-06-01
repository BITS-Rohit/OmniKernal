"""
Plugin Processing is phase 1 of Omnikernal...

Loading Plugin -> Validating -> Insertion in DB...
"""

from .adapters import AdapterManager, MockAdapter
from .contracts import PluginManifest
from .layers import PluginEngine

__all__ = [
    "AdapterManager",
    "MockAdapter",
    "PluginEngine",
    "PluginManifest",
]
