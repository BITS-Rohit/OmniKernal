"""
PluginManifest — Frozen Pydantic Contract

Represents the parsed contents of a plugin's manifest.json file.
Built by the PluginLoader when scanning the plugins/ directory.
Used by the Core to register plugins in the DB and to validate
compatibility before loading.

Invariant: The Core reads manifest.json — it never imports plugin Python
files just to discover metadata.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from src.omni_logger import omni_logger


class PluginManifest(BaseModel):
    """
    Parsed plugin identity from manifest.json.

    Attributes:
        name:             Unique plugin identifier. Must match folder name.
        version:          Semantic version string (e.g. '1.0.0').
        min_core_version: Minimum OmniKernal version required (e.g. '0.1.0').
        author:           Plugin author name or handle. Defaults to "unknown".
        description:      Human-readable description. Defaults to "No description provided".
    """

    model_config = ConfigDict(frozen=True)

    name: str
    version: str
    min_core_version: str
    author: str = "unknown"
    description: str = "No description provided"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginManifest | None:
        """
        Safely constructs a PluginManifest from a parsed manifest.json dictionary.

        Traps ValidationErrors if required fields (name, version, min_core_version)
        are missing or malformed, protecting the PluginEngine from crashing.
        """
        try:
            return cls.model_validate(data)
        except ValidationError as e:
            omni_logger.debug(f"Failed to parse plugin manifest. Schema mismatch: {e}")
            return None

    def to_dict(self) -> dict[str, Any]:
        """
        Unpacks the PluginManifest model back into a standard dictionary.
        """
        return self.model_dump()

    def __str__(self) -> str:
        return f"PluginManifest(name={self.name}, version={self.version}, author={self.author})"

    def __repr__(self) -> str:
        return (
            f"PluginManifest(name={self.name!r}, version={self.version!r}, author={self.author!r})"
        )
