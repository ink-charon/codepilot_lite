from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatch
import re
from typing import Literal

PermissionAction = Literal["allow", "deny", "ask"]


@dataclass
class PermissionDecision:
    action: PermissionAction
    reason: str = ""
    matched_rule: str | None = None


@dataclass
class PermissionPolicy:
    tools: dict[str, PermissionAction] = field(default_factory=dict)
    paths: dict[str, PermissionAction] = field(default_factory=dict)
    command_allow: list[str] = field(default_factory=list)
    command_ask: list[str] = field(default_factory=list)
    command_deny: list[str] = field(default_factory=list)

    dangerous_command_patterns: tuple[str, ...] = (
        r"\brm\s+-rf\s+/",
        r"\brm\s+-rf\s+\*",
        r"\bdel\s+/s\s+/q\s+c:\\",
        r"\bformat\b",
        r"\bshutdown\b",
        r"\breboot\b",
        r"\bremove-item\b.*\s-recurse\b.*\s-force\b.*c:\\",
        r"\bstop-computer\b",
        r"\brestart-computer\b",
    )

    @classmethod
    def default(cls) -> "PermissionPolicy":
        return cls(
            tools={
                "read_file": "allow",
                "list_dir": "allow",
                "write_file": "ask",
                "edit_file": "ask",
                "run_command": "ask",
            },
            paths={
                ".env": "deny",
                ".env.*": "deny",
                "secrets/*": "deny",
                "*.key": "deny",
                "*.pem": "deny",
                "README.md": "ask",
            },
            command_allow=[
                "python --version",
                "python -m pytest",
                "git status",
            ],
            command_ask=[
                "git add",
                "git commit",
                "git push",
                "pip install",
            ],
            command_deny=[
                "rm -rf /",
                "rm -rf *",
                "del /s /q C:\\",
                "format",
                "shutdown",
                "reboot",
                "Remove-Item -Recurse -Force C:\\",
                "Stop-Computer",
                "Restart-Computer",
            ],
        )

    def decide_tool(self, tool_name: str) -> PermissionDecision:
        action = self.tools.get(tool_name, "allow")
        matched_rule = f"tools.{tool_name}" if tool_name in self.tools else None
        return PermissionDecision(
            action=action,
            reason=f"Tool rule {tool_name}: {action}.",
            matched_rule=matched_rule,
        )

    def decide_path(self, path: str) -> PermissionDecision:
        normalized = self._normalize_path(path)
        for pattern, action in self.paths.items():
            if fnmatch(normalized, self._normalize_path(pattern)):
                return PermissionDecision(
                    action=action,
                    reason=f"Path rule {pattern}: {action}.",
                    matched_rule=pattern,
                )
        return PermissionDecision(action="allow", reason="No path rule matched.")

    def decide_command(self, command: str) -> PermissionDecision:
        if self._matches_dangerous_command(command):
            return PermissionDecision(
                action="deny",
                reason=f"Dangerous command blocked by permission policy: {command}",
                matched_rule="dangerous_command",
            )

        for rule in self.command_deny:
            if self._matches_command_rule(command, rule):
                return PermissionDecision(
                    action="deny",
                    reason=f"Command deny rule {rule}: deny.",
                    matched_rule=rule,
                )
        for rule in self.command_allow:
            if self._matches_command_rule(command, rule):
                return PermissionDecision(
                    action="allow",
                    reason=f"Command allow rule {rule}: allow.",
                    matched_rule=rule,
                )
        for rule in self.command_ask:
            if self._matches_command_rule(command, rule):
                return PermissionDecision(
                    action="ask",
                    reason=f"Command ask rule {rule}: ask.",
                    matched_rule=rule,
                )
        return PermissionDecision(action="allow", reason="No command rule matched.")

    def _matches_dangerous_command(self, command: str) -> bool:
        for pattern in self.dangerous_command_patterns:
            if re.search(pattern, command, flags=re.IGNORECASE):
                return True
        return False

    def _matches_command_rule(self, command: str, rule: str) -> bool:
        normalized_command = command.strip().lower()
        normalized_rule = rule.strip().lower()
        return (
            normalized_command == normalized_rule
            or normalized_command.startswith(normalized_rule + " ")
            or fnmatch(normalized_command, normalized_rule)
        )

    def _normalize_path(self, path: str) -> str:
        normalized = path.replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        return normalized
