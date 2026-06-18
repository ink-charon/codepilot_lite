from __future__ import annotations

from typing import Any

from my_agent.hooks.base import HookEvent, HookResult
from my_agent.permission.command_analyzer import detect_command_file_writes
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
            extra: dict[str, Any] = {}
            include_file_write_paths = bool(event.extra.get("include_file_write_paths"))
            if decision.action == "deny":
                return self._to_hook_result(decision)

            if event.tool_name in self.path_tools:
                path = self._check_workspace_path(event.tool_name, event.arguments)
                path_decision = self.policy.decide_path(path)
                if path_decision.matched_rule is not None:
                    decision = path_decision
                if decision.action == "deny":
                    return self._to_hook_result(decision)
                if include_file_write_paths and event.tool_name in {"write_file", "edit_file"}:
                    extra["file_write_paths"] = [str(self.workspace.resolve_path(path))]

            if event.tool_name == "run_command":
                command = self._required_command(event.arguments)
                command_decision = self.policy.decide_command(command)
                if command_decision.matched_rule is not None:
                    decision = command_decision
                if decision.action == "deny":
                    return self._to_hook_result(decision)
                write_targets = self._check_command_file_writes(command)
                if include_file_write_paths and write_targets:
                    extra["file_write_paths"] = [resolved for _raw, resolved in write_targets]
                for raw_path, _resolved in write_targets:
                    path_decision = self.policy.decide_path(raw_path)
                    if path_decision.matched_rule is not None:
                        decision = path_decision
                    if decision.action == "deny":
                        return self._to_hook_result(decision)
        except Exception as exc:
            return HookResult(allowed=False, message=str(exc))

        return self._to_hook_result(decision, extra=extra)

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

    def _check_command_file_writes(self, command: str) -> list[tuple[str, str]]:
        paths: list[tuple[str, str]] = []
        for path in detect_command_file_writes(command):
            paths.append((path, str(self.workspace.resolve_path(path))))
        return paths

    def _to_hook_result(
        self,
        decision: PermissionDecision,
        extra: dict[str, Any] | None = None,
    ) -> HookResult:
        result_extra = extra or {}
        if decision.action == "deny":
            return HookResult(allowed=False, message=decision.reason, extra=result_extra)
        if decision.action == "ask":
            result_extra = {**result_extra, "requires_confirmation": True}
            return HookResult(
                allowed=True,
                message=decision.reason,
                extra=result_extra,
            )
        return HookResult(extra=result_extra)

