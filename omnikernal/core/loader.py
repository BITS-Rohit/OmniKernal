"""
PluginEngine — Declarative Plugin Discovery & Loading

Scans the plugins/ directory, validates manifest.json and commands.yaml,
and registers findings into the OmniRepository.

Now uses PluginManifest.from_dict() to parse and validate
manifests formally, instead of raw dict access.

Now enforces min_core_version — plugins that require a higher
core version than the currently running OMNIKERNAL_VERSION are rejected
at load time with a clear log message.

Warns when a command_name from one plugin would overwrite a
command_name already registered by a different plugin, so admins know which
plugin "won" the collision.

PluginEngine now accepts the running platform_name and skips
(or marks inactive) plugins that don't support the current platform. This
prevents polluting the DB with tools that can never execute.
"""

import json
import os
from typing import TYPE_CHECKING

import yaml

from omnikernal.core.contracts.plugin_manifest import PluginManifest
from omnikernal.core.logger import core_logger

if TYPE_CHECKING:
    from omnikernal.database.repository import OmniRepository

# single source of truth for the current Core version
OMNIKERNAL_VERSION: str = "0.1.0"


def _version_tuple(v: str) -> tuple[int, ...]:
    """
    Parse a semver-like string into a comparable tuple.
    Pads with zeros to ensure '1.2' is (1, 2, 0) for stable comparison.
    """
    try:
        # Split by '.' and then only take the digit parts of each segment
        # (e.g. '1.0.0-alpha' -> '1', '0', '0')
        import re

        parts = []
        for segment in v.split("."):
            match = re.search(r"\d+", segment)
            if match:
                parts.append(int(match.group()))
            else:
                parts.append(0)

        # Pad to 3 parts (major, minor, patch)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])
    except (ValueError, AttributeError):
        return 0, 0, 0


