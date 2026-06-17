# my_agent

Phase 1 minimal local Coding Agent.

It implements one loop:

```text
user input -> LLM -> tool_calls -> execute tools -> tool_result messages -> LLM
```

Implemented tools:

- `read_file`
- `list_dir`
- `run_command`

Not implemented in Phase 1:

- `write_file`
- `edit_file`
- todo
- hooks
- permissions plugin system
- MCP
- multi-agent
- cron
- background tasks
- memory
- skills

## Configure

Copy `.env.example` to `.env`, then set your model provider values:

```env
LLM_API_KEY=your_deepseek_api_key_here
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-pro
AGENT_MAX_TURNS=10
COMMAND_TIMEOUT_SECONDS=30
MAX_COMMAND_OUTPUT_CHARS=12000
```

## Run

```powershell
python -m my_agent.main --workspace .
```

Then enter a task:

```text
读取 README.md 并总结
```

Type `exit` or `quit` to stop.

## Test

```powershell
python -m pytest
```
