from __future__ import annotations

import json

from my_agent.hooks.base import HookManager
from my_agent.hooks.permission import PermissionHook
from my_agent.permission.confirmer import (
    AutoApproveConfirmationProvider,
    AutoDenyConfirmationProvider,
    ConfirmationProvider,
)
from my_agent.tools.registry import build_tool_registry, execute_tools
from my_agent.workspace.manager import WorkspaceManager


class RecordingConfirmationProvider(ConfirmationProvider):
    def __init__(self, allowed: bool) -> None:
        self.allowed = allowed
        self.calls: list[tuple[str, dict]] = []

    def confirm(self, tool_name: str, arguments: dict, reason: str | None = None) -> bool:
        self.calls.append((tool_name, arguments))
        return self.allowed


def _tool_message(name: str, arguments: dict[str, object]) -> dict:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(arguments),
                },
            }
        ],
    }


def _permission_manager(workspace: WorkspaceManager) -> HookManager:
    manager = HookManager()
    manager.register("PreToolUse", PermissionHook(workspace))
    return manager


def _execute_with_permission(
    tmp_path,
    name: str,
    arguments: dict[str, object],
    confirmation_provider: ConfirmationProvider | None,
) -> dict:
    workspace = WorkspaceManager(tmp_path)
    registry = build_tool_registry(workspace)
    [result] = execute_tools(
        _tool_message(name, arguments),
        registry.tool_handlers,
        hook_manager=_permission_manager(workspace),
        confirmation_provider=confirmation_provider,
    )
    return json.loads(result["content"])


def test_write_file_requires_confirmation_and_auto_approve_allows_execution(tmp_path):
    content = _execute_with_permission(
        tmp_path,
        "write_file",
        {"path": "notes.txt", "content": "hello"},
        AutoApproveConfirmationProvider(),
    )

    assert content["status"] == "ok"
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "hello"


def test_write_file_requires_confirmation_and_auto_deny_blocks_execution(tmp_path):
    content = _execute_with_permission(
        tmp_path,
        "write_file",
        {"path": "notes.txt", "content": "hello"},
        AutoDenyConfirmationProvider(),
    )

    assert content["status"] == "error"
    assert content["output"]["type"] == "PermissionError"
    assert "User denied permission" in content["output"]["error"]
    assert not (tmp_path / "notes.txt").exists()


def test_edit_file_requires_confirmation_and_auto_approve_allows_execution(tmp_path):
    (tmp_path / "notes.txt").write_text("hello phase 3", encoding="utf-8")

    content = _execute_with_permission(
        tmp_path,
        "edit_file",
        {"path": "notes.txt", "old_text": "phase 3", "new_text": "phase 4"},
        AutoApproveConfirmationProvider(),
    )

    assert content["status"] == "ok"
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "hello phase 4"


def test_run_command_requires_confirmation_and_auto_deny_blocks_execution(tmp_path):
    content = _execute_with_permission(
        tmp_path,
        "run_command",
        {"command": "echo hello"},
        AutoDenyConfirmationProvider(),
    )

    assert content["status"] == "error"
    assert content["output"]["type"] == "PermissionError"
    assert "User denied permission" in content["output"]["error"]


def test_read_file_does_not_require_confirmation(tmp_path):
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")

    content = _execute_with_permission(
        tmp_path,
        "read_file",
        {"path": "notes.txt"},
        AutoDenyConfirmationProvider(),
    )

    assert content["status"] == "ok"
    assert content["output"]["content"] == "hello"


def test_dangerous_command_is_blocked_before_confirmation(tmp_path):
    provider = RecordingConfirmationProvider(allowed=True)

    content = _execute_with_permission(
        tmp_path,
        "run_command",
        {"command": "rm -rf /"},
        provider,
    )

    assert content["status"] == "error"
    assert content["output"]["type"] == "PermissionError"
    assert "Dangerous command blocked" in content["output"]["error"]
    assert provider.calls == []


def test_confirmation_provider_none_blocks_requires_confirmation_tools(tmp_path):
    content = _execute_with_permission(
        tmp_path,
        "write_file",
        {"path": "notes.txt", "content": "hello"},
        None,
    )

    assert content["status"] == "error"
    assert content["output"]["type"] == "PermissionError"
    assert "Permission confirmation required" in content["output"]["error"]
    assert not (tmp_path / "notes.txt").exists()


def test_hook_manager_none_keeps_old_behavior(tmp_path):
    registry = build_tool_registry(WorkspaceManager(tmp_path))

    [result] = execute_tools(
        _tool_message("write_file", {"path": "notes.txt", "content": "hello"}),
        registry.tool_handlers,
        hook_manager=None,
        confirmation_provider=AutoDenyConfirmationProvider(),
    )
    content = json.loads(result["content"])

    assert content["status"] == "ok"
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "hello"
