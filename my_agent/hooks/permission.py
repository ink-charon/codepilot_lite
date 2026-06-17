from __future__ import annotations

import re
from typing import Any

from my_agent.hooks.base import HookEvent, HookResult
from my_agent.workspace.manager import WorkspaceManager


class PermissionHook:
    def __init__(self, workspace: WorkspaceManager) -> None:
        self.workspace = workspace
        self.path_tools = {"read_file", "write_file", "edit_file", "list_dir"}
        self.confirmation_tools = {"write_file", "edit_file", "run_command"}
        self.dangerous_command_patterns = [
            r"\brm\s+-rf\s+/",
            r"\brm\s+-rf\s+\*",
            r"\bdel\s+/s\s+/q\s+c:\\",
            r"\bformat\b",
            r"\bshutdown\b",
            r"\breboot\b",
            r"\bremove-item\b.*\s-recurse\b.*\s-force\b.*c:\\",
            r"\bstop-computer\b",
            r"\brestart-computer\b",
        ]

    def __call__(self, event: HookEvent) -> HookResult:
        if event.event_type != "PreToolUse":
            return HookResult()

        try:
            if event.tool_name in self.path_tools:
                self._check_workspace_path(event.tool_name, event.arguments)
            if event.tool_name == "run_command":
                self._check_command(event.arguments)
        except Exception as exc:
            return HookResult(allowed=False, message=str(exc))

        if event.tool_name in self.confirmation_tools:
            return HookResult(allowed=True, extra={"requires_confirmation": True})
        return HookResult()

    def _check_workspace_path(self, tool_name: str, arguments: dict[str, Any]) -> None:
        path = arguments.get("path", ".") if tool_name == "list_dir" else arguments.get("path")
        if not isinstance(path, str):
            raise ValueError("path must be a string.")
        self.workspace.resolve_path(path)

    def _check_command(self, arguments: dict[str, Any]) -> None:
        command = arguments.get("command")
        if not isinstance(command, str):
            raise ValueError("command must be a string.")
        for pattern in self.dangerous_command_patterns:
            if re.search(pattern, command, flags=re.IGNORECASE):
                raise ValueError(f"Dangerous command blocked by permission hook: {command}")

