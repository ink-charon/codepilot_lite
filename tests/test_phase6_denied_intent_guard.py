from __future__ import annotations

import json

from my_agent.agent.prompt import build_system_prompt
from my_agent.hooks.base import HookManager
from my_agent.hooks.permission import PermissionHook
from my_agent.permission.command_analyzer import detect_command_file_writes
from my_agent.permission.confirmer import ConfirmationProvider
from my_agent.permission.session import PermissionSession
from my_agent.tools.registry import build_tool_registry, execute_tools
from my_agent.workspace.manager import WorkspaceManager


class SequenceConfirmationProvider(ConfirmationProvider):
    def __init__(self, responses: list[bool]) -> None:
        self.responses = responses
        self.calls = 0

    def confirm(self, tool_name: str, arguments: dict, reason: str | None = None) -> bool:
        response = self.responses[self.calls]
        self.calls += 1
        return response


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


def _execute(
    tmp_path,
    name: str,
    arguments: dict[str, object],
    provider: ConfirmationProvider,
    session: PermissionSession,
) -> dict:
    workspace = WorkspaceManager(tmp_path)
    registry = build_tool_registry(workspace)
    [result] = execute_tools(
        _tool_message(name, arguments),
        registry.tool_handlers,
        hook_manager=_permission_manager(workspace),
        confirmation_provider=provider,
        permission_session=session,
    )
    return json.loads(result["content"])


def test_denied_write_file_blocks_same_path_write_file_without_reconfirming(tmp_path):
    session = PermissionSession()
    provider = SequenceConfirmationProvider([False, True])

    first = _execute(
        tmp_path,
        "write_file",
        {"path": "demo_test.txt", "content": "first"},
        provider,
        session,
    )
    second = _execute(
        tmp_path,
        "write_file",
        {"path": "demo_test.txt", "content": "second"},
        provider,
        session,
    )

    assert first["status"] == "error"
    assert "不会继续尝试通过其他工具修改该文件" in first["output"]["error"]
    assert second["status"] == "error"
    assert "此前已被拒绝" in second["output"]["error"]
    assert provider.calls == 1
    assert not (tmp_path / "demo_test.txt").exists()


def test_denied_edit_file_blocks_run_command_echo_write_same_path(tmp_path):
    (tmp_path / "demo_test.txt").write_text("old", encoding="utf-8")
    session = PermissionSession()
    provider = SequenceConfirmationProvider([False, True])

    first = _execute(
        tmp_path,
        "edit_file",
        {"path": "demo_test.txt", "old_text": "old", "new_text": "new"},
        provider,
        session,
    )
    second = _execute(
        tmp_path,
        "run_command",
        {"command": "echo new > demo_test.txt"},
        provider,
        session,
    )

    assert first["status"] == "error"
    assert second["status"] == "error"
    assert "此前已被拒绝" in second["output"]["error"]
    assert provider.calls == 1
    assert (tmp_path / "demo_test.txt").read_text(encoding="utf-8") == "old"


def test_denied_write_file_blocks_python_open_write_same_path(tmp_path):
    session = PermissionSession()
    provider = SequenceConfirmationProvider([False, True])

    first = _execute(
        tmp_path,
        "write_file",
        {"path": "demo_test.txt", "content": "first"},
        provider,
        session,
    )
    second = _execute(
        tmp_path,
        "run_command",
        {"command": "python -c \"open('demo_test.txt', 'w').write('second')\""},
        provider,
        session,
    )

    assert first["status"] == "error"
    assert second["status"] == "error"
    assert "此前已被拒绝" in second["output"]["error"]
    assert provider.calls == 1
    assert not (tmp_path / "demo_test.txt").exists()


def test_run_command_echo_redirection_detects_write_target():
    assert detect_command_file_writes("echo hello > demo_test.txt") == ["demo_test.txt"]
    assert detect_command_file_writes("printf hello >> logs/out.txt") == ["logs/out.txt"]


def test_run_command_python_and_pathlib_writes_detect_write_targets():
    command = (
        "python -c \"open('a.txt', 'w').write('x'); "
        "pathlib.Path(\\\"b.txt\\\").write_text('y')\""
    )

    assert detect_command_file_writes(command) == ["a.txt", "b.txt"]


def test_run_command_write_outside_workspace_is_blocked(tmp_path):
    session = PermissionSession()
    provider = SequenceConfirmationProvider([True])

    content = _execute(
        tmp_path,
        "run_command",
        {"command": "echo escaped > ../outside.txt"},
        provider,
        session,
    )

    assert content["status"] == "error"
    assert "escapes workspace" in content["output"]["error"]
    assert provider.calls == 0


def test_hook_manager_none_keeps_old_behavior_with_denied_session(tmp_path):
    session = PermissionSession()
    session.record_denied_file_write("demo_test.txt")
    registry = build_tool_registry(WorkspaceManager(tmp_path))

    [result] = execute_tools(
        _tool_message("write_file", {"path": "demo_test.txt", "content": "allowed"}),
        registry.tool_handlers,
        hook_manager=None,
        confirmation_provider=SequenceConfirmationProvider([False]),
        permission_session=session,
    )
    content = json.loads(result["content"])

    assert content["status"] == "ok"
    assert (tmp_path / "demo_test.txt").read_text(encoding="utf-8") == "allowed"


def test_system_prompt_forbids_bypassing_denied_file_modifications(tmp_path):
    prompt = build_system_prompt(WorkspaceManager(tmp_path))

    assert "do not propose or attempt another way" in prompt
    assert "do not suggest or retry through another tool" in prompt
    assert "shell redirection" in prompt
    assert "Python one-liners" in prompt
    assert "explicitly authorize the write operation" in prompt


def test_denied_file_write_message_does_not_suggest_bypass(tmp_path):
    session = PermissionSession()
    provider = SequenceConfirmationProvider([False])

    content = _execute(
        tmp_path,
        "write_file",
        {"path": "demo_test.txt", "content": "first"},
        provider,
        session,
    )
    message = content["output"]["error"]

    assert "换一种方式" not in message
    assert "alternative way" not in message.lower()
    assert "不会继续尝试通过其他工具修改该文件" in message
    assert "重新发起请求并明确授权写入操作" in message
