"""
User — Frozen Pydantic Contract

Represents a platform user who sent a message to the bot.
Constructed by the adapter from raw platform data and passed
through the Core pipeline. Immutable — never modified in flight.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from src.omni_logger import omni_logger


class ROLE(StrEnum):
    """
    ROLE enum representing the permission role.
    ADMIN > MODERATOR > USER
    """

    USER = "USER"
    ADMIN = "ADMIN"
    MODERATOR = "MODERATOR"


class User(BaseModel):
    """
    A user who interacted with the bot on a platform.

    Attributes:
        id:           Platform-specific unique identifier (e.g. phone number, user ID).
        display_name: Human-readable name as seen on the platform.
        platform:     Platform this user belongs to (e.g. 'WhatsApp', 'telegram').
        role:         Permission role. Default 'user'. Elevated to 'admin' via config.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    display_name: str
    platform: str
    role: ROLE = ROLE.USER

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User | None:
        """
        Safely parses a dictionary into a User object.
        Automatically coerces string roles (e.g., 'ADMIN') into ROLE Enums.
        """
        try:
            return cls.model_validate(data)
        except ValidationError as e:
            omni_logger.debug(f"Dropped invalid User payload. Schema mismatch: {e}")
            return None

    def to_dict(self) -> dict[str, Any]:
        """Unpacks the User model back into a standard dictionary."""
        return self.model_dump()

    @property
    def is_admin(self) -> bool:
        """Return True if this user has admin role."""
        return self.role == ROLE.ADMIN

    @property
    def is_user(self) -> bool:
        """Return True if this user has user role."""
        return self.role == ROLE.USER

    @property
    def is_moderator(self) -> bool:
        """Return True if this user has moderator role."""
        return self.role == ROLE.MODERATOR

    def __str__(self) -> str:
        return (
            f"User(id={self.id}, "
            f"name={self.display_name}, "
            f"platform={self.platform}, "
            f"role={self.role})"
        )

    def __repr__(self) -> str:
        return (
            f"User(id={self.id!r}, "
            f"name={self.display_name!r}, "
            f"platform={self.platform!r}, "
            f"role={self.role!r})"
        )
