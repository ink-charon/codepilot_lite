from __future__ import annotations

from my_agent.hooks.base import HookEvent
from my_agent.hooks.permission import PermissionHook
from my_agent.policy.loader import load_permission_policy
from my_agent.policy.policy import PermissionPolicy
from my_agent.workspace.manager import WorkspaceManager


def test_default_policy_read_file_allow():
    decision = PermissionPolicy.default().decide_tool("read_file")

    assert decision.action == "allow"


def test_default_policy_write_file_ask():
    decision = PermissionPolicy.default().decide_tool("write_file")

    assert decision.action == "ask"


def test_default_policy_run_command_ask():
    decision = PermissionPolicy.default().decide_tool("run_command")

    assert decision.action == "ask"


def test_default_policy_dangerous_command_deny():
    decision = PermissionPolicy.default().decide_command("shutdown /s")

    assert decision.action == "deny"
    assert "Dangerous command blocked" in decision.reason


def test_path_env_deny():
    decision = PermissionPolicy.default().decide_path(".env")

    assert decision.action == "deny"
    assert decision.matched_rule == ".env"


def test_path_secrets_token_deny():
    decision = PermissionPolicy.default().decide_path("secrets/token.txt")

    assert decision.action == "deny"
    assert decision.matched_rule == "secrets/*"


def test_path_readme_ask():
    decision = PermissionPolicy.default().decide_path("README.md")

    assert decision.action == "ask"
    assert decision.matched_rule == "README.md"


def test_command_python_version_allow():
    decision = PermissionPolicy.default().decide_command("python --version")

    assert decision.action == "allow"
    assert decision.matched_rule == "python --version"


def test_command_git_push_ask():
    decision = PermissionPolicy.default().decide_command("git push origin main")

    assert decision.action == "ask"
    assert decision.matched_rule == "git push"


def test_command_rm_rf_root_deny():
    decision = PermissionPolicy.default().decide_command("rm -rf /")

    assert decision.action == "deny"


def test_permission_hook_uses_policy_requires_confirmation(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    hook = PermissionHook(WorkspaceManager(tmp_path), PermissionPolicy.default())

    result = hook(HookEvent("PreToolUse", "read_file", {"path": "README.md"}))

    assert result.allowed is True
    assert result.extra == {"requires_confirmation": True}
    assert "Path rule README.md" in result.message


def test_missing_policy_file_falls_back_to_default(tmp_path):
    policy = load_permission_policy(str(tmp_path / "missing.yaml"))

    assert policy.decide_tool("write_file").action == "ask"
    assert policy.decide_path(".env").action == "deny"
