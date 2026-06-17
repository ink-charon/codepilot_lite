from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from my_agent.policy.policy import PermissionAction, PermissionPolicy


def load_permission_policy(path: str | None) -> PermissionPolicy:
    if path is None:
        return PermissionPolicy.default()

    policy_path = Path(path)
    if not policy_path.exists():
        return PermissionPolicy.default()

    try:
        data = _load_mapping(policy_path)
    except Exception:
        return PermissionPolicy.default()

    permissions = data.get("permissions", data)
    if not isinstance(permissions, dict):
        return PermissionPolicy.default()

    commands = permissions.get("commands")
    if not isinstance(commands, dict):
        commands = {}

    default_policy = PermissionPolicy.default()
    return PermissionPolicy(
        tools={**default_policy.tools, **_read_actions_dict(permissions.get("tools"))},
        paths={**default_policy.paths, **_read_actions_dict(permissions.get("paths"))},
        command_allow=_read_string_list(commands.get("allow")) or default_policy.command_allow,
        command_ask=_read_string_list(commands.get("ask")) or default_policy.command_ask,
        command_deny=_read_string_list(commands.get("deny")) or default_policy.command_deny,
    )


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml
    except ImportError:
        parsed = json.loads(text)
    else:
        parsed = yaml.safe_load(text)
    if not isinstance(parsed, dict):
        return {}
    return parsed


def _read_actions_dict(value: Any) -> dict[str, PermissionAction]:
    if not isinstance(value, dict):
        return {}
    actions: dict[str, PermissionAction] = {}
    for key, action in value.items():
        if isinstance(key, str) and action in {"allow", "deny", "ask"}:
            actions[key] = action
    return actions


def _read_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
