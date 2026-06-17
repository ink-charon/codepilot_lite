from __future__ import annotations

from typing import Any


class ConfirmationProvider:
    def confirm(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        reason: str | None = None,
    ) -> bool:
        raise NotImplementedError


class CliConfirmationProvider(ConfirmationProvider):
    def confirm(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        reason: str | None = None,
    ) -> bool:
        print(f"Tool requires confirmation: {tool_name}")
        print(f"Arguments: {self._summarize_arguments(arguments)}")
        if reason:
            print(f"Reason: {reason}")
        response = input("Allow this tool call? [y/N] ")
        return response.strip().lower() in {"y", "yes"}

    def _summarize_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        summarized: dict[str, Any] = {}
        for key, value in arguments.items():
            if isinstance(value, str) and len(value) > 200:
                summarized[key] = value[:200] + "...[truncated]"
            else:
                summarized[key] = value
        return summarized


class AutoApproveConfirmationProvider(ConfirmationProvider):
    def confirm(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        reason: str | None = None,
    ) -> bool:
        return True


class AutoDenyConfirmationProvider(ConfirmationProvider):
    def confirm(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        reason: str | None = None,
    ) -> bool:
        return False

