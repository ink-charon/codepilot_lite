from __future__ import annotations

from typing import Any, Literal


Message = dict[str, Any]


ToolStatus = Literal["ok", "error"]


def has_tool_use(message: Message) -> bool:
    return bool(message.get("tool_calls"))


def extract_text(message: Message) -> str:
    content = message.get("content")
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "\n".join(parts)
    return ""
