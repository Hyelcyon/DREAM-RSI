from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TypedDict


class McpServerSpec(TypedDict):
    command: str
    args: list[str]
    cwd: str
    env: dict[str, str]


class AgentMcpConfig(TypedDict):
    mcpServers: dict[str, McpServerSpec]


def get_default_mcp_config(project_root: Path | str | None = None) -> AgentMcpConfig:
    root = Path(project_root).resolve() if project_root else Path(__file__).resolve().parents[3]
    python_exe = sys.executable

    return {
        "mcpServers": {
            "dream-rsi": {
                "command": python_exe,
                "args": ["-m", "dream_rsi.mcp.server"],
                "cwd": str(root),
                "env": {
                    "PYTHONPATH": str(root / "src"),
                },
            }
        }
    }


def get_uvx_config(package_or_repo: str = "dream-rsi") -> AgentMcpConfig:
    args = ["--from", package_or_repo, "dream-rsi"] if package_or_repo != "dream-rsi" else ["dream-rsi"]
    return {
        "mcpServers": {
            "dream-rsi": {
                "command": "uvx",
                "args": args,
                "cwd": ".",
                "env": {},
            }
        }
    }


def export_claude_config(package_or_repo: str = "dream-rsi") -> str:
    return json.dumps(get_uvx_config(package_or_repo), indent=2, ensure_ascii=False)


def export_antigravity_config(package_or_repo: str = "dream-rsi") -> str:
    return json.dumps(get_uvx_config(package_or_repo), indent=2, ensure_ascii=False)


def export_codex_toml(package_or_repo: str = "dream-rsi") -> str:
    if package_or_repo != "dream-rsi":
        args_str = f'["--from", "{package_or_repo}", "dream-rsi"]'
    else:
        args_str = '["dream-rsi"]'

    return (
        '[mcp_servers.dream-rsi]\n'
        'command = "uvx"\n'
        f'args = {args_str}\n'
    )
