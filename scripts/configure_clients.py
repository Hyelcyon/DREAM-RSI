from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import sys
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        tomllib = None
from pathlib import Path

from dream_rsi.mcp.server import create_mcp_server


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_store_dir() -> Path:
    env_store = os.environ.get("DREAM_RSI_STORE_DIR")
    if env_store:
        return Path(env_store).resolve()
    return (get_repo_root() / "data" / "trees").resolve()


def get_claude_desktop_dir() -> Path:
    if sys.platform == "win32":
        return Path(os.path.expandvars(r"%APPDATA%\Claude"))
    if sys.platform == "darwin":
        return Path(os.path.expanduser("~/Library/Application Support/Claude"))
    config_home = os.environ.get("XDG_CONFIG_HOME")
    if config_home:
        return Path(config_home) / "Claude"
    return Path(os.path.expanduser("~/.config/Claude"))


async def configure_antigravity(target_dir: Path | None = None) -> bool:
    if target_dir is None:
        target_dir = Path(os.path.expanduser("~/.gemini/antigravity/mcp/dream-rsi"))
    target_dir.mkdir(parents=True, exist_ok=True)

    server = create_mcp_server()
    tools = await server.list_tools()

    existing_files = set(target_dir.glob("*.json"))
    generated_files: set[Path] = set()

    for tool in tools:
        filename = f"{tool.name}.json"
        file_path = target_dir / filename
        generated_files.add(file_path)

        schema = {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema or {"properties": {}, "type": "object"},
        }

        content = json.dumps(schema, indent=2, ensure_ascii=False)
        temp_path = file_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(temp_path, file_path)

    stale_files = existing_files - generated_files
    for stale in stale_files:
        stale.unlink()

    print(f"[Antigravity] Synced {len(tools)} tool schemas to {target_dir}")
    return True


def configure_codex(
    repo_root: Path,
    store_dir: Path,
    codex_home: Path | None = None,
) -> bool:
    if codex_home is None:
        codex_home = Path(os.path.expanduser("~/.codex"))
    if not codex_home.exists():
        print("[Codex] ~/.codex directory not found. Skipping.")
        return False

    config_path = codex_home / "config.toml"
    if not config_path.exists():
        original_text = ""
    else:
        with open(config_path, "r", encoding="utf-8") as f:
            original_text = f.read()

    backup_path = codex_home / "config.toml.bak"
    if config_path.exists() and not backup_path.exists():
        shutil.copy2(config_path, backup_path)

    root_str = repo_root.as_posix()
    store_str = store_dir.as_posix()

    dream_section = (
        f"[mcp_servers.dream-rsi]\n"
        f'command = "uv"\n'
        f'args = ["run", "--directory", "{root_str}", "dream-rsi"]\n'
        f"startup_timeout_sec = 60\n\n"
        f"[mcp_servers.dream-rsi.env]\n"
        f'DREAM_RSI_STORE_DIR = "{store_str}"\n'
    )

    pattern = re.compile(
        r"\[mcp_servers\.dream-rsi\][\s\S]*?(?=(\n\[(?!mcp_servers\.dream-rsi)|\Z))",
        re.MULTILINE,
    )

    if pattern.search(original_text):
        new_text = pattern.sub(dream_section.strip(), original_text)
    elif "[windows]" in original_text:
        new_text = original_text.replace("[windows]", f"{dream_section}\n[windows]")
    else:
        new_text = f"{original_text.rstrip()}\n\n{dream_section}"

    if tomllib is not None:
        try:
            tomllib.loads(new_text)
        except Exception as exc:
            print(f"[Codex] Validation error parsing updated TOML: {exc}", file=sys.stderr)
            return False

    temp_path = config_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    os.replace(temp_path, config_path)

    print(f"[Codex] Configured dream-rsi MCP server in {config_path}")
    return True


