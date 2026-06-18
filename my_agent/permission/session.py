from __future__ import annotations


class PermissionSession:
    def __init__(self) -> None:
        self.denied_file_writes: set[str] = set()

    def record_denied_file_write(self, path: str) -> None:
        self.denied_file_writes.add(self._normalize(path))

    def is_file_write_denied(self, path: str) -> bool:
        return self._normalize(path) in self.denied_file_writes

    def _normalize(self, path: str) -> str:
        normalized = path.replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        return normalized.lower()

