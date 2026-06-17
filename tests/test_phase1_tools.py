from __future__ import annotations

import json

from my_agent.tools.command_tools import CommandTools
from my_agent.tools.file_tools import FileTools
from my_agent.tools.registry import build_tool_registry, execute_tools
from my_agent.workspace.manager import WorkspaceManager


def test_file_tools_read_and_list(tmp_path):
    (tmp_path / "sample.txt").write_text("hello", encoding="utf-8")
    workspace = WorkspaceManager(tmp_path)
    tools = FileTools(workspace)

    assert tools.read_file({"path": "sample.txt"})["content"] == "hello"
    assert "sample.txt" in tools.list_dir({"path": "."})["entries"]


def test_command_tool_blocks_dangerous_command(tmp_path):
    tools = CommandTools(WorkspaceManager(tmp_path))

    try:
        tools.run_command({"command": "shutdown /s"})
    except ValueError as exc:
        assert "Dangerous command blocked" in str(exc)
    else:
        raise AssertionError("dangerous command was not blocked")


def test_execute_tools_returns_tool_result(tmp_path):
    (tmp_path / "sample.txt").write_text("hello", encoding="utf-8")
    registry = build_tool_registry(WorkspaceManager(tmp_path))
    assistant_message = {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": json.dumps({"path": "sample.txt"}),
                },
            }
        ],
    }

    [result] = execute_tools(assistant_message, registry.tool_handlers)
    content = json.loads(result["content"])

    assert result["role"] == "tool"
    assert result["tool_call_id"] == "call_1"
    assert content["status"] == "ok"
    assert content["output"]["content"] == "hello"
