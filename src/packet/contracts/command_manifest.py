"""
Contract for a single command that is defined inside a plugin's commands.yaml
This is used to validate the command against the schema and to create a Command object.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.omni_logger import omni_logger
from src.packet.contracts.user import ROLE


class CommandManifest(BaseModel):
    """
    Contract for a single command that is defined inside a plugin's commands.yaml.
    Validated safely by Pydantic at runtime to ensure Core stability.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    name: str
    description: str = "No description provided"
    pattern: str
    handler: str
    plugin_name: str

    minimum_role: ROLE = Field(default=ROLE.USER, alias="Minimum_Role")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CommandManifest | None":
        """
        Safely parses a dictionary into a CommandManifest object.

        Acts as a firewall for the PluginEngine: if the YAML/Dict contains
        missing fields, invalid types, or an unrecognized ROLE string,
        it traps the error, logs it, and returns None instead of crashing.
        """
        try:
            return cls.model_validate(data)
        except ValidationError as e:
            omni_logger.debug(f"Dropped invalid command manifest payload. Schema mismatch: {e}")
            return None

    def to_dict(self) -> dict[str, Any]:
        """
        Unpacks the CommandManifest model back into a standard dictionary.
        """
        return self.model_dump()

    def __str__(self) -> str:
        return (
            f"CommandManifest(name={self.name}, "
            f"plugin={self.plugin_name}, "
            f"role={self.minimum_role})"
        )

    def __repr__(self) -> str:
        return (
            f"CommandManifest(name={self.name!r}, "
            f"pattern={self.pattern!r}, "
            f"handler={self.handler!r}, "
            f"role={self.minimum_role!r}, "
            f"plugin={self.plugin_name!r})"
        )
