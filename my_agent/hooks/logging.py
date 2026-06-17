from __future__ import annotations

from my_agent.hooks.base import HookEvent, HookResult


class LoggingHook:
    def __init__(self) -> None:
        self.events: list[HookEvent] = []

    def __call__(self, event: HookEvent) -> HookResult:
        if event.event_type == "PostToolUse":
            self.events.append(event)
        return HookResult()

