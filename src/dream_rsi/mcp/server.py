from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from dream_rsi.benchmarks import (
    AutocorrelationEvaluator,
    Circle,
    CirclePackingEvaluator,
    LassoEvaluator,
    SumDifferenceEvaluator,
    generate_benchmark_discovery_tree,
)
from dream_rsi.core.models import (
    DiscoveryTree,
    GridPlanningContext,
    HistorySummaryItem,
    TreeNode,
)
from dream_rsi.optimizer.optimizer import PolicyOptimizer
from dream_rsi.optimizer.policy import DynamicPortfolioPolicy, OptimalPolicy
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
        beta: float = 0.6,
        worker_cap: int = 10,
        max_budget: int = 100,
        policy_type: str = "optimal",
    ) -> str:
        """Execute offline virtual replay of an exploration policy on a historical tree."""
        tree = store.get_tree(tree_id)
        if tree is None:
            return json.dumps({
                "status": "error",
                "message": f"Tree '{tree_id}' not found.",
            }, ensure_ascii=False)

        if policy_type == "optimal":
            policy = OptimalPolicy(config={
                "name": f"optimal_beta_{beta}",
                "beta": beta,
                "worker_cap": worker_cap,
            })
        else:
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

    @server.tool(name="dream_policy_select_beta")
    def dream_policy_select_beta(
        history_scores: list[float] | None = None,
        current_beta: float = 0.6,
        worker_cap: int = 10,
    ) -> str:
        """Calculates next-cycle default beta adaptation using historical trend and Pareto frontier."""
        tree_ids = store.list_trees()
        trees = [t for tid in tree_ids if (t := store.get_tree(tid)) is not None]

        frontier = optimizer.evaluate_frontier(
            trees=trees,
            beta_steps=5,
            worker_cap=worker_cap,
        ) if trees else []

        scores = history_scores or []
        res = optimizer.select_cross_cycle_beta(
            history_scores=scores,
            current_beta=current_beta,
            sweep_frontier=frontier,
        )
        return json.dumps({
            "status": "success",
            "result": res.model_dump(mode="json"),
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

        plan = OptimalPolicy.plan_grid(ctx)
        return json.dumps({
            "status": "success",
            "plan": plan.model_dump(mode="json"),
        }, ensure_ascii=False)

    @server.tool(name="dream_benchmark_evaluate")
    def dream_benchmark_evaluate(
        problem: str,
        payload: dict[str, Any],
    ) -> str:
        """Evaluates a candidate construction on scientific benchmark tasks (sum_difference, circle_packing, autocorrelation, lasso)."""
        prob = problem.lower().strip()
        if prob == "sum_difference":
            action = payload.get("action", "evaluate")
            if action == "search":
                max_iter = int(payload.get("max_iterations", 150))
                seed = int(payload.get("seed", 42))
                best_set, best_g = SumDifferenceEvaluator.search_high_gamma(max_iterations=max_iter, seed=seed)
                eval_res = SumDifferenceEvaluator.evaluate(best_set)
                return json.dumps({"status": "success", "best_set": best_set, "result": eval_res.model_dump(mode="json")})
            elements = payload.get("elements", [])
            if not isinstance(elements, list):
                return json.dumps({"status": "error", "message": "'elements' must be a list of integers."})
            int_elems = [int(x) for x in elements]
            eval_res = SumDifferenceEvaluator.evaluate(int_elems)
            return json.dumps({"status": "success", "result": eval_res.model_dump(mode="json")})

        if prob == "circle_packing":
            action = payload.get("action", "evaluate")
            raw_circles = payload.get("circles", [])
            if not isinstance(raw_circles, list):
                return json.dumps({"status": "error", "message": "'circles' must be a list of objects with x, y, r."})
            circles = [Circle.model_validate(c) for c in raw_circles]
            if action == "optimize":
                steps = int(payload.get("max_iterations", 150))
                optimized = CirclePackingEvaluator.optimize_packing(circles, max_iterations=steps)
                eval_res = CirclePackingEvaluator.evaluate(optimized)
                return json.dumps({
                    "status": "success",
                    "optimized_circles": [c.model_dump() for c in optimized],
                    "result": eval_res.model_dump(mode="json"),
                })
            eval_res = CirclePackingEvaluator.evaluate(circles)
            return json.dumps({"status": "success", "result": eval_res.model_dump(mode="json")})

        if prob == "autocorrelation":
            grid = payload.get("grid_values", [])
            if not isinstance(grid, list):
                return json.dumps({"status": "error", "message": "'grid_values' must be a list of floats."})
            float_grid = [float(x) for x in grid]
            eval_res = AutocorrelationEvaluator.evaluate(float_grid)
            return json.dumps({"status": "success", "result": eval_res.model_dump(mode="json")})

        if prob == "lasso":
            if "instance_runtimes_sec" in payload:
                runtimes = [float(t) for t in payload["instance_runtimes_sec"]]
                r_search = LassoEvaluator.calculate_geometric_mean_search_score(runtimes)
                return json.dumps({"status": "success", "r_search": r_search, "instances_count": len(runtimes)})
            x_rows = payload.get("x_rows", [])
            y = payload.get("y", [])
            lambdas = payload.get("lambdas", [])
            candidate_path = payload.get("candidate_path", [])
            runtime_ms = float(payload.get("runtime_ms", 10.0))
            eval_res = LassoEvaluator.evaluate_solution(
                x_rows=x_rows,
                y=y,
                lam_path=lambdas,
                candidate_path=candidate_path,
                runtime_ms=runtime_ms,
            )
            return json.dumps({"status": "success", "result": eval_res.model_dump(mode="json")})

        return json.dumps({
            "status": "error",
            "message": f"Unknown problem type '{problem}'. Supported: 'sum_difference', 'circle_packing', 'autocorrelation', 'lasso'.",
        })

    @server.tool(name="dream_benchmark_create_tree")
    def dream_benchmark_create_tree(
        problem: str,
        tree_id: str,
        num_branches: int = 4,
        depth_per_branch: int = 4,
        seed: int = 42,
    ) -> str:
        """Instantiates a realistic benchmark-grounded discovery tree and saves it into the store."""
        try:
            tree = generate_benchmark_discovery_tree(
                problem_type=problem,
                tree_id=tree_id,
                num_branches=num_branches,
                depth_per_branch=depth_per_branch,
                seed=seed,
            )
            store.save_tree(tree)
            return json.dumps({
                "status": "success",
                "tree_id": tree_id,
                "problem": problem,
                "total_nodes": len(tree.nodes),
            })
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

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

    @server.resource("dream://benchmarks/catalog")
    def resource_benchmarks() -> str:
        """Catalog of paper-grounded scientific discovery tasks."""
        return json.dumps({
            "benchmarks": [
                {
                    "name": "lasso",
                    "domain": "Algorithm Engineering",
                    "objective": "R_search = (prod t_i)^(-1/|I|) with KKT 1e-6 check",
                },
                {
                    "name": "sum_difference",
                    "domain": "Discrete Mathematics",
                    "objective": "Gamma(A) = log(|A+A|/|A|) / log(|A-A|/|A|)",
                },
                {
                    "name": "circle_packing",
                    "domain": "Geometric Optimization",
                    "objective": "Maximize sum r_i inside unit square with non-overlap",
                },
                {
                    "name": "autocorrelation",
                    "domain": "Functional Analysis",
                    "objective": "Minimize autoconvolution sup norm Phi_1(f)",
                },
            ]
        }, ensure_ascii=False)

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
