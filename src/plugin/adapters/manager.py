"""
AdapterManager — Adapter Registry & Pipeline Producer

Users explicitly register adapter instances under a string platform key.
That key MUST match Message.platform for the response layer to route correctly.

Usage:
    manager = AdapterManager()
    manager.register("whatsapp", WhatsAppAdapter())
    manager.register("telegram", TelegramAdapter())

    # Recommended: define your own StrEnum to avoid typos
    class Platform(StrEnum):
        WHATSAPP = "whatsapp"
        TELEGRAM = "telegram"

    manager.register(Platform.WHATSAPP, WhatsAppAdapter())

Producer-Consumer:
    - AdapterManager polls adapters via fetch_new_messages() → Producer
    - GlobalBroker.queue → Consumer
"""

import asyncio
import dataclasses
from typing import TYPE_CHECKING, Any

from omnikernal.plugin.interfaces import PlatformAdapter
from omnikernal.omni_logger import omni_logger

if TYPE_CHECKING:
    from omnikernal.packet import GlobalBroker


class AdapterManager:
    """
    Central registry for active platform adapters.

    Key = platform name string (must match Message.platform exactly).
    Value = list of PlatformAdapter instances for that platform.

    Multiple adapters per platform are supported (e.g. multi-account).
    On connect failure the adapter is removed and a clear fix hint is logged.
    """

    def __init__(self) -> None:
        self.logger = omni_logger.bind(subsystem="adapter_manager")
        # platform_name -> [adapter instances]
        self._registry: dict[str, list[PlatformAdapter]] = {}
        self._polling_tasks: list[asyncio.Task[Any]] = []
        # Tracks adapters that failed connect() for diagnostics
        self._failed: list[tuple[str, str]] = []  # (platform_name, adapter class name)

    # ------------------------------------------------------------------
    # Registration API
    # ------------------------------------------------------------------

    def register(
        self,
        platform_name: str,
        adapter: PlatformAdapter | list[PlatformAdapter],
    ) -> list[Any]:
        """
        Register one or multiple adapter instances under an explicit platform key.

        IMPORTANT: platform_name must exactly match Message.platform — this is
        the routing key for ResponseLayer.

        Args:
            platform_name: Explicit string key (e.g. "whatsapp").
            adapter:       A single or list of PlatformAdapter instances.

        Returns:
            List of items that failed validation (not PlatformAdapter instances).
            Empty list means all registered successfully.
        """
        candidates: list[PlatformAdapter] = adapter if isinstance(adapter, list) else [adapter]

        failed: list[Any] = []

        if platform_name not in self._registry:
            self._registry[platform_name] = []

        for a in candidates:
            if not isinstance(a, PlatformAdapter):
                self.logger.warning(
                    f"[SKIPPED] '{a!r}' is not a PlatformAdapter instance — "
                    f"cannot register under '{platform_name}'."
                )
                failed.append(a)  # narrowed to non-PlatformAdapter by isinstance
                continue

            self._registry[platform_name].append(a)
            self.logger.info(
                f"Registered '{type(a).__name__}' under platform key '{platform_name}'"
            )

        return failed

    def get_primary(self, platform_name: str) -> PlatformAdapter | None:
        """Returns the first healthy adapter for a platform, skipping failed ones."""
        return next(
            (a for a in self._registry.get(platform_name, [])),
            None,
        )

    def list_platforms(self) -> list[str]:
        """Returns all registered platform keys."""
        return list(self._registry.keys())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start_all(self, broker: "GlobalBroker") -> None:
        """
        Connects all registered adapters and spawns producer polling tasks.
        Adapters that fail connect() are removed from the active registry
        and a descriptive fix hint is logged.
        """
        for platform_name, adapters in list(self._registry.items()):
            active: list[PlatformAdapter] = []

            for adapter in adapters:
                cls_name = type(adapter).__name__
                try:
                    connected = await adapter.connect()
                except Exception as exc:
                    connected = False
                    self.logger.error(
                        f"Adapter '{cls_name}' for platform '{platform_name}' "
                        f"raised during connect(): {exc}",
                        exc_info=True,
                    )

                if connected:
                    self.logger.info(f"Adapter '{cls_name}' connected — platform '{platform_name}'")
                    active.append(adapter)
                    task = asyncio.create_task(self._poll_adapter(platform_name, adapter, broker))
                    self._polling_tasks.append(task)
                else:
                    self._failed.append((platform_name, cls_name))
                    self.logger.warning(
                        f"[SKIPPED] Adapter '{cls_name}' failed to connect for platform "
                        f"'{platform_name}'. "
                        f"Fix the adapter and call manager.register('{platform_name}', ...) again."
                    )

            # Replace registry entry with only healthy adapters
            self._registry[platform_name] = active

    async def _poll_adapter(
        self,
        platform_name: str,
        adapter: PlatformAdapter,
        broker: "GlobalBroker",
    ) -> None:
        """Background producer loop for a single adapter instance."""
        self.logger.info(f"Polling started — platform='{platform_name}'")
        try:
            async for item in adapter.fetch_new_messages():
                # Adapters may yield (Message, flags_dict) or plain Message
                if isinstance(item, tuple):
                    message, flags = item
                else:
                    message, flags = item, None

                # Attach originating adapter if not already set
                if message.adapter is None:
                    message = dataclasses.replace(message, adapter=adapter)

                await broker.push(message, flags=flags)
        except asyncio.CancelledError:
            self.logger.info(f"Polling cancelled — platform='{platform_name}'")
        except Exception as exc:
            self.logger.error(f"Polling error — platform='{platform_name}': {exc}", exc_info=True)

    async def stop_all(self) -> None:
        """Cancel all polling tasks and disconnect all adapters cleanly."""
        for task in self._polling_tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(*self._polling_tasks, return_exceptions=True)
        self._polling_tasks.clear()

        for platform_name, adapters in self._registry.items():
            for adapter in adapters:
                try:
                    await adapter.disconnect()
                    self.logger.info(f"Adapter disconnected — platform='{platform_name}'")
                except Exception as exc:
                    self.logger.warning(f"Disconnect error — platform='{platform_name}': {exc}")

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def report_failures(self) -> None:
        """Logs a summary of all adapters that failed to connect."""
        if not self._failed:
            self.logger.info("All adapters connected successfully.")
            return

        self.logger.warning(f"{len(self._failed)} adapter(s) failed to connect:")
        for platform_name, cls_name in self._failed:
            self.logger.warning(
                f"  → platform='{platform_name}', adapter='{cls_name}' "
                f"| Fix: repair the adapter, then call "
                f"manager.register('{platform_name}', {cls_name}(...)) and restart."
            )
