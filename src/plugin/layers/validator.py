"""
PluginValidator — Pure Business Logic

Stateless validation layer. No I/O, no DB calls, no state mutation.
Receives already-parsed data (dicts, PluginManifest) and returns bool/object.

Responsibilities:
    - Structural schema checks (manifest name vs folder, required fields)
    - Semver version gate (min_core_version)
    - Command field validation (pattern, handler, role type)
    - Handler file existence check (only disk stat — no read)
"""

from __future__ import annotations

import os
import re
from typing import Any

from src.omni_logger import omni_logger
from src.packet.contracts.command_manifest import CommandManifest
from src.packet.contracts.user import ROLE
from src.plugin.contracts.plugin_manifest import PluginManifest

# Single source of truth — imported by PluginEngine facade too
OMNIKERNAL_VERSION: str = "0.1.0"


def _version_tuple(v: str) -> tuple[int, ...]:
    """Parse a semver-like string to a comparable int tuple. '1.2.0-alpha' → (1, 2, 0)."""
    try:
        parts: list[int] = []
        for segment in v.split("."):
            m = re.search(r"\d+", segment)
            parts.append(int(m.group()) if m else 0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])
    except (ValueError, AttributeError):
        return (0, 0, 0)


class PluginValidator:
    """
    Stateless validator. All methods are static — no instance state.
    Receives parsed data, returns True/False or a contract object.
    Never touches the DB. Never does disk I/O beyond os.path.exists checks.
    """

    @staticmethod
    def validate_content(
        raw: dict[str, Any] | None,
        commands: dict[str, Any] | None,
    ) -> bool:
        """Guard: both dicts must be non-empty after parsing."""
        if not raw:
            omni_logger.debug("Manifest file is empty or contains invalid data")
            return False
        if not commands:
            omni_logger.debug("Commands file is empty or contains invalid data")
            return False
        return True

    @staticmethod
    def validate_plugin_schema(manifest: PluginManifest, plugin_folder: str) -> bool:
        """
        Structural checks on a parsed PluginManifest:
          1. manifest.name must match folder name (naming contract)
          2. min_core_version must be <= running core version
        """
        if manifest.name != plugin_folder:
            omni_logger.debug(
                f"Plugin load failed for '{plugin_folder}': "
                f"manifest 'name' ('{manifest.name}') does not match folder name."
            )
            return False

        if manifest.min_core_version:
            required = _version_tuple(manifest.min_core_version)
            running = _version_tuple(OMNIKERNAL_VERSION)
            if required > running:
                omni_logger.warning(
                    f"Plugin '{manifest.name}' requires core v{manifest.min_core_version} "
                    f"but running v{OMNIKERNAL_VERSION}. Skipping."
                )
                return False

        return True

    @staticmethod
    def validate_command(
        key: str,
        value: dict[str, Any],
        plugin_name: str,
        plugins_dir: str,
    ) -> CommandManifest | None:
        """
        Validates a single command entry from commands.yaml.
        Returns a CommandManifest on success, None on any validation failure.

        NOTE: DB conflict check (get_tool_by_command) is intentionally NOT here.
        That is an insertion-time concern and belongs in PluginInsertion.
        """
        if not isinstance(value, dict):
            omni_logger.debug(f"Skipping command '{key}' in plugin '{plugin_name}': expected dict.")
            return None

        pattern: Any = value.get("pattern")
        handler: Any = value.get("handler")
        description: str = value.get("description", "No description provided")
        role_raw: str = value.get("Minimum_Role", "USER")

        if not isinstance(pattern, str) or not isinstance(handler, str):
            omni_logger.debug(
                f"Skipping '{key}' in '{plugin_name}': missing or invalid 'pattern'/'handler'."
            )
            return None

        if not isinstance(role_raw, str):
            omni_logger.debug(
                f"Skipping '{key}' in '{plugin_name}': 'Minimum_Role' must be a string."
            )
            return None

        try:
            minimum_role: ROLE = ROLE(role_raw.upper())
        except ValueError:
            omni_logger.debug(
                f"Skipping '{key}' in '{plugin_name}': unknown role '{role_raw}'. Defaulting to USER."
            )
            minimum_role = ROLE.USER

        # Handler file existence — disk stat only, no import
        try:
            module_path, _ = handler.rsplit(".", 1)
            handler_file = os.path.join(plugins_dir, plugin_name, *module_path.split(".")) + ".py"
            if not os.path.exists(handler_file):
                omni_logger.error(
                    f"Handler file missing for '{key}' in '{plugin_name}': {handler_file}"
                )
                return None
        except ValueError:
            omni_logger.error(
                f"Invalid handler format for '{key}': '{handler}'. Expected 'module.func'."
            )
            return None

        return CommandManifest(
            name=key,
            description=description,
            pattern=pattern,
            handler=handler,
            Minimum_Role=minimum_role,
            plugin_name=plugin_name,
        )
