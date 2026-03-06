"""
CommandRouter — DB-backed Command Registry

Routes command triggers to their registered handler paths.
Acts as the single point of access for route lookup, keeping
the Dispatcher free of direct DB queries.

BUG 19 fix: CommandRouter is now used by EventDispatcher instead
of the dispatcher calling OmniRepository.get_tool_by_command directly.
"""

from typing import Any, Optional
from src.database.repository import OmniRepository


class CommandRouter:
    """
    Registry for all available commands.
    DB-backed in Phase 2+.

    Dispatcher uses this to resolve command_trigger -> handler_path.
    """

    def __init__(self, repository: OmniRepository):
        self.repository = repository

    async def get_route(self, command_name: str) -> Optional[dict]:
        """
        Looks up a route by command name from the database.

        Returns:
            dict with keys: command_name, pattern, handler_path, plugin_name, id
            or None if not found.
        """
        tool = await self.repository.get_tool_by_command(command_name)
        if not tool:
            return None

        return {
            "id": tool.id,
            "command_name": tool.command_name,
            "pattern": tool.pattern,
            "handler_path": tool.handler_path,
            "plugin_name": tool.plugin_name
        }

    async def list_commands(self) -> list[str]:
        """Returns all registered commands from DB."""
        tools = await self.repository.get_all_tools()
        return [t.command_name for t in tools]
