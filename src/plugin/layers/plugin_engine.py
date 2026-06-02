"""
PluginEngine — Facade Orchestrator

Thin coordinator for the plugin lifecycle pipeline:
    Loader  →  Validator  →  Insertion

This class owns NO business logic. It only calls the three layers in sequence
and passes data between them. If you find yourself adding if/else logic here,
it belongs in one of the three inner layers instead.

Pipeline:
    1. PluginLoader.get_plugin_folders()    — scan disk
    2. PluginLoader.read_manifest()         — parse manifest.json
    3. PluginLoader.read_commands()         — parse commands.yaml
    4. PluginValidator.validate_content()   — guard empty dicts
    5. PluginValidator.validate_plugin_schema() — name + version gate
    6. PluginValidator.validate_command()   — per-command field check
    7. PluginInsertion.persist()            — flush to DB
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.omni_logger import omni_logger
from src.packet.contracts.command_manifest import CommandManifest
from src.plugin.contracts.plugin_manifest import PluginManifest

from .insertion import PluginInsertion
from .loader import PluginLoader
from .validator import PluginValidator

if TYPE_CHECKING:
    from src.database.repository import OmniRepository


class PluginEngine:
    """
    Facade for the plugin lifecycle.
    Instantiate once per startup with a repo and a plugins directory.

    Usage::

        engine = PluginEngine(repo=repo, plugins_dir="/path/to/plugins")
        await engine.discover_and_load()
    """

    def __init__(self, repo: OmniRepository, plugins_dir: str) -> None:
        if repo is None:
            raise ValueError("OmniRepository is required for PluginEngine")
        if not plugins_dir:
            raise ValueError("plugins_dir is required for PluginEngine")

        self.repo = repo
        self._loader = PluginLoader(plugins_dir)
        self._logger = omni_logger.bind(subsystem="plugin_engine")

    async def discover_and_load(self) -> None:
        """
        Full lifecycle run:
            scan → parse → validate → collect → persist
        """
        folders = self._loader.get_plugin_folders()

        self._logger.info(f"Scanning for New plugins in: {self._loader.plugins_dir}")
        self._logger.info(f"Found plugins: {len(folders)}")
        self._logger.debug(f"Plugin folders found: {folders}")

        valid_plugins: list[PluginManifest] = []
        valid_commands: list[CommandManifest] = []
        failed_plugins: list[str] = []

        for folder in folders:
            if folder.startswith("__") or folder.startswith("."):
                continue
            result = self._process_plugin(folder)
            if result is None:
                failed_plugins.append(folder)
            else:
                plugin_manifest, commands = result
                valid_plugins.append(plugin_manifest)
                valid_commands.extend(commands)

        self._logger.debug("-----------------------------------------------")
        self._logger.info(f"Valid Plugins to add to DB: {len(valid_plugins)}")
        self._logger.debug(f"Valid Plugins to add to DB : {valid_plugins}")
        self._logger.info(f"Valid Commands to add to DB: {len(valid_commands)}")
        self._logger.debug(
            f"Valid Commands to add to DB : {(print('--> ', x) for x in valid_commands)}"
        )
        if failed_plugins:
            self._logger.warning(f"Failed to load plugins: {len(failed_plugins)}")
            self._logger.debug("-----------------------------------------------")
            self._logger.debug(f"Failed to load plugins: {failed_plugins}")

        # Database Insertion.
        await PluginInsertion.persist(
            repo=self.repo,
            valid_plugins=valid_plugins,
            valid_commands=valid_commands,
            failed_plugins=failed_plugins,
        )

    def _process_plugin(self, folder: str) -> tuple[PluginManifest, list[CommandManifest]] | None:
        """
        Process a single plugin folder through parse → validate.
        Returns (PluginManifest, commands) on success, None on any failure.
        """
        raw = self._loader.read_manifest(folder)
        commands_raw = self._loader.read_commands(folder)

        if not PluginValidator.validate_content(raw, commands_raw):
            return None

        assert raw is not None
        assert commands_raw is not None

        manifest = PluginManifest.from_dict(raw)
        if manifest is None:
            self._logger.debug(f"Failed to parse manifest for '{folder}': invalid schema")
            return None

        if not PluginValidator.validate_plugin_schema(manifest, folder):
            return None

        valid_commands: list[CommandManifest] = []
        invalid_count = 0

        for cmd_name, cmd_info in commands_raw.items():
            if not isinstance(cmd_info, dict):
                self._logger.debug(
                    f"Invalid command format for '{cmd_name}' in '{folder}': "
                    f"expected dict, got {type(cmd_info).__name__}"
                )
                invalid_count += 1
                continue

            cmd = PluginValidator.validate_command(
                key=cmd_name,
                value=cmd_info,
                plugin_name=manifest.name,
                plugins_dir=self._loader.plugins_dir,
            )
            if cmd:
                valid_commands.append(cmd)
            else:
                invalid_count += 1

        self._logger.debug(
            f"Loaded plugin '{manifest.name}' with "
            f"{len(commands_raw) - invalid_count} valid commands"
        )
        return manifest, valid_commands
