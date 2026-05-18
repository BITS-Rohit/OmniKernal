from dataclasses import dataclass

from .user import ROLE


@dataclass(frozen=True, slots=True)
class RouteCache:
    """
    Immutable cache object used by the GlobalBroker Pipeline (RouterLayer)
    for O(1) command lookup.
    """
    command_name: str
    pattern: str
    handler_path: str
    required_role: ROLE
    plugin_name: str
