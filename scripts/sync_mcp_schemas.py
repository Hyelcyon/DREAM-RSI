import asyncio
import json
import os
import sys
from pathlib import Path
from dream_rsi.mcp.server import create_mcp_server

async def sync_antigravity_schemas() -> None:
    # Target directory for Antigravity's lazy tool schemas
    target_dir = Path(os.path.expanduser("~/.gemini/antigravity/mcp/dream-rsi"))
    target_dir.mkdir(parents=True, exist_ok=True)

    server = create_mcp_server()
    tools = await server.list_tools()

    existing_files = set(target_dir.glob("*.json"))
    generated_files = set()

    print(f"Syncing {len(tools)} MCP tool schemas to {target_dir}...")

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
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  [+] Updated {filename}")

    # Remove stale tool JSONs if any were deleted from code
    stale_files = existing_files - generated_files
    for stale in stale_files:
        stale.unlink()
        print(f"  [-] Removed stale tool schema: {stale.name}")

    print("MCP schema sync completed successfully.")

if __name__ == "__main__":
    asyncio.run(sync_antigravity_schemas())
