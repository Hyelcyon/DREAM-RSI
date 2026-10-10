from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp.server.mcpserver import MCPServer
from mcp.types import CallToolResult, TextContent

from dream_rsi.mcp.server import create_mcp_server


def _extract_text(result: object) -> str:
    if not isinstance(result, CallToolResult):
        raise TypeError(f"Expected CallToolResult, got {type(result).__name__}")
    block = result.content[0]
    if isinstance(block, TextContent):
        return block.text
    raise TypeError(f"Expected TextContent, got {type(block).__name__}")


@pytest.mark.asyncio
async def test_mcp_benchmark_tools_and_beta_selection(tmp_path: Path) -> None:
    server = create_mcp_server(store_dir=tmp_path)

    # 1. Test create benchmark tree
    tree_tool_res = await server.call_tool(
        "dream_benchmark_create_tree",
        {
            "problem": "sum_difference",
            "tree_id": "tree_test_sd",
            "num_branches": 3,
            "depth_per_branch": 3,
        },
    )
    res = json.loads(_extract_text(tree_tool_res))
    assert res["status"] == "success"
    assert res["problem"] == "sum_difference"
    assert res["total_nodes"] == 10

    # 2. Test benchmark evaluate tool
    eval_tool_res = await server.call_tool(
        "dream_benchmark_evaluate",
        {
            "problem": "sum_difference",
            "payload": {"elements": [0, 2, 3, 4, 7, 11, 12, 14]},
        },
    )
    res_eval = json.loads(_extract_text(eval_tool_res))
    assert res_eval["status"] == "success"
    assert res_eval["result"]["is_valid"] is True
    assert res_eval["result"]["gamma_score"] > 0.0

    # 3. Test beta selection tool
    beta_tool_res = await server.call_tool(
        "dream_policy_select_beta",
        {
            "history_scores": [0.5, 0.7, 0.7],
            "current_beta": 0.5,
            "worker_cap": 3,
        },
    )
    res_beta = json.loads(_extract_text(beta_tool_res))
    assert res_beta["status"] == "success"
    assert "recommended_beta" in res_beta["result"]

    # 4. Test replay with Optimal policy
    replay_tool_res = await server.call_tool(
        "dream_replay_run",
        {
            "tree_id": "tree_test_sd",
            "beta": 0.6,
            "worker_cap": 3,
            "max_budget": 15,
            "policy_type": "optimal",
        },
    )
    res_rep = json.loads(_extract_text(replay_tool_res))
    assert res_rep["status"] == "success"
    assert res_rep["result"]["total_probes"] > 0
