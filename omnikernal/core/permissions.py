"""
PermissionValidator — Access Control Logic

Checks if a user has sufficient roles or permissions to execute a command.

"""
from omnikernal.core.contracts import ROLE

role_order = [ROLE.USER, ROLE.MODERATOR, ROLE.ADMIN]

class PermissionValidator:

    @staticmethod
    def resolve_permission(required : ROLE, actual : ROLE) -> bool:
        """
        Resolves and compares permission levels.

        Args:
            required: The required permission level
            actual: The actual permission level

        Returns:
            True if actual permission is equal to or higher than required, False otherwise
        """
        re , ac = PermissionValidator._resolve_numbers(required , actual)
        return ac >= re

    @staticmethod
    def _resolve_numbers(required : ROLE, actual : ROLE) -> tuple[int, int]:
        """
        Resolves permission levels to their numerical order.

        Args:
            required: The required permission level
            actual: The actual permission level

        Returns:
            A tuple containing the numerical indices of the required and actual roles
        """
        return role_order.index(required), role_order.index(actual)