def configure_claude(
    repo_root: Path,
    store_dir: Path,
    desktop_dir: Path | None = None,
) -> bool:
    root_str = repo_root.as_posix()
    store_str = store_dir.as_posix()

    desktop_entry = {
        "command": "uv",
        "args": ["run", "--directory", root_str, "dream-rsi"],
        "env": {
            "DREAM_RSI_STORE_DIR": store_str,
        },
    }

    if desktop_dir is None:
        desktop_dir = get_claude_desktop_dir()

    desktop_config = desktop_dir / "claude_desktop_config.json"
    try:
        desktop_dir.mkdir(parents=True, exist_ok=True)
        if desktop_config.exists():
            with open(desktop_config, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}

        if not isinstance(data, dict):
            data = {}
        servers = data.setdefault("mcpServers", {})
        if isinstance(servers, dict):
            servers["dream-rsi"] = desktop_entry

        temp_desktop = desktop_config.with_suffix(".tmp")
        with open(temp_desktop, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(temp_desktop, desktop_config)
        print(f"[Claude Desktop] Configured dream-rsi MCP server in {desktop_config}")
    except Exception as exc:
        print(f"[Claude Desktop] Failed to configure: {exc}", file=sys.stderr)

    project_entry = {
        "command": "uv",
        "args": ["run", "dream-rsi"],
        "env": {
            "DREAM_RSI_STORE_DIR": "data/trees",
        },
    }

    project_mcp = repo_root / ".mcp.json"
    try:
        if project_mcp.exists():
            with open(project_mcp, "r", encoding="utf-8") as f:
                project_data = json.load(f)
        else:
            project_data = {}

        if not isinstance(project_data, dict):
            project_data = {}
        p_servers = project_data.setdefault("mcpServers", {})
        if isinstance(p_servers, dict):
            p_servers["dream-rsi"] = project_entry

        temp_project = project_mcp.with_suffix(".tmp")
        with open(temp_project, "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=2, ensure_ascii=False)
        os.replace(temp_project, project_mcp)
        print(f"[Claude Code] Configured project MCP manifest in {project_mcp}")
    except Exception as exc:
        print(f"[Claude Code] Failed to configure: {exc}", file=sys.stderr)

    return True


async def verify_connection(repo_root: Path) -> bool:
    from mcp.client.session import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    server_params = StdioServerParameters(
        command="uv",
        args=["run", "--directory", repo_root.as_posix(), "dream-rsi"],
    )

    print(f"[Verify] Testing client-style STDIO spawn via uv from {repo_root}...")
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            init_res = await session.initialize()
            tools_res = await session.list_tools()
            tool_names = [t.name for t in tools_res.tools]
            print(f"[Verify] Protocol {init_res.protocol_version} connected successfully.")
            print(f"[Verify] Discovered {len(tool_names)} tools: {', '.join(tool_names[:4])}...")
            assert len(tool_names) >= 11
            return True


async def main() -> None:
    parser = argparse.ArgumentParser(description="Configure Dream-RSI MCP across clients.")
    parser.add_argument("--antigravity", action="store_true", help="Sync Antigravity schemas")
    parser.add_argument("--codex", action="store_true", help="Configure OpenAI Codex")
    parser.add_argument("--claude", action="store_true", help="Configure Claude Desktop & Claude Code")
    parser.add_argument("--verify", action="store_true", help="Verify live client connection over STDIO")
    parser.add_argument("--all", action="store_true", help="Configure all clients and verify connection")
    args = parser.parse_args()

    run_all = args.all or (not args.antigravity and not args.codex and not args.claude and not args.verify)

    repo_root = get_repo_root()
    store_dir = get_store_dir()

    if run_all or args.antigravity:
        await configure_antigravity()

    if run_all or args.codex:
        configure_codex(repo_root, store_dir)

    if run_all or args.claude:
        configure_claude(repo_root, store_dir)

    if run_all or args.verify:
        await verify_connection(repo_root)


if __name__ == "__main__":
    asyncio.run(main())
