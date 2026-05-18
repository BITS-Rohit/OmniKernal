"""
Adapters Package — Platform Integration Layer

Provides the AdapterManager for lifecycle control and the MockAdapter for testing.
"""

from .manager import AdapterManager
from .mock_adapter import MockAdapter

__all__ = ["AdapterManager", "MockAdapter"]
