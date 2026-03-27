"""
CommandContext — Safe Capability Surface for Handlers

The controlled object, the Core passes to every handler at execution time.
Handlers receive ONLY what they need — nothing more. This is the
single point of access for DB-backed capabilities (API key decryption,
structured logging).

Invariant: Handlers access the DB ONLY through ctx.get_api_key().
No raw DB session is ever exposed to handler scope.

The EncryptionEngine is now injected as a callable (_decrypter)
at construction time instead of being imported lazily inside get_api_key().
This eliminates the circular import risk, makes the dependency explicit to
static analyzers, and allows test code to pass a simple mock decrypter.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from omnikernal.database.repository import OmniRepository

    from .user import User


# after construction. get_api_key() only reads fields — no conflict with frozen.
@dataclass(frozen=True)
class CommandContext:
    """
    Safe, immutable capability surface provided to command handlers by the Core.

    Attributes:
        user:       The User who triggered this command.
        logger:     Structured logger scoped to this execution .
        _decrypter: callable (str) -> str provided by the Core.
                    Defaults to EncryptionEngine.decrypt if not injected.
    """

    user: User
    logger: Any = field(default=None, repr=False)
    _repository: OmniRepository | None = field(default=None, repr=False)
    _tool_id: int | None = field(default=None, repr=False)
    _decrypter: Callable[[str], str] | None = field(default=None, repr=False)

    async def get_api_key(self, service: str) -> str:
        """
        Retrieve and decrypt an API key for the given service.

        The `service` argument was previously accepted but silently
        ignored. It is now used as a human-readable label in error messages and
        debug logging, improving traceability. All API keys are stored per-tool
        (one key per tool_id) — if a future multi-key schema is added, this arg
        will become the lookup key. For now, it is a required label that must
        match the service name declared in commands.yaml.

        Args:
            service: Descriptive service name (e.g. 'YouTube's, 'openai').
            Used in error messages. Must be non-empty.

        Returns:
            Decrypted plaintext API key — only in handler scope, never logged.

        Raises:
            ValueError: If no API key is configured for this tool.
            RuntimeError: If the context is not fully initialized.
        """
        if not service:
            raise ValueError("get_api_key() requires a non-empty service name.")
        if not self._repository or self._tool_id is None:
            raise RuntimeError(
                "Repository or tool_id not configured in CommandContext."
            )

        encrypted_key = await self._repository.get_api_key(
            self._tool_id, service=service
        )
        if not encrypted_key:
            raise ValueError(
                f"No API key configured for service '{service}' (tool_id={self._tool_id}). "
                "Register it via OmniRepository.register_tool_requirement()."
            )

        # BUG 35 fix: use injected decrypter if provided (no circular import)
        if self._decrypter is not None:
            return self._decrypter(encrypted_key)

        from omnikernal.security.encryption import EncryptionEngine  # noqa: PLC0415

        return EncryptionEngine.decrypt(encrypted_key)

    def __repr__(self) -> str:
        return f"CommandContext(user={self.user!r})"
