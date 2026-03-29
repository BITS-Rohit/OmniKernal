"""
PermissionValidator — Access Control Logic

Checks if a user has sufficient roles or permissions to execute a command.

BUG 39 fix: Added check_role() classmethod that operates on a pre-resolved
role string rather than a User object. This lets the dispatcher pass the
effective_role (after OMNIKERNAL_ADMINS elevation) without needing to mutate
the frozen User dataclass.
"""
from typing import TYPE_CHECKING
import logging
if TYPE_CHECKING:
    pass
from omnikernal.core.contracts.user import ROLE

LEVEL_SYNONYMS = {
    "owner": "admin",
    "superuser": "admin",
    "administrator": "admin",
}

ROLE_LEVELS = {
    ROLE.ANY: 0,
    ROLE.USER: 10,
    ROLE.MODERATOR: 50,
    ROLE.ADMIN: 100
}

# Todo , Add the correct logger ,

class PermissionValidator:
    """
    Checks if a user has sufficient roles or permissions to execute a command.
    """

    @classmethod
    def check_role(cls, effective_role: ROLE, required_role: str = "user") -> bool:
        """
        Hierarchical RBAC check .
        Checks if the user's role level is >= the required role level.

        # Fail-closed on unrecognized roles.
        # If 'required_role' is misspelled, default to level 100 (admin).
        # This prevents typo-ing 'admin' and accidentally opening it to 'user'.
        # Fail-closed on unrecognized roles.
        # Maps common synonyms to internal levels to prevent accidental lockout.
        # normalize to lowercase for robust dictionary lookup

        Args:
            effective_role: The resolved role string (e.g. ROLE.ADMIN, ROLE.MODERATOR, ROLE.USER).
            required_role:  Minimum role required (default 'user').

        Returns:
            True if user role meets or exceeds required level.
        """

        mapped_req = LEVEL_SYNONYMS.get(required_role.lower(), required_role.lower())
        user_role = effective_role

        try:
            req_role = ROLE(mapped_req)
        except ValueError:
            logging.info(f"Invalid role at required role detected - {required_role} , fallback to Admin Role Checking.")
            return False # Deny Access

        user_lvl = ROLE_LEVELS.get(user_role, 0)
        req_lvl = ROLE_LEVELS.get(req_role, 100)  # Default to 100 (admin)

        return user_lvl >= req_lvl
