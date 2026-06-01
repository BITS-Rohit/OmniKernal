import json
import os
from typing import Any, cast

import yaml

from src.omni_logger import omni_logger


class PluginLoader:
    """
    Pure I/O module for the PluginEngine.
    Responsible exclusively for disk operations and raw file parsing.
    Contains zero state and zero business logic.
    """

    def __init__(self, plugins_dir: str):
        self.plugins_dir = plugins_dir
        self.logger = omni_logger.bind(subsystem="plugin_loader")

    def get_plugin_folders(self) -> list[str]:
        """Returns a list of directory names inside the plugins directory."""
        if not os.path.exists(self.plugins_dir):
            self.logger.error(f"Plugins directory not found: {self.plugins_dir}")
            return []

        return [
            folder
            for folder in os.listdir(self.plugins_dir)
            if os.path.isdir(os.path.join(self.plugins_dir, folder))
        ]

    def read_manifest(self, plugin_folder: str) -> dict[str, Any] | None:
        """Reads manifest.json and returns a raw dictionary."""
        path = os.path.join(self.plugins_dir, plugin_folder, "manifest.json")
        return self._read_file(path, is_json=True)

    def read_commands(self, plugin_folder: str) -> dict[str, Any] | None:
        """Reads commands.yaml and returns a raw dictionary."""
        path = os.path.join(self.plugins_dir, plugin_folder, "commands.yaml")
        return self._read_file(path, is_json=False)

    def _read_file(self, file_path: str, is_json: bool) -> dict[str, Any] | None:
        """Handles actual disk I/O and traps parsing errors."""
        if not os.path.exists(file_path):
            self.logger.debug(f"File not found: {file_path}")
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                if is_json:
                    return cast(dict[str, Any], json.load(f))
                return cast(dict[str, Any], yaml.safe_load(f))
        except (
            UnicodeDecodeError,
            PermissionError,
            OSError,
            json.JSONDecodeError,
            yaml.YAMLError,
        ) as e:
            self.logger.debug(f"I/O or Parsing error for {file_path}: {e}")
            return None
        except Exception as e:
            self.logger.debug(f"Unknown error reading {file_path}: {e}")
            return None
