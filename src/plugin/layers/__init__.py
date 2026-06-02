"""
plugin/layers/__init__.py — Public API

Exposes PluginEngine as the single public entry point for the plugin layer.
PluginEngine is a Facade: it orchestrates Loader → Validator → Insertion
but contains zero logic itself.

Internal layers (PluginLoader, PluginValidator, PluginInsertion) are
intentionally NOT exported — callers should never instantiate them directly.
"""

from src.plugin.layers.plugin_engine import PluginEngine

__all__ = ["PluginEngine"]
