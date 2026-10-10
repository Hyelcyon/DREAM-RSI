import json
from pathlib import Path

import pytest
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, InputRequiredResult, TextContent

from dream_rsi.mcp.server import create_mcp_server


def _extract_text(result: object) -> str:
    if not isinstance(result, CallToolResult):
        raise TypeError(f"Expected CallToolResult, got {type(result).__name__}")
    block = result.content[0]
    if isinstance(block, TextContent):
        return block.text
    raise TypeError(f"Expected TextContent, got {type(block).__name__}")


@pytest.fixture
def mcp_server(tmp_path: Path) -> MCPServer:
    return create_mcp_server(store_dir=tmp_path, server_name="test-dream-rsi")


@pytest.mark.asyncio
async def test_mcp_tools_and_resources_lifecycle(mcp_server: MCPServer) -> None:
    tools = await mcp_server.list_tools()
    tool_names = {t.name for t in tools}
    expected_tools = {
        "dream_history_list",
        "dream_history_get_tree",
        "dream_history_save_node",
        "dream_replay_run",
        "dream_replay_get_frontier",
        "dream_policy_compare",
        "dream_policy_plan_grid",
        "dream_status",
    }
    assert expected_tools.issubset(tool_names)

    status_res = await mcp_server.call_tool("dream_status", {})
    status_data = json.loads(_extract_text(status_res))
    assert status_data["status"] == "healthy"
    assert status_data["total_trees"] == 0

    root_node_payload = {
        "node_id": "r1",
        "parent_id": None,
        "branch_id": 0,
        "depth": 0,
        "observation": {
            "branch": 0,
            "attempt": 0,
            "score": 0.3,
            "evaluated": True,
            "valid": True,
            "fail_class": "ok",
        },
    }
    save_res = await mcp_server.call_tool(
        "dream_history_save_node",
        {"tree_id": "demo_tree", "node_data": root_node_payload},
    )
    save_data = json.loads(_extract_text(save_res))
    assert save_data["status"] == "success"
    assert save_data["total_nodes"] == 1

    child_node_payload = {
        "node_id": "c1",
        "parent_id": "r1",
        "branch_id": 1,
        "depth": 1,
        "observation": {
            "branch": 1,
            "attempt": 0,
            "score": 0.85,
            "evaluated": True,
            "valid": True,
            "fail_class": "ok",
        },
    }
    await mcp_server.call_tool(
        "dream_history_save_node",
        {"tree_id": "demo_tree", "node_data": child_node_payload},
    )

    list_res = await mcp_server.call_tool("dream_history_list", {})
    list_data = json.loads(_extract_text(list_res))
    assert "demo_tree" in list_data["tree_ids"]
    assert list_data["total_trees"] == 1

    get_res = await mcp_server.call_tool("dream_history_get_tree", {"tree_id": "demo_tree"})
    get_data = json.loads(_extract_text(get_res))
    assert get_data["status"] == "success"
    assert len(get_data["tree"]["nodes"]) == 2

    replay_res = await mcp_server.call_tool(
        "dream_replay_run",
        {"tree_id": "demo_tree", "beta": 0.5, "worker_cap": 5, "max_budget": 10},
    )
    replay_data = json.loads(_extract_text(replay_res))
    assert replay_data["status"] == "success"
    assert replay_data["result"]["max_score"] >= 0.85

    frontier_res = await mcp_server.call_tool(
        "dream_replay_get_frontier",
        {"beta_steps": 3, "worker_cap": 5, "max_budget": 10},
    )
    frontier_data = json.loads(_extract_text(frontier_res))
    assert frontier_data["status"] == "success"
    assert len(frontier_data["frontier"]) == 3

    compare_res = await mcp_server.call_tool(
        "dream_policy_compare",
        {"candidate_beta": 0.8, "baseline_beta": 0.2, "worker_cap": 5, "max_budget": 10},
    )
    compare_data = json.loads(_extract_text(compare_res))
    assert compare_data["status"] == "success"
    assert "delta_replay_score" in compare_data["comparison"]

    plan_res = await mcp_server.call_tool("dream_policy_plan_grid", {})
    plan_data = json.loads(_extract_text(plan_res))
    assert plan_data["status"] == "success"
    assert plan_data["plan"]["branch_count"] >= 1
    assert plan_data["plan"]["refine_count"] >= 0

    resources = await mcp_server.list_resources()
    resource_uris = {str(r.uri) for r in resources}
    assert "dream://history/manifest" in resource_uris
    assert "dream://status" in resource_uris

    manifest_read = await mcp_server.read_resource("dream://history/manifest")
    assert not isinstance(manifest_read, InputRequiredResult)
    items = list(manifest_read)
    assert len(items) > 0
    raw_content = items[0].content
    assert isinstance(raw_content, str)
    manifest_obj = json.loads(raw_content)
    assert manifest_obj["total_trees"] == 1
