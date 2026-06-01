"""
CommandResult — Handler Return Contract

The typed return value every command handler must produce.
The Core reads this object to decide what to do next:
    - If .reply is set  → pipe it through adapter.send_message()
    - If .ok is False   → log the failure; if .api_url set, trigger ApiWatchdog

Invariant: Handlers NEVER call send_message() directly.
They return a CommandResult and the Core handles delivery.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, ValidationError

from src.omni_logger import omni_logger


class CommandResult(BaseModel):
    """
    The result of a command handler execution.

    Use the factory class methods to construct instances:
        CommandResult.success(reply="message")
        CommandResult.success(reply=None)   # no reply needed
        CommandResult.error(reason="why")
        CommandResult.error(reason="why", api_url="https://...") # triggers watchdog

    Attributes:
        ok:             True if the command executed successfully.
        reply:          Optional reply text. Core calls adapter.send_message() with this.
                        None means no reply is sent.
        error_reason:   Human-readable failure reason. Only set when ok=False.
                        Logged by the Core — never sent to the user directly.
        api_url:        Optional. If the failure was caused by an external API, set this
                        URL so the Core can report it to ApiWatchdog. Never set on success.
    """
    model_config = ConfigDict(frozen=True)

    ok: bool
    reply: str | None = None
    error_reason: str | None = None
    api_url: str | None = None

    @classmethod
    def success(cls, reply: str | None = None) -> CommandResult:
        """
        Build a successful result.

        Args:
            reply:  Optional reply text to send back to the user.
                    If None, the Core skips calling send_message().
        """
        return cls(ok=True, reply=reply)

    @classmethod
    def error(cls, reason: str, api_url: str | None = None) -> CommandResult:
        """
        Build a failure result.

        Args:
            reason:     Human-readable description of what went wrong.
                        This is logged — it is NOT sent to the user.
            api_url:    If the failure originated from an external API call, pass
                        its URL here so the Core can feed it to ApiWatchdog.
        """
        return cls(ok=False, error_reason=reason, api_url=api_url)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CommandResult | None:
        """
        Safely parses a dictionary into a CommandResult object.
        Traps ValidationErrors to prevent malformed handler returns from crashing the Core.
        """
        try:
            return cls.model_validate(data)
        except ValidationError as e:
            omni_logger.error(f"Invalid CommandResult payload returned from handler: {e}")
            return None

    def to_dict(self) -> dict[str, Any]:
        """
        Unpacks the CommandResult model back into a standard dictionary.
        """
        return self.model_dump()

    def __repr__(self) -> str:
        if self.ok:
            return f"CommandResult(ok=True, reply={self.reply!r})"
        return f"CommandResult(ok=False, reason={self.error_reason!r})"