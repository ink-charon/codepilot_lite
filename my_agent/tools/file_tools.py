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

    def write_file(self, args: dict[str, Any]) -> dict[str, Any]:
        path = self._required_str(args, "path")
        content = self._required_str(args, "content")
        target = self.workspace.write_text(path, content)
        return {"path": path, "bytes": len(content.encode("utf-8")), "message": f"Wrote {target.name}"}

    def edit_file(self, args: dict[str, Any]) -> dict[str, Any]:
        path = self._required_str(args, "path")
        old_text = self._required_str(args, "old_text")
        new_text = self._required_str(args, "new_text")
        if old_text == "":
            raise ValueError("old_text must not be empty.")

        content = self.workspace.read_text(path)
        if old_text not in content:
            raise ValueError(f"old_text not found in file: {path}")

        updated = content.replace(old_text, new_text)
        self.workspace.write_text(path, updated)
        return {"path": path, "message": "Edited file"}

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
