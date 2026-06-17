from __future__ import annotations

import pytest

from my_agent.workspace.manager import WorkspaceError, WorkspaceManager


def test_resolve_inside_workspace(tmp_path):
    workspace = WorkspaceManager(tmp_path)
    assert workspace.resolve_path("a.txt") == tmp_path / "a.txt"


def test_resolve_blocks_parent_escape(tmp_path):
    workspace = WorkspaceManager(tmp_path)
    with pytest.raises(WorkspaceError):
        workspace.resolve_path("../outside.txt")


def test_write_and_read_text(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    workspace = WorkspaceManager(tmp_path)
    assert workspace.read_text("a.txt") == "hello"


def test_list_dir(tmp_path):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "pkg").mkdir()
    workspace = WorkspaceManager(tmp_path)
    assert workspace.list_dir(".") == ["a.txt", "pkg/"]
