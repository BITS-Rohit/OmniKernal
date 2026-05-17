from __future__ import annotations

from dataclasses import dataclass, field
from logging import Logger, LoggerAdapter
from typing import Any

from omnikernal.core.contracts import ROLE, CommandResult, Message
from omnikernal.omni_logger import omni_looger

from .packet_state import PacketState


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

    Layers Order :
    1. resolve cmd name from cache.
    2. User Role Permissions.
    3. maps exe.run process.
    4. Sanitize the packet.
    5. parse the message raw-text to create cli based headers and vals and store in packet.
    6. execute the mapped func and update the result field in the packet.
    7. Response back to user(using adapter's send_message() method), sends `reply` content to user.
    8. If failed any process , Routed to Hitory or watch Dog for later inspection.


    Handler API (what plugin devs use):
        ctx.resolve("reply text")       # success
        ctx.fail("reason string")       # failure
        ctx.set_flag("key", value)      # attach dynamic data
        ctx.get_flag("key", default)    # read dynamic data
        await ctx.get_api_key("svc")    # decrypt stored API key

    Attributes:
        message: Type = Message — inbound platform message (immutable).
        state:   Type = PacketState, Current pipeline stage (PacketState enum).
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
    required_role : ROLE | None = None
    mapped_handler : str | None = None
    logger: Logger | LoggerAdapter = field(default_factory=omni_looger)
    tool_id: int | None = None
    message_cli_args: dict[str, str] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
    result: CommandResult | None = None

    @classmethod
    def from_dict(cls, data: dict, logger : Logger | LoggerAdapter|None = None) -> IntentPacket:
        return cls(
            message=Message.from_dict(data["message"]),
            logger= omni_looger if logger is None else logger,
            state=PacketState(data["state"]),
            mapped_handler=data["mapped_handler"],
            required_role=ROLE(data["required_role"]),
            tool_id=data.get("tool_id"),
            message_cli_args=data.get("message_cli_args", {}),
            flags=data.get("flags", {}),
            result=CommandResult.from_dict(data["result"]) if data.get("result") else None,
        )

    def to_dict(self) -> dict:

        return {
            "state": self.state.value,
            "tool_id": self.tool_id,
            "required_role": self.required_role,
            "message": self.message.to_dict() if self.message else None,
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

    # ------------------------------------------------------------------
    # Dynamic Flags API
    # ------------------------------------------------------------------

    def set_flag(self, key: str, value: Any) -> None:
        """Attach a dynamic attribute to this packet."""
        self.flags[key] = value

    def get_flag(self, key: str, default: Any = None) -> Any:
        """Read a dynamic attribute. Returns default if not set."""
        return self.flags.get(key, default)

    @property
    def user(self):
        return self.message.user

    @property
    def platform(self):
        return self.message.platform

    @property
    def raw_text(self):
        return self.message.raw_text

    def __repr__(self) -> str:
        return (
            f"IntentPacket(platform={self.platform!r}, state={self.state.value!r})"
        )


# ---------------------------------------------------------------------------
# Decorator: Dynamic Flag Injection
# ---------------------------------------------------------------------------
# Usage in commands.yaml or handler registration:
#
#   @inject_flags(target="group", priority="high")
#   async def run(packet: IntentPacket) -> None:
#       grp = packet.get_flag("target")   # → "group"
#
# The decorator wraps the handler and calls packet.set_flag()
# before execution. Allows per-command flag schemas defined
# declaratively without modifying handler signatures.


# def inject_flags(**flags: Any):
#     """
#     Decorator factory. Injects static flags into the packet before handler runs.

#     Example:
#         @inject_flags(scope="admin", notify=True)
#         async def run(packet: IntentPacket) -> None:
#             if packet.get_flag("notify"):
#                 ...
#     """

#     def decorator(func):
#         import functools

#         @functools.wraps(func)
#         async def wrapper(packet: IntentPacket, *args, **kwargs):
#             for key, value in flags.items():
#                 packet.set_flag(key, value)
#             return await func(packet, *args, **kwargs)

#         return wrapper

#     return decorator

# Todo  , check the flow for Command Result , tp engine.py to adhere the new IntentPacket structure.
