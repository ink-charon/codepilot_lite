from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class HookEvent:
    event_type: str
    tool_name: str
    arguments: dict[str, Any]
    tool_call_id: str = ""
    status: str | None = None
    output: Any = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class HookResult:
    allowed: bool = True
    message: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


HookHandler = Callable[[HookEvent], HookResult | None]


class HookManager:
    def __init__(self) -> None:
        self._hooks: dict[str, list[HookHandler]] = {}

    def register(self, event_type: str, hook: HookHandler) -> None:
        self._hooks.setdefault(event_type, []).append(hook)

    def trigger(self, event: HookEvent) -> HookResult:
        combined_extra: dict[str, Any] = {}
        messages: list[str] = []

        for hook in self._hooks.get(event.event_type, []):
            result = hook(event) or HookResult()
            combined_extra.update(result.extra)
            if result.message:
                messages.append(result.message)
            if not result.allowed:
                return HookResult(
                    allowed=False,
                    message=result.message or "Hook blocked tool execution.",
                    extra=combined_extra,
                )

        return HookResult(
            allowed=True,
            message="; ".join(messages),
            extra=combined_extra,
        )

