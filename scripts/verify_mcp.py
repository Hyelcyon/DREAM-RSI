from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.types import CallToolResult, TextContent


def _extract_text(result: CallToolResult) -> str:
    block = result.content[0]
    if isinstance(block, TextContent):
        return block.text
    raise TypeError(f"Expected TextContent block, got {type(block).__name__}")


async def run_verification() -> bool:
    project_root = Path(__file__).resolve().parents[1]
    python_exe = sys.executable

    print(f"[1/5] Initializing STDIO connection to Dream-RSI server at {project_root}...")
    server_params = StdioServerParameters(
        command=python_exe,
        args=["-m", "dream_rsi.mcp.server"],
        cwd=str(project_root),
        env={"PYTHONPATH": str(project_root / "src")},
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            print("[2/5] Performing MCP protocol handshake...")
            init_res = await session.initialize()
            print(f"       Handshake successful: protocol_version={init_res.protocol_version}")

            print("[3/5] Enumerating tools and resources...")
            tools = await session.list_tools()
            tool_names = [t.name for t in tools.tools]
            print(f"       Discovered {len(tool_names)} tools: {', '.join(tool_names)}")

            expected_tools = [
                "dream_history_list",
                "dream_history_get_tree",
                "dream_history_save_node",
                "dream_replay_run",
                "dream_replay_get_frontier",
                "dream_policy_compare",
                "dream_policy_plan_grid",
                "dream_status",
            ]
            for exp in expected_tools:
                assert exp in tool_names, f"Missing expected tool: {exp}"

            print("[4/5] Executing live tool invocation test sequence...")

            res_status = await session.call_tool("dream_status", {})
            status_data = json.loads(_extract_text(res_status))
            print(f"       -> dream_status: {status_data['status']} (trees={status_data['total_trees']})")
            assert status_data["status"] == "healthy"

            tree_id = "verification_test_tree"
            root_payload = {
                "node_id": "v_root",
                "parent_id": None,
                "branch_id": 0,
                "depth": 0,
                "observation": {
                    "branch": 0,
                    "attempt": 0,
                    "score": 0.25,
                    "evaluated": True,
                    "valid": True,
                    "fail_class": "ok",
                },
            }
            res_root = await session.call_tool(
                "dream_history_save_node",
                {"tree_id": tree_id, "node_data": root_payload},
            )
            root_data = json.loads(_extract_text(res_root))
            print(f"       -> dream_history_save_node (root): {root_data['status']}")
            assert root_data["status"] == "success"

            child_payload = {
                "node_id": "v_b1_c1",
                "parent_id": "v_root",
                "branch_id": 1,
                "depth": 1,
                "observation": {
                    "branch": 1,
                    "attempt": 0,
                    "score": 0.88,
                    "evaluated": True,
                    "valid": True,
                    "fail_class": "ok",
                },
            }
            res_child = await session.call_tool(
                "dream_history_save_node",
                {"tree_id": tree_id, "node_data": child_payload},
            )
            child_data = json.loads(_extract_text(res_child))
            print(f"       -> dream_history_save_node (child): {child_data['status']}")
            assert child_data["status"] == "success"

            res_list = await session.call_tool("dream_history_list", {})
            list_data = json.loads(_extract_text(res_list))
            print(f"       -> dream_history_list: total={list_data['total_trees']}")
            assert tree_id in list_data["tree_ids"]

            res_tree = await session.call_tool("dream_history_get_tree", {"tree_id": tree_id})
            tree_data = json.loads(_extract_text(res_tree))
            print(f"       -> dream_history_get_tree: nodes={len(tree_data['tree']['nodes'])}")
            assert len(tree_data["tree"]["nodes"]) == 2

            res_replay = await session.call_tool(
                "dream_replay_run",
                {"tree_id": tree_id, "beta": 0.5, "worker_cap": 5, "max_budget": 10},
            )
            replay_data = json.loads(_extract_text(res_replay))
            res_obj = replay_data["result"]
            print(f"       -> dream_replay_run: max_score={res_obj['max_score']}, replay_score={res_obj['replay_score']:.4f}")
            assert res_obj["max_score"] >= 0.88

            res_frontier = await session.call_tool(
                "dream_replay_get_frontier",
                {"beta_steps": 3, "worker_cap": 5, "max_budget": 10},
            )
            frontier_data = json.loads(_extract_text(res_frontier))
            print(f"       -> dream_replay_get_frontier: {len(frontier_data['frontier'])} points evaluated")
            assert len(frontier_data["frontier"]) == 3

            res_compare = await session.call_tool(
                "dream_policy_compare",
                {"candidate_beta": 0.9, "baseline_beta": 0.1, "worker_cap": 5, "max_budget": 10},
            )
            compare_data = json.loads(_extract_text(res_compare))
            comp_obj = compare_data["comparison"]
            print(f"       -> dream_policy_compare: delta={comp_obj['delta_replay_score']:.4f}")

            res_plan = await session.call_tool("dream_policy_plan_grid", {})
            plan_data = json.loads(_extract_text(res_plan))
            p = plan_data["plan"]
            print(f"       -> dream_policy_plan_grid: W={p['branch_count']}, R={p['refine_count']}")
            assert p["branch_count"] >= 1
            assert p["refine_count"] >= 0

            print("[5/5] All 8 tools verified successfully over live STDIO protocol!")
            return True


def main() -> None:
    success = asyncio.run(run_verification())
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
