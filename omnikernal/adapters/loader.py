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

from typing import Any, Callable, Type

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

    _registry: dict[str, Type[PlatformAdapter]] = {}

    def __init__(self) -> None:
        self.logger = core_logger.bind(subsystem="adapter_loader")


    # Todo , Class level logger for static event like register decorator.
    @classmethod
    def register_adapter(cls, name: str) -> Callable[[Type[PlatformAdapter]], Type[PlatformAdapter]]:
        """
        Registers an adapter class under the given name.
        Works as Decorator.

        Example :
            @register("console") <-- give name here to what to register it with.
            class ExampleAdapter(PlatformAdapter):
                ...
        Args:
            name: Logical name for the adapter (e.g. "console", "WhatsApp").

        Raises:
            TypeError: If cls is not a subclass of PlatformAdapter.
        """

        def wrapper(adapter_cls: Type[PlatformAdapter]):
            """
            decorator for adapter class.
            :param adapter_cls:
            :return:
            """
            if not issubclass(adapter_cls, PlatformAdapter):
                raise TypeError(f"Cannot register '{name}': {adapter_cls!r} is not a PlatformAdapter subclass.")

            if name not in cls._registry:
                cls._registry[name] = adapter_cls
            return adapter_cls

        return wrapper

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
        instance: PlatformAdapter = cls(**kwargs)  # type [ignore]
        self.logger.info(f"Adapter loaded: {instance.platform_name}")
        return instance

    def list_adapters(self) -> list[str]:
        """Returns the names of all registered adapters."""
        return list(self._registry.keys())
