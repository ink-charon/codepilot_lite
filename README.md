# CodePilot Lite

CodePilot Lite is a lightweight local Coding Agent harness inspired by the `s20_comprehensive` architecture from `learn-claude-code`.

The project focuses on building a minimal but extensible Agent loop:

```python
while True:
    response = LLM(messages, tools)

    if not has_tool_use(response):
        return response

    tool_results = execute_tools(response)
    messages.append(tool_results)
```

In Phase 1, CodePilot Lite supports:

* Workspace-safe file reading
* Directory listing
* Safe command execution
* Tool registry and tool dispatch
* Tool result feedback to the LLM
* Basic pytest coverage

The goal is not to copy a full Claude Code implementation, but to gradually build a clear, testable, and extensible local Coding Agent from a minimal working loop.
