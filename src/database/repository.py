"""
Database Repository — Encapsulated SQL Logic

Isolates all SQLAlchemy queries. Ensures parameterized inputs and
consistent error handling.
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnikernal.packet.contracts import CommandManifest, PluginManifest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from omnikernal.packet.contracts import ROLE, RouteCache

from .models import (
    ExecutionLog,
    Plugin,
    Tool,
)


class OmniRepository:
    """
    Main repository for all OmniKernal data access.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Plugin & Tool Registry ---

    async def register_plugins(self, plugins: list["PluginManifest"]) -> None:
        """Registers or updates plugins in a single batch query (Upsert)."""
        if not plugins:
            return

        from sqlalchemy.dialects.sqlite import insert

        stmt = insert(Plugin).values(
            [
                {
                    "name": p.name,
                    "version": p.version,
                    "author": p.author,
                    "description": p.description,
                    "is_active": True,
                }
                for p in plugins
            ]
        )

        # ON CONFLICT UPDATE
        stmt = stmt.on_conflict_do_update(
            index_elements=["name"],
            set_=dict(
                version=stmt.excluded.version,
                author=stmt.excluded.author,
                description=stmt.excluded.description,
                # Intentionally not updating is_active to preserve user overrides
            ),
        )

        await self.session.execute(stmt)
        await self.session.commit()

    async def register_tools(self, tools: list["CommandManifest"]) -> None:
        """Registers or updates tools in a single batch query (Upsert)."""
        if not tools:
            return

        from sqlalchemy.dialects.sqlite import insert

        stmt = insert(Tool).values(
            [
                {
                    "command_name": t.name,
                    "pattern": t.pattern,
                    "handler_path": t.handler,
                    "plugin_name": t.plugin_name,
                    "description": t.description,
                    "required_role": t.minimum_role,
                }
                for t in tools
            ]
        )

        # ON CONFLICT UPDATE
        stmt = stmt.on_conflict_do_update(
            index_elements=["command_name"],
            set_=dict(
                pattern=stmt.excluded.pattern,
                handler_path=stmt.excluded.handler_path,
                description=stmt.excluded.description,
                plugin_name=stmt.excluded.plugin_name,
                required_role=stmt.excluded.required_role,
            ),
        )

        await self.session.execute(stmt)
        await self.session.commit()

    async def get_tool_by_command(self, command_name: str) -> Tool | None:
        """Looks up a tool by its !command trigger."""
        result = await self.session.execute(select(Tool).where(Tool.command_name == command_name))
        return result.scalar_one_or_none()

    async def get_tool_by_id(self, tool_id: int) -> Tool | None:
        """Looks up a tool by its integer primary key."""
        return await self.session.get(Tool, tool_id)

    async def get_all_tools(self) -> Sequence[Tool]:
        """Returns all registered tools."""
        result = await self.session.execute(select(Tool))
        return result.scalars().all()

    async def get_routing_cache(self) -> dict[str, "RouteCache"]:
        """Returns an O(1) lookup dictionary of RouteCache objects for all ACTIVE commands."""

        # We need joinedload to check if the parent Plugin is active
        result = await self.session.execute(select(Tool).options(joinedload(Tool.plugin)))
        tools = result.scalars().all()

        cache = {}
        for t in tools:
            # Only cache tools whose parent plugin is active!
            if t.plugin and t.plugin.is_active:
                cache[t.command_name] = RouteCache(
                    command_name=t.command_name,
                    pattern=t.pattern,
                    handler_path=t.handler_path,
                    required_role=ROLE(t.required_role),
                    plugin_name=t.plugin_name,
                )
        return cache

    async def get_all_plugins(self) -> Sequence[Plugin]:
        """Returns all registered plugins (active and inactive)."""
        result = await self.session.execute(select(Plugin))
        return result.scalars().all()

    async def remove_plugins(self, plugin_names: list[str]) -> None:
        """Hard deletes plugins and cascades to their tools."""
        from sqlalchemy import delete

        if not plugin_names:
            return
        await self.session.execute(delete(Plugin).where(Plugin.name.in_(plugin_names)))
        await self.session.commit()

    async def remove_missing_plugins(self, active_names: list[str]) -> None:
        """Hard deletes plugins NOT in the list."""
        from sqlalchemy import delete

        if not active_names:
            # If no active plugins, delete everything
            await self.session.execute(delete(Plugin))
        else:
            await self.session.execute(delete(Plugin).where(Plugin.name.notin_(active_names)))
        await self.session.commit()

    # --- Execution Logging ---

    async def log_execution(
        self,
        user_id: str,
        platform: str,
        command_name: str,
        raw_input: str,
        success: bool,
        response_time_ms: float | None = None,
        error_reason: str | None = None,
    ) -> None:
        """Adds a record to the audit trail.sanitized."""
        # Sanitize error reason specifically for audit logs to prevent injection
        from omnikernal.packet.layers.sanitizer import CommandSanitizer

        safe_reason = CommandSanitizer._clean(error_reason) if error_reason else None

        log = ExecutionLog(
            user_id=user_id,
            platform=platform,
            command_name=command_name,
            raw_input=raw_input,
            success=success,
            response_time_ms=response_time_ms,
            error_reason=safe_reason,
        )
        self.session.add(log)
        await self.session.commit()
