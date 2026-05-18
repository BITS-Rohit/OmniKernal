from __future__ import annotations

from dataclasses import dataclass, field
from logging import Logger, LoggerAdapter
from typing import Any

from omnikernal.core.omni_logger import omni_logger

from .command_result import CommandResult
from .message import Message
from .packet_state import PacketState
from .user import ROLE, User


@dataclass(slots=True)
class IntentPacket:
    """
    The single unified packet that travels the entire OmniKernal pipeline.

    Replaces the split (CommandContext + CommandResult) pattern.

    Lifecycle:
        1. Gloabal Broker creates packet using IntentPacket and pushes it to global queue.
        2. consumers sees the packet, consume it and asynchronously processes it througth dedicated layers.
        3. Layers and handlers can modify the packet. state can be modified using handlers resolve(), fail() and drop() methods.
        4. Once the packet is processed, it can be discarded or stored in history.


    Handler API (what plugin devs use):
        ctx.resolve("reply text")       # success
        ctx.fail("reason string")       # failure
        ctx.set_flag("key", value)      # attach dynamic data
        ctx.get_flag("key", default)    # read dynamic data
        await ctx.get_api_key("svc")    # decrypt stored API key

    Attributes:
        message: Type = Message — inbound platform message (immutable).
        state:   Type = PacketState, Current pipeline stage (PacketState enum).
        sanitized_text : str | None = None , Contains the sanitized text.
        required_role : Type = ROLE | None — Required role for the command (ROLE enum).
        mapped_handler : Type = str — gives Execution handler.
        logger:  Type = Logger — execution scoped logger.
        tool_id: Type = int | None — set at ROUTED stage.
        args:    Type = dict, Parsed command arguments dict. Populated by Parser at ROUTED.
        flags:   Type = dict, Dynamic per-message attributes. Populated by --p / --t style
                 decorator injection OR handler code. Type-unsafe by design.
        result:  Type = CommandResult | None , Set by handler via ctx.resolve() / ctx.fail().
                 None until EXECUTING state.
    """

    message: Message
    state: PacketState = PacketState.RECEIVED
    sanitized_text: str | None = None
    required_role: ROLE | None = None
    mapped_handler: str | None = None
    logger: Logger | LoggerAdapter[Any] = field(default_factory=lambda: omni_logger)
    tool_id: int | None = None
    message_cli_args: dict[str, str] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
    result: CommandResult | None = None

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        logger: Logger | LoggerAdapter[Any] | None = None,
    ) -> IntentPacket:
        return cls(
            message=Message.from_dict(data["message"]),
            sanitized_text=data.get("sanitized_text"),
            logger=omni_logger if logger is None else logger,
            state=PacketState(data["state"]),
            mapped_handler=data["mapped_handler"],
            required_role=ROLE(data["required_role"]),
            tool_id=data.get("tool_id"),
            message_cli_args=data.get("message_cli_args", {}),
            flags=data.get("flags", {}),
            result=CommandResult.from_dict(data["result"]) if data.get("result") else None,
        )

    def to_dict(self) -> dict[str, Any]:

        return {
            "state": self.state.value,
            "tool_id": self.tool_id,
            "required_role": self.required_role,
            "message": self.message.to_dict() if self.message else None,
            "sanitized_text": self.sanitized_text,
            "args": self.message_cli_args,
            "flags": self.flags,
            "result": self.result.to_dict() if self.result else None,
        }

    # ------------------------------------------------------------------
    # Handler-facing API
    # ------------------------------------------------------------------

    def resolve(self, reply: str | None = None) -> None:
        """
        Mark command as successfully executed.
        Sets result to CommandResult.success and transitions to DONE.
        """
        from omnikernal.core.contracts.command_result import CommandResult

        self.result = CommandResult.success(reply=reply)
        self.state = PacketState.DONE

    def fail(self, reason: str, api_url: str | None = None) -> None:
        """
        Mark command as failed.
        Sets result to CommandResult.error and transitions to FAILED.
        """
        from omnikernal.core.contracts.command_result import CommandResult

        self.result = CommandResult.error(reason=reason, api_url=api_url)
        self.state = PacketState.FAILED

    def drop(self) -> None:
        """
        Mark packet as dropped (no route found or pre-check failed).
        Transitions to DROPPED. Engine will log and discard silently.
        """
        self.state = PacketState.DROPPED

    @property
    def user(self)-> User:
        return self.message.user

    @property
    def platform(self)-> str:
        return self.message.platform

    @property
    def raw_text(self) -> str:
        return self.message.raw_text

    def __repr__(self) -> str:
        return (
            f"IntentPacket(platform={self.platform!r}, state={self.state.value!r})"
        )
