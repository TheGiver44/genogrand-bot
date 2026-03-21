import importlib.util
import os
from pathlib import Path


def _load_script_module():
    script_path = Path("scripts/send_changelog_test_tweet.py")
    spec = importlib.util.spec_from_file_location("send_changelog_test_tweet", script_path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_resolve_project_hint_defaults_to_boona(monkeypatch):
    monkeypatch.delenv("CHANGELOG_SLUG", raising=False)
    module = _load_script_module()
    assert module._resolve_project_hint() == "changelog:boona"


def test_resolve_project_hint_uses_env_slug(monkeypatch):
    monkeypatch.setenv("CHANGELOG_SLUG", "genogrand_bot")
    module = _load_script_module()
    assert module._resolve_project_hint() == "changelog:genogrand_bot"
