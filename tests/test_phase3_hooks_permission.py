from __future__ import annotations

import json

from my_agent.hooks.base import HookEvent, HookManager, HookResult
from my_agent.hooks.logging import LoggingHook
from my_agent.hooks.permission import PermissionHook
from my_agent.tools.registry import build_tool_registry, execute_tools
from my_agent.workspace.manager import WorkspaceManager


def _tool_message(name: str, arguments: dict[str, str]) -> dict:
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


def test_hook_manager_can_trigger_hook():
    manager = HookManager()
    seen: list[HookEvent] = []

    def record(event: HookEvent) -> HookResult:
        seen.append(event)
        return HookResult(extra={"seen": True})

    manager.register("PreToolUse", record)
    result = manager.trigger(HookEvent("PreToolUse", "read_file", {"path": "a.txt"}))

    assert result.allowed is True
    assert result.extra == {"seen": True}
    assert seen[0].tool_name == "read_file"


def test_hook_manager_can_block_operation():
    manager = HookManager()

    def block(_event: HookEvent) -> HookResult:
        return HookResult(allowed=False, message="blocked by test hook")

    manager.register("PreToolUse", block)
    result = manager.trigger(HookEvent("PreToolUse", "read_file", {"path": "a.txt"}))

    assert result.allowed is False
    assert result.message == "blocked by test hook"


def test_permission_hook_allows_workspace_read_file(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    hook = PermissionHook(WorkspaceManager(tmp_path))

    result = hook(HookEvent("PreToolUse", "read_file", {"path": "a.txt"}))

    assert result.allowed is True


def test_permission_hook_blocks_workspace_escape_read_file(tmp_path):
    hook = PermissionHook(WorkspaceManager(tmp_path))

    result = hook(HookEvent("PreToolUse", "read_file", {"path": "../outside.txt"}))

    assert result.allowed is False
    assert "escapes workspace" in result.message


def test_permission_hook_blocks_dangerous_rm_command(tmp_path):
    hook = PermissionHook(WorkspaceManager(tmp_path))

    result = hook(HookEvent("PreToolUse", "run_command", {"command": "rm -rf *"}))

    assert result.allowed is False
    assert "Dangerous command blocked" in result.message


def test_permission_hook_blocks_dangerous_powershell_command(tmp_path):
    hook = PermissionHook(WorkspaceManager(tmp_path))

    result = hook(
        HookEvent(
            "PreToolUse",
            "run_command",
            {"command": "Remove-Item -Recurse -Force C:\\"},
        )
    )

    assert result.allowed is False
    assert "Dangerous command blocked" in result.message


def test_permission_hook_marks_write_file_requires_confirmation(tmp_path):
    hook = PermissionHook(WorkspaceManager(tmp_path))

    result = hook(HookEvent("PreToolUse", "write_file", {"path": "a.txt"}))

    assert result.allowed is True
    assert result.extra == {"requires_confirmation": True}


def test_permission_hook_marks_edit_file_requires_confirmation(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    hook = PermissionHook(WorkspaceManager(tmp_path))

    result = hook(HookEvent("PreToolUse", "edit_file", {"path": "a.txt"}))

    assert result.allowed is True
    assert result.extra == {"requires_confirmation": True}


def test_execute_tools_can_be_blocked_by_pre_tool_use(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    registry = build_tool_registry(WorkspaceManager(tmp_path))
    manager = HookManager()

    def block(_event: HookEvent) -> HookResult:
        return HookResult(allowed=False, message="blocked before execution")

    manager.register("PreToolUse", block)

    [result] = execute_tools(
        _tool_message("read_file", {"path": "a.txt"}),
        registry.tool_handlers,
        hook_manager=manager,
    )
    content = json.loads(result["content"])

    assert content["status"] == "error"
    assert content["output"]["type"] == "PermissionError"
    assert "blocked before execution" in content["output"]["error"]


def test_execute_tools_triggers_post_tool_use(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    registry = build_tool_registry(WorkspaceManager(tmp_path))
    manager = HookManager()
    logging_hook = LoggingHook()
    manager.register("PostToolUse", logging_hook)

    [result] = execute_tools(
        _tool_message("read_file", {"path": "a.txt"}),
        registry.tool_handlers,
        hook_manager=manager,
    )
    content = json.loads(result["content"])

    assert content["status"] == "ok"
    assert len(logging_hook.events) == 1
    assert logging_hook.events[0].event_type == "PostToolUse"
    assert logging_hook.events[0].output["content"] == "hello"
