from __future__ import annotations

from dataclasses import dataclass

from my_agent.agent.messages import Message, extract_text, has_tool_use
from my_agent.agent.prompt import build_system_prompt
from my_agent.config.settings import Settings
from my_agent.hooks.base import HookManager
from my_agent.llm.client import LLMClient
from my_agent.permission.confirmer import ConfirmationProvider
from my_agent.permission.session import PermissionSession
from my_agent.tools.registry import ToolRegistry, execute_tools
from my_agent.workspace.manager import WorkspaceManager


@dataclass
class Agent:
    settings: Settings
    workspace: WorkspaceManager
    registry: ToolRegistry
    llm: LLMClient
    hook_manager: HookManager | None = None
    confirmation_provider: ConfirmationProvider | None = None

    def run(self, user_prompt: str) -> str:
        permission_session = PermissionSession()
        messages: list[Message] = [
            {"role": "system", "content": build_system_prompt(self.workspace)},
            {"role": "user", "content": user_prompt},
        ]

        for _ in range(self.settings.max_turns):
            assistant_message = self.llm.chat(messages, self.registry.tool_definitions)
            messages.append(assistant_message)

            if not has_tool_use(assistant_message):
                return extract_text(assistant_message)

            tool_result_messages = execute_tools(
                assistant_message,
                self.registry.tool_handlers,
                hook_manager=self.hook_manager,
                confirmation_provider=self.confirmation_provider,
                permission_session=permission_session,
            )
            messages.extend(tool_result_messages)

        return "Reached the maximum loop count. The task may be incomplete."
