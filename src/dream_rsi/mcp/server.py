from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from dream_rsi.core.models import (
    DiscoveryTree,
    GridPlanningContext,
    HistorySummaryItem,
    TreeNode,
)
from dream_rsi.optimizer.optimizer import PolicyOptimizer
from dream_rsi.optimizer.policy import DynamicPortfolioPolicy
from dream_rsi.replay.simulator import ReplaySimulator
from dream_rsi.storage.store import JsonFileHistoryStore

def create_mcp_server(
    store_dir: str | Path | None = None,
    server_name: str = "dream-rsi",
) -> MCPServer:
    if store_dir is None:
        store_dir = os.environ.get("DREAM_RSI_STORE_DIR", "data/trees")
    server = MCPServer(
        name=server_name,
        instructions="Dream-RSI Policy Optimization and Historical Replay MCP Server.",
    )
    store = JsonFileHistoryStore(base_dir=store_dir)
    simulator = ReplaySimulator()
    optimizer = PolicyOptimizer(simulator=simulator)

    @server.tool(name="dream_history_list")
    def dream_history_list() -> str:
        """List all registered discovery trees and sessions."""
        trees = store.list_trees()
        return json.dumps({
            "status": "success",
            "total_trees": len(trees),
            "tree_ids": trees,
        }, ensure_ascii=False)

    @server.tool(name="dream_history_get_tree")
    def dream_history_get_tree(tree_id: str) -> str:
        """Retrieve the topology and node metadata for a specific tree."""
        tree = store.get_tree(tree_id)
        if tree is None:
            return json.dumps({
                "status": "error",
                "message": f"Tree '{tree_id}' not found.",
            }, ensure_ascii=False)

        return json.dumps({
            "status": "success",
            "tree": tree.model_dump(mode="json"),
        }, ensure_ascii=False)

    @server.tool(name="dream_history_save_node")
    def dream_history_save_node(tree_id: str, node_data: dict[str, object]) -> str:
        """Persist a newly evaluated online exploration attempt into a discovery tree."""
        try:
            node = TreeNode.model_validate(node_data)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Invalid node schema: {str(e)}",
            }, ensure_ascii=False)

        tree = store.get_tree(tree_id)
        if tree is None:
            if not node.is_root:
                return json.dumps({
                    "status": "error",
                    "message": f"Cannot create new tree '{tree_id}' with non-root node.",
                }, ensure_ascii=False)
            tree = DiscoveryTree(tree_id=tree_id, root_id=node.node_id)
            tree.add_node(node)
            store.save_tree(tree)
        else:
            try:
                tree.add_node(node)
                store.save_tree(tree)
            except Exception as e:
                return json.dumps({
                    "status": "error",
                    "message": f"Failed to add node to tree: {str(e)}",
                }, ensure_ascii=False)

        return json.dumps({
            "status": "success",
            "tree_id": tree_id,
            "node_id": node.node_id,
            "total_nodes": len(tree.nodes),
        }, ensure_ascii=False)

    @server.tool(name="dream_replay_run")
    def dream_replay_run(
        tree_id: str,
        beta: float = 0.5,
        worker_cap: int = 10,
        max_budget: int = 100,
    ) -> str:
        """Execute offline virtual replay of a Dynamic Portfolio policy on a historical tree."""
        tree = store.get_tree(tree_id)
        if tree is None:
            return json.dumps({
                "status": "error",
                "message": f"Tree '{tree_id}' not found.",
            }, ensure_ascii=False)

        policy = DynamicPortfolioPolicy(
            name=f"portfolio_beta_{beta}",
            beta=beta,
            worker_cap=worker_cap,
        )
        res = simulator.run_episode(policy, tree, max_budget=max_budget)
        return json.dumps({
            "status": "success",
            "result": res.model_dump(mode="json"),
        }, ensure_ascii=False)

    @server.tool(name="dream_replay_get_frontier")
    def dream_replay_get_frontier(
        beta_steps: int = 5,
        worker_cap: int = 10,
        max_budget: int = 100,
    ) -> str:
        """Compute beta-sweep Pareto frontier across all historical discovery trees."""
        tree_ids = store.list_trees()
        trees = [t for tid in tree_ids if (t := store.get_tree(tid)) is not None]

        if not trees:
            return json.dumps({
                "status": "error",
                "message": "No historical trees found in store.",
            }, ensure_ascii=False)

        frontier = optimizer.evaluate_frontier(
            trees=trees,
            beta_steps=beta_steps,
            worker_cap=worker_cap,
            max_budget=max_budget,
        )
        return json.dumps({
            "status": "success",
            "trees_evaluated": len(trees),
            "frontier": [p.model_dump(mode="json") for p in frontier],
        }, ensure_ascii=False)

    @server.tool(name="dream_policy_compare")
    def dream_policy_compare(
        candidate_beta: float,
        baseline_beta: float = 0.5,
        worker_cap: int = 10,
        max_budget: int = 100,
    ) -> str:
        """Compare candidate policy against baseline policy across stored discovery trees."""
        tree_ids = store.list_trees()
        trees = [t for tid in tree_ids if (t := store.get_tree(tid)) is not None]

        if not trees:
            return json.dumps({
                "status": "error",
                "message": "No historical trees found in store.",
            }, ensure_ascii=False)

        cand_policy = DynamicPortfolioPolicy(
            name=f"candidate_beta_{candidate_beta}",
            beta=candidate_beta,
            worker_cap=worker_cap,
        )
        base_policy = DynamicPortfolioPolicy(
            name=f"baseline_beta_{baseline_beta}",
            beta=baseline_beta,
            worker_cap=worker_cap,
        )

        comparison = optimizer.compare_policies(
            candidate_policy=cand_policy,
            baseline_policy=base_policy,
            trees=trees,
            max_budget=max_budget,
        )
        return json.dumps({
            "status": "success",
            "comparison": comparison.model_dump(mode="json"),
        }, ensure_ascii=False)

    @server.tool(name="dream_policy_plan_grid")
    def dream_policy_plan_grid(
        context: dict[str, object] | None = None,
    ) -> str:
        """Plan branch count W and refinement depth R deterministically for next live episode."""
        if context is not None:
            ctx = GridPlanningContext.model_validate(context)
        else:
            manifest = store.get_manifest()
            history_summary: list[HistorySummaryItem] = []
            for item in manifest.trees:
                tree = store.get_tree(item.tree_id)
                max_d = max([n.depth for n in tree.nodes.values()]) if tree and tree.nodes else 0
                history_summary.append(
                    HistorySummaryItem(
                        tree_id=item.tree_id,
                        best_score=item.best_score,
                        max_depth=max_d,
                        node_count=item.node_count,
                    )
                )
            ctx = GridPlanningContext(history=history_summary)

        plan = DynamicPortfolioPolicy.plan_grid(ctx)
        return json.dumps({
            "status": "success",
            "plan": plan.model_dump(mode="json"),
        }, ensure_ascii=False)

    @server.tool(name="dream_status")
    def dream_status() -> str:
        """Get engine status, registered tree counts, and storage configuration."""
        manifest = store.get_manifest()
        return json.dumps({
            "status": "healthy",
            "engine": "Dream-RSI Cleanroom v1.0",
            "total_trees": manifest.total_trees,
            "storage_dir": str(store.base_dir),
            "manifest": manifest.model_dump(mode="json"),
        }, ensure_ascii=False)

    @server.resource("dream://history/manifest")
    def resource_manifest() -> str:
        """Manifest summary of all recorded discovery trees."""
        return json.dumps(store.get_manifest().model_dump(mode="json"), ensure_ascii=False)

    @server.resource("dream://status")
    def resource_status() -> str:
        """Diagnostics and health status of the Dream-RSI engine."""
        return json.dumps({
            "status": "healthy",
            "engine": "Dream-RSI Cleanroom v1.0",
            "trees": len(store.list_trees()),
        }, ensure_ascii=False)

    return server


def main() -> None:
    server = create_mcp_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
