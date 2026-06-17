from __future__ import annotations

from typing import Any

from my_agent.workspace.manager import WorkspaceManager


class FileTools:
    def __init__(self, workspace: WorkspaceManager) -> None:
        self.workspace = workspace

    def read_file(self, args: dict[str, Any]) -> dict[str, Any]:
        path = self._required_str(args, "path")
        content = self.workspace.read_text(path)
        return {"path": path, "content": content}

    def list_dir(self, args: dict[str, Any]) -> dict[str, Any]:
        path = args.get("path", ".")
        if not isinstance(path, str):
            raise ValueError("path must be a string.")
        entries = self.workspace.list_dir(path)
        return {"path": path, "entries": entries}

    def _required_str(self, args: dict[str, Any], key: str) -> str:
        value = args.get(key)
        if not isinstance(value, str):
            raise ValueError(f"{key} must be a string.")
        return value
