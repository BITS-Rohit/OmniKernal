"""
Message — Frozen Dataclass Contract

Represents an inbound message returned by adapter.fetch_new_messages().
The Core never constructs this directly — the adapter builds it from
raw platform data (DOM elements, socket payloads, API responses).
Immutable — passed read-only through the entire processing pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from .user import User

if TYPE_CHECKING:
    from omnikernal.core.interfaces import PlatformAdapter

@dataclass(frozen=True, slots=True)
class Message:
    """
    An inbound platform message ready for Core processing.

    Attributes:
        id:        Platform-specific message identifier (for dedup / ack).
        raw_text:  The original message text — NOT yet sanitized.
                   The Core passes this through CommandSanitizer before parsing.
        user:      The User who sent this message ( id,display_name,platform ,role ).
        timestamp: When the message was received (platform time).
        platform:  Which platform this message came from.
        adapter:   PlatformAdapter | None — platform specific adapter
    """

    id: str
    raw_text: str
    user: User
    timestamp: datetime
    platform: str
    adapter: PlatformAdapter | None = None


    @classmethod
    def from_dict(cls, data: dict[str , Any]) -> Message:
        """
        Create a Message from a dictionary and returns it.
        """
        Message._validate(data)

        return cls(
            id=data["id"],
            raw_text=data["raw_text"],
            user=User.from_dict(data["user"]),
            timestamp=data["timestamp"],
            platform=data["platform"] or data["user"]["platform"] or data["user"].platform,
            adapter=data.get("adapter")
        )

    @staticmethod
    def _validate(data : dict[str , str| User])-> None:
        if data["user"] is None:
            raise ValueError("User must be given in `Message` Model.")
        if data["id"] is None:
            raise ValueError("Message ID must be given in `Message` Model.")
        if data["raw_text"] is None:
            raise ValueError("Raw text must be given in `Message` Model.")
        if data["timestamp"] is None:
            raise ValueError("Timestamp must be given in `Message` Model.")
        if data["platform"] is None:
            raise ValueError("Platform must be given in `Message` Model.")

    def to_dict(self) -> dict[str , Any]:
        """
        Convert a Message to a dictionary.
        """
        return {
            "id": self.id,
            "raw_text": self.raw_text,
            "user": self.user,
            "timestamp": self.timestamp,
            "platform": self.platform,
            "adapter": self.adapter,
        }

    def __str__(self) -> str:
        return f"Message( \
            id={self.id},\
            raw_text={self.raw_text},\
            user={self.user},\
            timestamp={self.timestamp},\
            platform={self.platform}\
        )"

    def __repr__(self) -> str:
        preview = self.raw_text[:40] + "..." if len(self.raw_text) > 40 else self.raw_text
        return f"Message(id={self.id!r}, from={self.user.id!r}, text={preview!r})"
