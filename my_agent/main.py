from __future__ import annotations

import argparse

from my_agent.agent.loop import Agent
from my_agent.config.settings import Settings
from my_agent.llm.client import LLMClient
from my_agent.tools.registry import build_tool_registry
from my_agent.workspace.manager import WorkspaceManager


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local Coding Agent.")
    parser.add_argument("--workspace", default=".", help="Workspace root.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = Settings.from_env()
    workspace = WorkspaceManager(args.workspace)
    registry = build_tool_registry(workspace)
    llm = LLMClient(settings)

    agent = Agent(
        settings=settings,
        workspace=workspace,
        registry=registry,
        llm=llm,
    )
    print(f"Workspace: {workspace.root}")
    print("Enter a task. Type 'exit' or 'quit' to stop.")
    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_input.lower() in {"exit", "quit"}:
            break
        if not user_input:
            continue
        print(agent.run(user_input))


if __name__ == "__main__":
    main()
