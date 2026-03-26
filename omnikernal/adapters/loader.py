"""
AdapterLoader — Adapter Registry & Loader

Provides a simple registry for PlatformAdapter implementations.
Adapters are registered directly by class reference (no external
YAML descriptors or directory scanning needed).

Usage:
    loader = AdapterLoader()
    loader.register("console", ConsoleMockAdapter)
    adapter = loader.load("console")
"""


from typing import Any

from omnikernal.core.interfaces.platform_adapter import PlatformAdapter
from omnikernal.core.logger import core_logger


class AdapterLoader:
    """
    Registry-based adapter loader.

    Adapters are registered by a string name pointing to a PlatformAdapter subclass.
    Calling load() validates the class and returns a ready-to-use instance.

    Usage:
        loader = AdapterLoader()
        loader.register("console", ConsoleMockAdapter)
        adapter = loader.load("console")
    """

    def __init__(self) -> None:
        self._registry: dict[str, type[PlatformAdapter]] = {}
        self.logger = core_logger.bind(subsystem="adapter_loader")

    def register(self, name: str, cls: type[PlatformAdapter]) -> None:
        """
        Registers an adapter class under the given name.

        Args:
            name: Logical name for the adapter (e.g. "console", "whatsapp").
            cls:  A PlatformAdapter subclass to register.

        Raises:
            TypeError: If cls is not a subclass of PlatformAdapter.
        """
        if not (isinstance(cls, type) and issubclass(cls, PlatformAdapter)):
            raise TypeError(
                f"Cannot register '{name}': {cls!r} is not a PlatformAdapter subclass."
            )
        self._registry[name] = cls
        self.logger.debug(f"Adapter registered: '{name}' -> {cls.__name__}")

    def load(self, name: str, **kwargs: Any) -> PlatformAdapter:
        """
        Instantiates and returns a registered adapter by name.

        Args:
            name:    The registered adapter name.
            **kwargs: Passed to the adapter class constructor.

        Returns:
            A PlatformAdapter instance.

        Raises:
            KeyError: If no adapter is registered under the given name.
        """
        if name not in self._registry:
            available = list(self._registry.keys())
            raise KeyError(
                f"No adapter registered under '{name}'. Available: {available}"
            )

        cls = self._registry[name]
        self.logger.info(f"Loading adapter: '{name}' ({cls.__name__})")
        instance: PlatformAdapter = cls(**kwargs)
        self.logger.info(f"Adapter loaded: {instance.platform_name}")
        return instance

    def list_adapters(self) -> list[str]:
        """Returns the names of all registered adapters."""
        return list(self._registry.keys())
