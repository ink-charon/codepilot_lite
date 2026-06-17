from __future__ import annotations

import json

from my_agent.tools.file_tools import FileTools
from my_agent.tools.registry import build_tool_registry, execute_tools
from my_agent.workspace.manager import WorkspaceManager


def _execute_single_tool(tmp_path, name: str, arguments: dict[str, str]) -> dict:
    registry = build_tool_registry(WorkspaceManager(tmp_path))
    [result] = execute_tools(
        {
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
        },
        registry.tool_handlers,
    )
    return json.loads(result["content"])


def test_write_file_success(tmp_path):
    tools = FileTools(WorkspaceManager(tmp_path))

    result = tools.write_file({"path": "notes.txt", "content": "hello phase 2"})

    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "hello phase 2"
    assert result["path"] == "notes.txt"
    assert result["bytes"] == len("hello phase 2".encode("utf-8"))


def test_write_file_creates_parent_dir(tmp_path):
    tools = FileTools(WorkspaceManager(tmp_path))

    tools.write_file({"path": "docs/notes.txt", "content": "nested"})

    assert (tmp_path / "docs" / "notes.txt").read_text(encoding="utf-8") == "nested"


def test_write_file_blocks_parent_escape(tmp_path):
    content = _execute_single_tool(
        tmp_path,
        "write_file",
        {"path": "../outside.txt", "content": "blocked"},
    )

    assert content["status"] == "error"
    assert content["output"]["type"] == "WorkspaceError"
    assert "escapes workspace" in content["output"]["error"]
    assert not (tmp_path.parent / "outside.txt").exists()


def test_edit_file_success(tmp_path):
    (tmp_path / "notes.txt").write_text("hello phase 1", encoding="utf-8")
    tools = FileTools(WorkspaceManager(tmp_path))

    result = tools.edit_file(
        {"path": "notes.txt", "old_text": "phase 1", "new_text": "phase 2"}
    )

    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "hello phase 2"
    assert result["path"] == "notes.txt"


def test_edit_file_old_text_not_found(tmp_path):
    (tmp_path / "notes.txt").write_text("hello phase 1", encoding="utf-8")

    content = _execute_single_tool(
        tmp_path,
        "edit_file",
        {"path": "notes.txt", "old_text": "missing", "new_text": "phase 2"},
    )

    assert content["status"] == "error"
    assert content["output"]["type"] == "ValueError"
    assert "old_text not found" in content["output"]["error"]
    assert (tmp_path / "notes.txt").read_text(encoding="utf-8") == "hello phase 1"


def test_edit_file_blocks_parent_escape(tmp_path):
    content = _execute_single_tool(
        tmp_path,
        "edit_file",
        {"path": "../outside.txt", "old_text": "old", "new_text": "new"},
    )

    assert content["status"] == "error"
    assert content["output"]["type"] == "WorkspaceError"
    assert "escapes workspace" in content["output"]["error"]
