from __future__ import annotations

import json
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

import pytest

from scripts.configure_clients import configure_claude, configure_codex, get_claude_desktop_dir


def test_configure_codex_with_empty_and_existing_toml(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    codex_home.mkdir(parents=True)
    config_file = codex_home / "config.toml"

    initial_toml = """model = "gpt-6-astra"

[windows]
sandbox = "elevated"
"""
    config_file.write_text(initial_toml, encoding="utf-8")

    repo_root = tmp_path / "repo"
    store_dir = repo_root / "data" / "trees"

    success = configure_codex(repo_root, store_dir, codex_home=codex_home)
    assert success is True

    parsed = tomllib.loads(config_file.read_text(encoding="utf-8"))
    mcp = parsed["mcp_servers"]["dream-rsi"]
    assert mcp["command"] == "uv"
    assert mcp["args"] == ["run", "--directory", repo_root.as_posix(), "dream-rsi"]
    assert mcp["startup_timeout_sec"] == 60
    assert mcp["env"]["DREAM_RSI_STORE_DIR"] == store_dir.as_posix()
    assert parsed["model"] == "gpt-6-astra"
    assert parsed["windows"]["sandbox"] == "elevated"

    # Verify idempotence / update
    updated_store = repo_root / "other" / "trees"
    success_update = configure_codex(repo_root, updated_store, codex_home=codex_home)
    assert success_update is True

    parsed_updated = tomllib.loads(config_file.read_text(encoding="utf-8"))
    assert parsed_updated["mcp_servers"]["dream-rsi"]["env"]["DREAM_RSI_STORE_DIR"] == updated_store.as_posix()


def test_configure_claude_json_generation(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True)
    store_dir = repo_root / "data" / "trees"

    fake_appdata = tmp_path / "AppData" / "Roaming" / "Claude"
    fake_appdata.mkdir(parents=True)

    success = configure_claude(repo_root, store_dir, desktop_dir=fake_appdata)
    assert success is True

    desktop_file = fake_appdata / "claude_desktop_config.json"
    assert desktop_file.exists()
    desktop_data = json.loads(desktop_file.read_text(encoding="utf-8"))
    entry = desktop_data["mcpServers"]["dream-rsi"]
    assert entry["command"] == "uv"
    assert entry["args"] == ["run", "--directory", repo_root.as_posix(), "dream-rsi"]
    assert entry["env"]["DREAM_RSI_STORE_DIR"] == store_dir.as_posix()

    project_file = repo_root / ".mcp.json"
    assert project_file.exists()
    project_data = json.loads(project_file.read_text(encoding="utf-8"))
    assert project_data["mcpServers"]["dream-rsi"]["command"] == "uv"
    assert project_data["mcpServers"]["dream-rsi"]["args"] == ["run", "dream-rsi"]
    assert project_data["mcpServers"]["dream-rsi"]["env"]["DREAM_RSI_STORE_DIR"] == "data/trees"


def test_get_claude_desktop_dir() -> None:
    desktop_dir = get_claude_desktop_dir()
    assert isinstance(desktop_dir, Path)
    assert len(desktop_dir.parts) > 0
