from __future__ import annotations

from pathlib import Path


class WorkspaceError(RuntimeError):
    pass


class WorkspaceManager:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.exists():
            raise FileNotFoundError(f"Workspace does not exist: {self.root}")
        if not self.root.is_dir():
            raise NotADirectoryError(f"Workspace is not a directory: {self.root}")

    def resolve_path(self, path: str | Path) -> Path:
        raw = Path(path)
        target = raw if raw.is_absolute() else self.root / raw
        resolved = target.resolve()
        self.ensure_inside_workspace(resolved)
        return resolved

    def ensure_inside_workspace(self, path: Path) -> None:
        try:
            path.resolve().relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceError(f"Path escapes workspace: {path}") from exc

    def read_text(self, path: str | Path) -> str:
        target = self.resolve_path(path)
        if not target.exists():
            raise FileNotFoundError(f"File does not exist: {path}")
        if not target.is_file():
            raise IsADirectoryError(f"Path is not a file: {path}")
        return target.read_text(encoding="utf-8")

    def list_dir(self, path: str | Path = ".") -> list[str]:
        target = self.resolve_path(path)
        if not target.exists():
            raise FileNotFoundError(f"Directory does not exist: {path}")
        if not target.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {path}")
        entries = []
        for child in sorted(target.iterdir(), key=lambda item: item.name.lower()):
            suffix = "/" if child.is_dir() else ""
            entries.append(f"{child.name}{suffix}")
        return entries
