"""Hook package."""

from my_agent.hooks.base import HookEvent, HookManager, HookResult
from my_agent.hooks.logging import LoggingHook
from my_agent.hooks.permission import PermissionHook

__all__ = [
    "HookEvent",
    "HookManager",
    "HookResult",
    "LoggingHook",
    "PermissionHook",
]
