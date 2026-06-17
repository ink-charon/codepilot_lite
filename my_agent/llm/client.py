from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from my_agent.agent.messages import Message
from my_agent.config.settings import Settings


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def chat(self, messages: list[Message], tools: list[dict[str, Any]]) -> Message:
        return self._complete_openai_compatible(messages, tools)

    def _complete_openai_compatible(
        self, messages: list[Message], tools: list[dict[str, Any]]
    ) -> Message:
        if not self.settings.api_key:
            raise RuntimeError("LLM_API_KEY is required. Create .env from .env.example.")

        payload = {
            "model": self.settings.model,
            "messages": messages,
            "tools": tools,
        }
        data = json.dumps(payload).encode("utf-8")
        url = self.settings.base_url.rstrip("/") + "/chat/completions"
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {self.settings.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        last_error: Exception | None = None
        for attempt in range(self.settings.llm_retries + 1):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    body = json.loads(response.read().decode("utf-8"))
                return body["choices"][0]["message"]
            except urllib.error.HTTPError as exc:
                last_error = RuntimeError(self._format_http_error(exc))
                if attempt < self.settings.llm_retries:
                    time.sleep(1 + attempt)
            except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
                last_error = exc
                if attempt < self.settings.llm_retries:
                    time.sleep(1 + attempt)
        raise RuntimeError(f"LLM API call failed: {last_error}")

    def _format_http_error(self, exc: urllib.error.HTTPError) -> str:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return f"HTTP {exc.code} {exc.reason}: {body}"
