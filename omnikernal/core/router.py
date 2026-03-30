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
"""

import re
from collections import defaultdict
from collections.abc import Sequence
from typing import Any

from omnikernal.database.repository import OmniRepository


class RulesCache:
    """
    Mutable container for cached routing rules .
    Allows sharing a cache across multiple ephemeral CommandRouter instances.
    """

    def __init__(self) -> None:
        self.rules: Sequence[Any] | None = None
        # store regex cache in shared container so it persists across messages
        self.regex_cache: dict[str, re.Pattern] = {}


class CommandRouter:
    """
    Registry for all available commands.
    Dispatcher uses this to resolve a command trigger → route dict.
    Resolution order:
      1. Check routing_rules table — first regex pattern that matches wins.
      2. Fall back to exact command name lookup in the tools table.

    routing_rules are loaded once and cached.
    Call invalidate_route_cache() if rules change at runtime.
    """

    def __init__(
        self, repository: OmniRepository, cache: RulesCache | None = None
    ) -> None:
        self.repository = repository
        # use shared cache if provided, else local one
        self._shared_cache = cache
        self._local_cache: Sequence[Any] | None = None
        # regex cache container (instance-local or shared)
        self._local_regex_cache: dict[str, re.Pattern] = {}

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
        """Clears the cached routing rules."""
        if self._shared_cache:
            self._shared_cache.rules = None
            self._shared_cache.regex_cache.clear()
        else:
            self._local_cache = None
            self._local_regex_cache.clear()

    def _get_compiled_regex(self, pattern: str) -> re.Pattern:
        """
        Get pre-compiled regex from the correct cache.
        """
        cache_dict = (
            self._shared_cache.regex_cache
            if self._shared_cache
            else self._local_regex_cache
        )
        if pattern not in cache_dict:
            cache_dict[pattern] = re.compile(pattern)
        return cache_dict[pattern]

    async def get_route(self, command_trigger: str) -> dict[str, Any] | None:
        """
        Looks up a route by command trigger.

        Checks routing_rules (regex overrides) first, then
        falls back to the exact tool command_name lookup.

        routing_rules are cached after first load.

        Args:
            command_trigger: The raw command name without '!' (e.g. 'echo').

        Returns:
            dict with keys: id, command_name, pattern, handler_path, plugin_name
            or None if no route is found.
        """
        #  Load rules (cached after first call)
        if self._rules is None:
            self._rules = await self.repository.get_all_routing_rules()

        rules = self._rules or []
        for rule in rules:
            try:
                # use pre-compiled regex from cache
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
                # Malformed regex in DB — skip this rule gracefully
                # Maybe we should consider deleting that malformed regex to remove with tool & handle state association
                continue

        tool = await self.repository.get_tool_by_command(command_trigger.lower())
        if not tool:
            return None

        return {
            "id": tool.id,
            "command_name": tool.command_name,
            "pattern": tool.pattern,
            "handler_path": tool.handler_path,
            "plugin_name": tool.plugin_name,
            "required_role": tool.required_role,
        }

    async def list_commands(self) -> dict[str, list[str]]:
        """Returns all registered commands, grouped by plugin."""
        tools = await self.repository.get_all_tools()
        grouped = defaultdict(list)
        for t in tools:
            grouped[t.plugin_name].append(t.command_name)
        return dict(grouped)
