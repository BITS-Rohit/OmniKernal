from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from src.omni_logger import omni_logger
from src.packet.contracts.user import ROLE


class RouteCache(BaseModel):
    """
    Immutable cache object used by the GlobalBroker Pipeline (RouterLayer)
    for O(1) command lookup.
    """

    model_config = ConfigDict(frozen=True)

    command_name: str
    pattern: str
    handler_path: str
    required_role: ROLE
    plugin_name: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RouteCache | None":
        """
        Safely parses a dictionary into a RouteCache object.

        Acts as a firewall for the RouterLayer: if the dictionary contains
        missing fields, invalid types, or an unrecognized ROLE string,
        it traps the error, logs it, and returns None instead of crashing.
        """
        try:
            return cls.model_validate(data)
        except ValidationError as e:
            omni_logger.debug(f"Dropped invalid routing cache payload. Schema mismatch: {e}")
            return None

    def to_dict(self) -> dict[str, Any]:
        """
        Unpacks the RouteCache model back into a standard dictionary.
        Automatically handles converting the ROLE Enum back into a string if needed.
        """
        return self.model_dump()

    def __str__(self) -> str:
        return (
            f"RouteCache(command={self.command_name}, "
            f"plugin={self.plugin_name}, "
            f"role={self.required_role})"
        )

    def __repr__(self) -> str:
        return (
            f"RouteCache(command_name={self.command_name!r}, "
            f"pattern={self.pattern!r}, "
            f"handler_path={self.handler_path!r}, "
            f"required_role={self.required_role!r}, "
            f"plugin_name={self.plugin_name!r})"
        )
