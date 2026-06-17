from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> None:
    dotenv_path = Path(path)
    if not dotenv_path.exists():
        return
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass
class Settings:
    api_key: str
    base_url: str
    model: str
    max_turns: int = 12
    llm_retries: int = 2
    command_timeout_seconds: int = 30
    max_command_output_chars: int = 12000

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            api_key=os.getenv("LLM_API_KEY", ""),
            base_url=os.getenv("LLM_BASE_URL", "https://api.deepseek.com"),
            model=os.getenv("LLM_MODEL", "deepseek-v4-pro"),
            max_turns=int(os.getenv("AGENT_MAX_TURNS", "10")),
            llm_retries=int(os.getenv("LLM_RETRIES", "2")),
            command_timeout_seconds=int(os.getenv("COMMAND_TIMEOUT_SECONDS", "30")),
            max_command_output_chars=int(os.getenv("MAX_COMMAND_OUTPUT_CHARS", "12000")),
        )
