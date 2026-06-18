from __future__ import annotations

import re


def detect_command_file_writes(command: str) -> list[str]:
    command = command.replace('\\"', '"').replace("\\'", "'")
    paths: list[str] = []
    paths.extend(_detect_redirection_writes(command))
    paths.extend(_detect_python_writes(command))
    paths.extend(_detect_powershell_writes(command))
    return _dedupe(paths)


def _detect_redirection_writes(command: str) -> list[str]:
    paths: list[str] = []
    pattern = re.compile(
        r"(?:^|[;&|]\s*)(?:echo|printf|type\s+nul)\b.*?(?:>>|>)\s*(?P<path>\"[^\"]+\"|'[^']+'|[^\s&|;]+)",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(command):
        paths.append(_clean_path(match.group("path")))
    return paths


def _detect_python_writes(command: str) -> list[str]:
    paths: list[str] = []
    open_pattern = re.compile(
        r"open\(\s*(?P<quote>['\"])(?P<path>.+?)(?P=quote)\s*,\s*['\"](?P<mode>[waxt])",
        flags=re.IGNORECASE,
    )
    for match in open_pattern.finditer(command):
        if match.group("mode").lower() in {"w", "a", "x"}:
            paths.append(match.group("path"))

    path_write_pattern = re.compile(
        r"(?:pathlib\.)?Path\(\s*(?P<quote>['\"])(?P<path>.+?)(?P=quote)\s*\)\.write_text\(",
        flags=re.IGNORECASE,
    )
    for match in path_write_pattern.finditer(command):
        paths.append(match.group("path"))
    return paths


def _detect_powershell_writes(command: str) -> list[str]:
    paths: list[str] = []
    pattern = re.compile(
        r"\b(?:Set-Content|Out-File)\b\s+(?:(?:-Path|-LiteralPath|-FilePath)\s+)?(?P<path>\"[^\"]+\"|'[^']+'|[^\s]+)",
        flags=re.IGNORECASE,
    )
    for match in pattern.finditer(command):
        path = _clean_path(match.group("path"))
        if not path.startswith("-"):
            paths.append(path)
    return paths


def _clean_path(path: str) -> str:
    value = path.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value


def _dedupe(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for path in paths:
        normalized = path.replace("\\", "/").lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(path)
    return result
