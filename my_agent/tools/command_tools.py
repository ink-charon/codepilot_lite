from __future__ import annotations

import subprocess
import re
from typing import Any

from my_agent.workspace.manager import WorkspaceManager


class CommandTools:
    def __init__(
        self,
        workspace: WorkspaceManager,
        default_timeout_seconds: int = 30,
        max_output_chars: int = 12000,
    ) -> None:
        self.workspace = workspace
        self.default_timeout_seconds = default_timeout_seconds
        self.max_output_chars = max_output_chars
        self.dangerous_patterns = [
            r"\brm\s+-rf\s+/",
            r"\bdel\s+/s\s+/q\s+[a-z]:\\",
            r"\bformat\b",
            r"\bshutdown\b",
            r"\breboot\b",
        ]

    def run_command(self, args: dict[str, Any]) -> dict[str, Any]:
        command = args.get("command")
        if not isinstance(command, str):
            raise ValueError("command must be a string.")
        self._ensure_safe_command(command)
        timeout = args.get("timeout_seconds", self.default_timeout_seconds)
        if not isinstance(timeout, int):
            raise ValueError("timeout_seconds must be an integer.")

        completed = subprocess.run(
            command,
            cwd=self.workspace.root,
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": self._truncate(completed.stdout),
            "stderr": self._truncate(completed.stderr),
        }

    def _ensure_safe_command(self, command: str) -> None:
        normalized = command.strip().lower()
        for pattern in self.dangerous_patterns:
            if re.search(pattern, normalized):
                raise ValueError(f"Dangerous command blocked: {command}")

    def _truncate(self, value: str) -> str:
        if len(value) <= self.max_output_chars:
            return value
        return value[: self.max_output_chars] + "\n...[truncated]"
