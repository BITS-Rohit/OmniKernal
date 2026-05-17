"""
User — Frozen Dataclass Contract

Represents a platform user who sent a message to the bot.
Constructed by the adapter from raw platform data and passed
through the Core pipeline. Immutable — never modified in flight.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ROLE(StrEnum):
    """
    ROLE enum representing the permission role.
    ADMIN > MODERATOR > USER
    """

    USER = "USER"
    ADMIN = "ADMIN"
    MODERATOR = "MODERATOR"


@dataclass(frozen=True, slots=True)
class User:
    """
    A user who interacted with the bot on a platform.

    Attributes:
        id:           Platform-specific unique identifier (e.g. phone number, user ID).
        display_name: Human-readable name as seen on the platform.
        platform:     Platform this user belongs to (e.g. 'WhatsApp', 'telegram').
        role:         Permission role. Default 'user'. Elevated to 'admin' via config.
    """

    id: str
    display_name: str
    platform: str
    role: ROLE = ROLE.USER

    @classmethod
    def from_dict(cls, data: dict) -> User:
        return cls(
            id=data["id"],
            display_name=data["display_name"],
            platform=data["platform"],
            role=data["role"],
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "platform": self.platform,
            "role": self.role,
        }

    @property
    def is_admin(self) -> bool:
        """Return True if this user has admin role."""
        return self.role == ROLE.ADMIN

    @property
    def is_user(self) -> bool:
        """Return True if this user has user role."""
        return self.role == ROLE.USER

    @property
    def is_moderator(self)-> bool:
        """Return True if this user has moderator role."""
        return self.role == ROLE.MODERATOR

    def __str__(self) -> str:
        return f"User(id={self.id},\
                name={self.display_name},\
                platform={self.platform}, \
                role={self.role})"

    def __repr__(self) -> str:
        return f"User(id={self.id!r},\
                name={self.display_name!r},\
                platform={self.platform!r}, \
                role={self.role!r})"
