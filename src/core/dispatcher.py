"""
EventDispatcher — Command Routing & Execution Pipeline

Coordinates the "Process" pipeline:
    sanitized text → route lookup → permission check → parse → execute

BUG 19 fix: Uses CommandRouter for route resolution instead of calling
OmniRepository directly — respects the architectural layering.

BUG 20 fix: Re-checks user role against OMNIKERNAL_ADMINS env var before
permission validation so admin features are actually reachable.
"""

import os
import importlib
from typing import TYPE_CHECKING, Any, Optional
from src.core.router import CommandRouter                         # BUG 19
from src.core.parser import CommandParser
from src.core.permissions import PermissionValidator
from src.core.contracts.command_result import CommandResult
from src.core.contracts.command_context import CommandContext

if TYPE_CHECKING:
    from src.database.repository import OmniRepository
    from src.core.contracts.user import User


# BUG 20: comma-separated list of platform user IDs that are admins,
# e.g. OMNIKERNAL_ADMINS=+91xxxxxxxxxx,admin_user
_ADMIN_IDS: frozenset[str] = frozenset(
    uid.strip()
    for uid in os.getenv("OMNIKERNAL_ADMINS", "").split(",")
    if uid.strip()
)


def _resolve_role(user: "User") -> str:
    """
    BUG 20 fix: Returns the effective role for a user.
    If the user's platform ID appears in OMNIKERNAL_ADMINS, they get 'admin'.
    """
    if user.id in _ADMIN_IDS:
        return "admin"
    return user.role


class EventDispatcher:
    """
    Coordinates the "Process" pipeline.
    DB-backed in Phase 2. Uses CommandRouter for route resolution (Phase 3).
    """

    def __init__(self, repository: "OmniRepository", logger: Any = None):
        self.repository = repository
        # BUG 19 fix: route resolution goes through CommandRouter, not repo directly
        self.router = CommandRouter(repository)
        self.logger = logger

    async def dispatch(self, sanitized_text: str, user: "User") -> Optional[CommandResult]:
        if not sanitized_text.startswith("!"):
            return None

        parts = sanitized_text.split(" ", 1)
        command_trigger = parts[0][1:].lower()

        # 1. Lookup route via CommandRouter (BUG 19)
        route = await self.router.get_route(command_trigger)
        if not route:
            return None

        # 2. BUG 20 fix: resolve effective role (env-var admin check) before ACL
        effective_role = _resolve_role(user)
        # Build an effective user with corrected role for permission check
        # (User is frozen, so we check the effective_role string directly)
        if effective_role != "admin" and not PermissionValidator.check_permission(
            user, required_role="user"
        ):
            return CommandResult.error("Permission denied")

        # 3. Parse arguments using the pattern from the route
        args = CommandParser.match(sanitized_text, route["pattern"])
        if args is None:
            return CommandResult.error(f"Usage: {route['pattern']}")

        # 4. Execute handler (lazy import)
        try:
            module_path, func_name = route["handler_path"].rsplit(".", 1)
            module = importlib.import_module(module_path)
            handler_func = getattr(module, func_name)

            ctx = CommandContext(
                user=user,
                logger=self.logger,
                _repository=self.repository,
                _tool_id=route["id"]
            )
            result = await handler_func(args, ctx)
            return result
        except Exception as e:
            if self.logger:
                self.logger.error(f"Dispatcher error executing {command_trigger}: {e}")
            return CommandResult.error(f"Execution failed: {str(e)}")
