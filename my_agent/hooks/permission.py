from __future__ import annotations

from typing import Any

from my_agent.hooks.base import HookEvent, HookResult
from my_agent.policy.policy import PermissionDecision, PermissionPolicy
from my_agent.workspace.manager import WorkspaceManager


class PermissionHook:
    def __init__(self, workspace: WorkspaceManager, policy: PermissionPolicy | None = None) -> None:
        self.workspace = workspace
        self.policy = policy or PermissionPolicy.default()
        self.path_tools = {"read_file", "write_file", "edit_file", "list_dir"}

    def __call__(self, event: HookEvent) -> HookResult:
        if event.event_type != "PreToolUse":
            return HookResult()

        try:
            decision = self.policy.decide_tool(event.tool_name)
            if decision.action == "deny":
                return self._to_hook_result(decision)

            if event.tool_name in self.path_tools:
                path = self._check_workspace_path(event.tool_name, event.arguments)
                path_decision = self.policy.decide_path(path)
                if path_decision.matched_rule is not None:
                    decision = path_decision
                if decision.action == "deny":
                    return self._to_hook_result(decision)

            if event.tool_name == "run_command":
                command = self._required_command(event.arguments)
                command_decision = self.policy.decide_command(command)
                if command_decision.matched_rule is not None:
                    decision = command_decision
                if decision.action == "deny":
                    return self._to_hook_result(decision)
        except Exception as exc:
            return HookResult(allowed=False, message=str(exc))

        return self._to_hook_result(decision)

    def _check_workspace_path(self, tool_name: str, arguments: dict[str, Any]) -> str:
        path = arguments.get("path", ".") if tool_name == "list_dir" else arguments.get("path")
        if not isinstance(path, str):
            raise ValueError("path must be a string.")
        self.workspace.resolve_path(path)
        return path

    def _required_command(self, arguments: dict[str, Any]) -> str:
        command = arguments.get("command")
        if not isinstance(command, str):
            raise ValueError("command must be a string.")
        return command

    def _to_hook_result(self, decision: PermissionDecision) -> HookResult:
        if decision.action == "deny":
            return HookResult(allowed=False, message=decision.reason)
        if decision.action == "ask":
            return HookResult(
                allowed=True,
                message=decision.reason,
                extra={"requires_confirmation": True},
            )
        return HookResult()

