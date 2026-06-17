from __future__ import annotations

from dataclasses import dataclass
import json
import traceback
from typing import Any, Callable

from my_agent.hooks.base import HookEvent, HookManager
from my_agent.permission.confirmer import ConfirmationProvider
from my_agent.tools.command_tools import CommandTools
from my_agent.tools.file_tools import FileTools
from my_agent.workspace.manager import WorkspaceManager

ToolHandler = Callable[[dict[str, Any]], Any]


@dataclass
class ToolRegistry:
    tool_definitions: list[dict[str, Any]]
    tool_handlers: dict[str, ToolHandler]

    def get_handler(self, name: str) -> ToolHandler:
        if name not in self.tool_handlers:
            raise KeyError(f"Unknown tool: {name}")
        return self.tool_handlers[name]


def build_tool_registry(workspace: WorkspaceManager) -> ToolRegistry:
    file_tools = FileTools(workspace)
    command_tools = CommandTools(workspace)

    tool_definitions = [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a text file inside the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List directory entries inside the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write a complete text file inside the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "Replace text in a file inside the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "old_text": {"type": "string"},
                        "new_text": {"type": "string"},
                    },
                    "required": ["path", "old_text", "new_text"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Run a shell command in the workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string"},
                        "timeout_seconds": {"type": "integer"},
                    },
                    "required": ["command"],
                },
            },
        },
    ]
    tool_handlers: dict[str, ToolHandler] = {
        "read_file": file_tools.read_file,
        "list_dir": file_tools.list_dir,
        "write_file": file_tools.write_file,
        "edit_file": file_tools.edit_file,
        "run_command": command_tools.run_command,
    }
    return ToolRegistry(tool_definitions=tool_definitions, tool_handlers=tool_handlers)


def execute_tools(
    assistant_message: dict[str, Any],
    tool_handlers: dict[str, ToolHandler],
    hook_manager: HookManager | None = None,
    confirmation_provider: ConfirmationProvider | None = None,
) -> list[dict[str, Any]]:
    tool_results: list[dict[str, Any]] = []
    for tool_call in assistant_message.get("tool_calls") or []:
        tool_call_id = tool_call.get("id", "")
        function = tool_call.get("function", {})
        name = function.get("name", "")
        arguments = _parse_arguments(function.get("arguments", {}))

        try:
            if hook_manager is not None:
                pre_result = hook_manager.trigger(
                    HookEvent(
                        event_type="PreToolUse",
                        tool_name=name,
                        arguments=arguments,
                        tool_call_id=tool_call_id,
                    )
                )
                if not pre_result.allowed:
                    raise PermissionError(pre_result.message)
                if pre_result.extra.get("requires_confirmation"):
                    if confirmation_provider is None:
                        raise PermissionError("Permission confirmation required.")
                    confirmed = confirmation_provider.confirm(
                        name,
                        arguments,
                        pre_result.message or None,
                    )
                    if not confirmed:
                        raise PermissionError("User denied permission.")

            if name not in tool_handlers:
                raise KeyError(f"Unknown tool: {name}")
            output = tool_handlers[name](arguments)
            status = "ok"

            if hook_manager is not None:
                post_result = hook_manager.trigger(
                    HookEvent(
                        event_type="PostToolUse",
                        tool_name=name,
                        arguments=arguments,
                        tool_call_id=tool_call_id,
                        status=status,
                        output=output,
                    )
                )
                if not post_result.allowed:
                    raise PermissionError(post_result.message)
        except Exception as exc:
            status = "error"
            output = _format_exception(exc)

        tool_results.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(
                    {"status": status, "tool": name, "output": output},
                    ensure_ascii=False,
                ),
            }
        )
    return tool_results


def _format_exception(exc: Exception) -> dict[str, Any]:
    return {
        "error": str(exc),
        "type": type(exc).__name__,
        "traceback": "".join(traceback.format_exception_only(type(exc), exc)).strip(),
    }


def _parse_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except json.JSONDecodeError:
            return {"raw": arguments}
        if isinstance(parsed, dict):
            return parsed
    return {}
