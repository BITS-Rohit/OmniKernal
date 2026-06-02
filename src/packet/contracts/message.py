"""
Message — Frozen Pydantic Contract

Represents an inbound message returned by adapter.fetch_new_messages().
The Core never constructs this directly — the adapter builds it from
raw platform data (DOM elements, socket payloads, API responses).
Immutable — passed read-only through the entire processing pipeline.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from src.omni_logger import omni_logger
from src.packet.contracts.user import User
from src.plugin.interfaces import PlatformAdapter


class Message(BaseModel):
    """
    An inbound platform message ready for Core processing.

    Attributes:
        id:        Platform-specific message identifier (for dedup / ack).
        raw_text:  The original message text — NOT yet sanitized.
                   The Core passes this through CommandSanitizer before parsing.
        user:      The User who sent this message.
        timestamp: When the message was received (platform time).
        platform:  Which platform this message came from.
        adapter:   PlatformAdapter | None — platform specific adapter
    """

    model_config = ConfigDict(
        frozen=True,
        arbitrary_types_allowed=True,
        revalidate_instances="never",
        from_attributes=True,
    )

    id: str
    raw_text: str
    user: User
    timestamp: datetime
    platform: str
    adapter: PlatformAdapter | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message | None:
        """
        Safely parses a dictionary into a Message object.
        Returns None instead of throwing an exception if the schema is invalid,
        acting as a firewall for the Core application.
        """
        try:
            return cls.model_validate(data)
        except ValidationError as e:
            omni_logger.debug(f"Dropped invalid platform payload. Schema mismatch: {e}")
            return None

    def to_dict(self) -> dict[str, Any]:
        """
        Unpacks the Pydantic model back into a standard dictionary.
        Automatically converts nested models (like User) into dictionaries as well.
        """
        return self.model_dump()

    def __str__(self) -> str:
        return (
            f"Message("
            f"id={self.id}, "
            f"raw_text={self.raw_text!r}, "
            f"user={self.user}, "
            f"timestamp={self.timestamp}, "
            f"platform={self.platform}"
            f")"
        )

    def __repr__(self) -> str:
        preview = self.raw_text[:40] + "..." if len(self.raw_text) > 40 else self.raw_text
        return f"Message(id={self.id!r}, from={self.user.id!r}, text={preview!r})"
