"""
PluginInsertion — DB Persistence Layer

Single responsibility: flush validated plugin/command data into OmniRepository.
Owns ALL repo.* calls. No file I/O. No validation logic.

Responsibilities:
    - Bulk upsert plugins
    - Bulk upsert commands (with conflict logging — only place repo is queried)
    - Bulk delete stale/failed plugins
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.omni_logger import omni_logger
from src.packet.contracts.command_manifest import CommandManifest
from src.plugin.contracts.plugin_manifest import PluginManifest

if TYPE_CHECKING:
    from src.database.repository import OmniRepository


class PluginInsertion:
    """
    Stateless DB persistence layer.
    All methods receive the repo as a parameter — no instance state.
    """

    @staticmethod
    async def persist(
        repo: OmniRepository,
        valid_plugins: list[PluginManifest],
        valid_commands: list[CommandManifest],
        failed_plugins: list[str],
    ) -> None:
        """
        Flush a full discovery cycle into the DB atomically:
          1. Upsert valid plugins
          2. Check command conflicts (only DB read in the whole layer)
          3. Upsert valid commands
          4. Remove explicitly failed plugins
          5. Remove stale plugins no longer on disk
        """
        logger = omni_logger.bind(subsystem="plugin_insertion")

        # 1. Upsert plugins
        await repo.register_plugins(valid_plugins)
        logger.debug(f"Upserted {len(valid_plugins)} plugins.")

        # 2. Conflict check + upsert commands
        for cmd in valid_commands:
            existing = await repo.get_tool_by_command(cmd.name)
            if existing and existing.plugin_name != cmd.plugin_name:
                logger.warning(
                    f"Command conflict: '{cmd.name}' already registered by "
                    f"'{existing.plugin_name}'. '{cmd.plugin_name}' will overwrite it."
                )

        await repo.register_tools(valid_commands)
        logger.debug(f"Upserted {len(valid_commands)} commands.")

        # 3. Remove explicitly failed plugins
        if failed_plugins:
            await repo.remove_plugins(failed_plugins)
            logger.debug(f"Removed {len(failed_plugins)} failed plugins.")

        # 4. Remove stale plugins (were in DB but no longer on disk)
        safe_names = [p.name for p in valid_plugins]
        await repo.remove_missing_plugins(safe_names)
        logger.debug("Stale plugin cleanup done.")