class PluginEngine:
    """
    Main orchestrator for plugin lifecycle.
    Handles plugins loading & validation

    Args:
        repo:          The OmniRepository to register plugins/tools into.
        plugins_dir:   Directory to scan for plugin folders.
        platform_name: running platform identifier (e.g. 'whatsapp').
                       Plugins that don't list this platform (or 'any') are skipped.
                       Pass None to disable platform filtering (all plugins load).
    """

    def __init__(
        self,
        repo: "OmniRepository",
        plugins_dir: str,
        platform_name: str | None = None,
    ):
        self.repo = repo
        self.plugins_dir = plugins_dir
        self.platform_name = platform_name
        self.logger = core_logger.bind(subsystem="plugin_engine")

    async def discover_and_load(self) -> None:
        """
        Scans the plugins directory and registers valid plugins in the DB.
        """
        self.logger.info(f"Scanning for plugins in: {self.plugins_dir}")

        if not os.path.exists(self.plugins_dir):
            self.logger.warning(f"Plugins directory not found: {self.plugins_dir}")
            return

        found_names: list[str] = []
        failed_plugins: list[str] = []

        for plugin_folder in os.listdir(self.plugins_dir):  # Loop through all plugins.
            plugin_path = os.path.join(self.plugins_dir, plugin_folder)

            if not os.path.isdir(plugin_path):
                continue
            self.logger.info(f"Loading plugins from directory: '{plugin_folder}' ")
            name, status = await self._load_plugin(plugin_folder, plugin_path)
            if status:
                found_names.append(name)
            else:
                if name is not None:
                    failed_plugins.append(name)

        # cleanup any plugins in DB that are NO LONGER on disk.
        if found_names:
            await self.repo.deactivate_missing_plugins(found_names)

    async def _load_plugin(self, plugin_folder: str, path: str) -> tuple[str | None, bool]:
        """
        Loads a single plugin folder.

        Returns :
            bool : True : on sucess else False
        """
        manifest_path = os.path.join(path, "manifest.json")
        commands_path = os.path.join(path, "commands.yaml")

        if not os.path.exists(manifest_path):
            self.logger.debug(f"Skipping {plugin_folder}: No manifest.json found.")
            return None, False

        manifest: PluginManifest | None = None

        try:
            # Load & Validate Manifest using formal contract
            with open(manifest_path, encoding="utf-8") as f:
                raw = json.load(f)

            manifest = PluginManifest.from_dict(raw)  # gives validated cls obj

            # folder name must match manifest.name, prevents import failures if a user renames a plugin folder on disk.
            if manifest.name != plugin_folder:
                self.logger.error(
                    f"Plugin load failed for '{plugin_folder}': manifest 'name' ('{manifest.name}') "
                    f"does not match folder name. Please rename the folder or fix the manifest."
                )
                return None, False

            # enforce min_core_version before registration
            if manifest.min_core_version:
                required = _version_tuple(manifest.min_core_version)
                running = _version_tuple(OMNIKERNAL_VERSION)
                if required > running:
                    self.logger.warning(
                        f"Plugin '{manifest.name}' requires core v{manifest.min_core_version} "
                        f"but running v{OMNIKERNAL_VERSION}. Skipping. --Suggestion : upgrade plugin version or OmniKernal"
                    )
                    return None, False

            # skip plugins incompatible with the active platform
            if self.platform_name and not manifest.supports_platform(
                self.platform_name
            ):
                self.logger.info(
                    f"Plugin '{manifest.name}' does not support platform "
                    f"'{self.platform_name}' (supports {manifest.platform}). Skipping."
                )
                return None, False

            # Register Plugin in DB
            await self.repo.register_plugin(
                name=manifest.name,
                version=manifest.version,
                author_name=manifest.author,
                description=manifest.description,
            )

            # Load & Process commands.yaml
            if os.path.exists(commands_path):
                with open(commands_path, encoding="utf-8") as f:
                    cmd_cfg = yaml.safe_load(f)

                # check empty, malformed YAML files or 'commands' key not a dictionary
                if not isinstance(cmd_cfg, dict):
                    self.logger.warning(
                        f"Skipping Registering of Plugin for '{manifest.name}': commands.yaml is empty or malformed."
                    )
                else:
                    commands_raw = cmd_cfg.get("commands", {})
                    if not isinstance(commands_raw, dict):
                        self.logger.warning(
                            f"Skipping Registering of Plugin for '{manifest.name}': 'commands' key in commands.yaml is not a dictionary."
                        )
                        return manifest.name, False
                    else:
                        commands = commands_raw

                for cmd_name, cmd_info in commands.items():
                    # validate schema before registration
                    if not isinstance(cmd_info, dict):
                        self.logger.error(
                            f"Skipping command '{cmd_name}' in plugin '{manifest.name}': "
                            "Expected a dictionary."
                        )
                        continue

                    pattern = cmd_info.get("pattern")
                    handler = cmd_info.get("handler")

                    if not isinstance(pattern, str) or not isinstance(handler, str):
                        self.logger.error(
                            f"Skipping command '{cmd_name}' in plugin '{manifest.name}': "
                            f"missing or invalid 'pattern' or 'handler'."
                        )
                        continue

                    # ----------------------------------------------------------------
                    # warn if an existing tool with this name belongs
                    # to a different plugin (silent overwrite is a footgun).
                    existing = await self.repo.get_tool_by_command(cmd_name)
                    if existing and existing.plugin_name != manifest.name:
                        self.logger.warning(
                            f"Command name conflict: '{cmd_name}' is already registered "
                            f"by plugin '{existing.plugin_name}'. "
                            f"Plugin '{manifest.name}' will overwrite it."
                        )

                    await self.repo.register_tool(
                        command_name=cmd_name.lower(),  # normalize to lowercase
                        pattern=pattern,
                        handler_path=handler,
                        plugin_name=manifest.name,
                        description=cmd_info.get("description"),
                        required_role=cmd_info.get("role", "user"),
                    )
                    # ----------------------------------------------------------------

            self.logger.info(
                f"Loaded plugin: {manifest}"  # uses PluginManifest.__repr__
            )
            return manifest.name, True

        except Exception as e:
            self.logger.error(f"Failed to load plugin '{plugin_folder}': {e}")
            # mark plugin inactive in DB if partially registered
            if manifest is not None:
                try:
                    await self.repo.set_plugin_inactive(manifest.name)
                    self.logger.warning(
                        f"Plugin '{manifest.name}' marked inactive due to load failure."
                    )
                except Exception as inner:
                    self.logger.error(
                        f"Could not mark plugin '{manifest.name}' inactive: {inner}"
                    )
        if manifest is None:
            return None, False
        return manifest.name, False
