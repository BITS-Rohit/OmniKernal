"""
CommandRouter — DB-backed Command Registry

Routes command triggers to their registered handler paths.
Acts as the single point of access for route lookup, keeping
the Dispatcher free of direct DB queries.

CommandRouter is now used by EventDispatcher instead
of the dispatcher calling OmniRepository.get_tool_by_command directly.

get_route() now checks the routing_rules table first for
regex-based overrides before falling back to exact command name lookup.
This implements routing strategy.

routing_rules are cached in memory after the first load.
Rules rarely change at runtime; loading them from the DB on every
message (default 1s poll) was a needless DB round-trip per message.
Call invalidate_route_cache() after inserting a new routing rule.

tool_cache: all registered tools are bulk-loaded from DB once on first
lookup miss and stored as dict[command_name → route_dict]. Subsequent
lookups are pure Python O(1) dict access with no DB round-trip, enabling
true sub-millisecond resolution latency at scale (500+ plugins).
Call clear_route_cache() to invalidate both rules and tool cache together.
"""

import re
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from omnikernal.database.repository import OmniRepository


class RulesCache:
    """
    Mutable container for cached routing rules and tool lookup map.
    Allows sharing a cache across multiple ephemeral CommandRouter instances.

    tool_cache: populated lazily on first tool lookup miss.
    Maps command_name (str) → pre-built route dict so get_route() never
    hits the DB again after the initial bulk load.
    """

    def __init__(self) -> None:
        self.rules: Sequence[Any] | None = None
        # store regex cache in shared container so it persists across messages
        self.regex_cache: dict[str, re.Pattern] = {}
        # tool lookup cache — None means "not loaded yet"; {} means "loaded, empty"
        self.tool_cache: dict[str, dict[str, Any]] | None = None


class CommandRouter:
    """
    Registry for all available commands.
    Dispatcher uses this to resolve a command trigger → route dict.
    Resolution order:
      1. Check routing_rules table — first regex pattern that matches wins.
      2. Check in-memory tool_cache (bulk-loaded once from DB on first miss).
      3. Fall back to a single DB SELECT only if cache is disabled.

    routing_rules and tool_cache are loaded once and shared via RulesCache.
    Call clear_route_cache() if plugins are added/removed at runtime.
    """

    def __init__(self, repository: OmniRepository, cache: RulesCache | None = None) -> None:
        self.repository = repository
        # use shared cache if provided, else local one
        self._shared_cache = cache
        self._local_cache: Sequence[Any] | None = None
        # regex cache container (instance-local or shared)
        self._local_regex_cache: dict[str, re.Pattern] = {}
        # tool cache (instance-local fallback when no shared cache is used)
        self._local_tool_cache: dict[str, dict[str, Any]] | None = None

    @property
    def _rules(self) -> Sequence[Any] | None:
        if self._shared_cache:
            return self._shared_cache.rules
        return self._local_cache

    @_rules.setter
    def _rules(self, value: Sequence[Any]) -> None:
        if self._shared_cache:
            self._shared_cache.rules = value
        else:
            self._local_cache = value

    def clear_route_cache(self) -> None:
        """Clears cached routing rules and tool lookup map."""
        if self._shared_cache:
            self._shared_cache.rules = None
            self._shared_cache.regex_cache.clear()
            self._shared_cache.tool_cache = None
        else:
            self._local_cache = None
            self._local_regex_cache.clear()
            self._local_tool_cache = None

    def _get_compiled_regex(self, pattern: str) -> re.Pattern:
        """
        Get pre-compiled regex from the correct cache.
        """
        cache_dict = (
            self._shared_cache.regex_cache if self._shared_cache else self._local_regex_cache
        )
        if pattern not in cache_dict:
            cache_dict[pattern] = re.compile(pattern)
        return cache_dict[pattern]

    @property
    def _tool_cache(self) -> dict[str, dict[str, Any]] | None:
        if self._shared_cache:
            return self._shared_cache.tool_cache
        return self._local_tool_cache

    @_tool_cache.setter
    def _tool_cache(self, value: dict[str, dict[str, Any]]) -> None:
        if self._shared_cache:
            self._shared_cache.tool_cache = value
        else:
            self._local_tool_cache = value

    async def _ensure_tool_cache(self) -> dict[str, dict[str, Any]]:
        """
        Bulk-loads all tools from DB once and stores them in a dict.
        Subsequent calls return the already-populated dict instantly (O(1)).
        """
        if self._tool_cache is not None:
            return self._tool_cache

        tools = await self.repository.get_all_tools()
        cache: dict[str, dict[str, Any]] = {
            t.command_name: {
                "id": t.id,
                "command_name": t.command_name,
                "pattern": t.pattern,
                "handler_path": t.handler_path,
                "plugin_name": t.plugin_name,
                "required_role": t.required_role,
            }
            for t in tools
        }
        self._tool_cache = cache
        return cache

    async def get_route(self, command_trigger: str) -> dict[str, Any] | None:
        """
        Looks up a route by command trigger.

        Resolution order:
          1. routing_rules (regex overrides) — cached after first load.
          2. tool_cache (bulk-loaded once) — O(1) dict lookup, no DB hit.

        Args:
            command_trigger: The raw command name without '!' (e.g. 'echo').

        Returns:
            dict with keys: id, command_name, pattern, handler_path, plugin_name
            or None if no route is found.
        """
        # Step 1 — routing_rules (cached after first call)
        if self._rules is None:
            self._rules = await self.repository.get_all_routing_rules()

        rules = self._rules or []
        for rule in rules:
            try:
                pattern_obj = self._get_compiled_regex(rule.regex_pattern)
                if pattern_obj.fullmatch(command_trigger):
                    tool = rule.tool
                    if tool:
                        return {
                            "id": tool.id,
                            "command_name": tool.command_name,
                            "pattern": tool.pattern,
                            "handler_path": tool.handler_path,
                            "plugin_name": tool.plugin_name,
                            "required_role": tool.required_role,
                            "_via_routing_rule": rule.regex_pattern,
                        }
            except re.error:
                # Malformed regex in DB — skip gracefully
                continue

        # Step 2 — in-memory tool cache (bulk-loaded once, O(1) lookup)
        tool_map = await self._ensure_tool_cache()
        return tool_map.get(command_trigger.lower())

    async def list_commands(self) -> dict[str, list[str]]:
        """Returns all registered commands, grouped by plugin."""
        tools = await self.repository.get_all_tools()
        grouped = defaultdict(list)
        for t in tools:
            grouped[t.plugin_name].append(t.command_name)
        return dict(grouped)
