"""
PluginManifest — Frozen Dataclass Contract

Represents the parsed contents of a plugin's manifest.json file.
Built by the PluginLoader when scanning the plugins/ directory.
Used by the Core to register plugins in the DB and to validate
compatibility before loading.

Invariant: The Core reads manifest.json — it never imports plugin Python
files just to discover metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """
    Parsed plugin identity from manifest.json.

    Attributes:
        name:             Unique plugin identifier. Must match folder name.
        version:          Semantic version string (e.g. '1.0.0').
        author:           Plugin author name or handle.
        description:      Human-readable description.
        platform:         List of supported platforms (e.g. ['WhatsApp', 'any']).
        min_core_version: Minimum OmniKernal version required (e.g. '0.1.0').
                          Optional — older manifests may omit this field.
    """

    name: str
    version: str
    author: str
    description: str
    min_core_version: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginManifest:
        """
        Constructs a PluginManifest from a parsed manifest.json dictionary.
        Supports both 'platform' and the legacy 'supported_platforms' key.

        Args:
            data: Raw dict from json.load(manifest.json).

        Returns:
            A validated, immutable PluginManifest instance.

        Raises:
            ValueError: If required fields (name, version) are missing.
        """
        name = data.get("name")
        version = data.get("version")
        min_core_version = data.get("min_core_version")

        if not name:
            raise ValueError("Plugin's  manifest.json file is missing required field: 'name'")

        if not version:
            raise ValueError("Plugin's  manifest.json file is missing required field: 'version'")

        if not min_core_version:
            raise ValueError(
                "Plugin's  manifest.json file is missing required field: 'min_core_version'"
            )

        author = data.get("author", "unknown")
        description = data.get("description", "No description provided")

        return cls(
            name=name,
            version=version,
            author=author,
            description=description,
            min_core_version=min_core_version,
        )

    def __str__(self) -> str:
        return f"PluginManifest(name={self.name}, \
            version={self.version}, \
                author={self.author})"  # noqa: E501

    def __repr__(self) -> str:
        return (
            f"PluginManifest(name={self.name!r}, version={self.version!r}, author={self.author!r})"
        )
