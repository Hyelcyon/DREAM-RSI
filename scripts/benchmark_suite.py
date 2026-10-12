from __future__ import annotations

import json
import statistics
import time
import tracemalloc
from pathlib import Path
from typing import Any, Callable

from dream_rsi.benchmarks import generate_benchmark_discovery_tree
from dream_rsi.core.models import DiscoveryTree, Observation, TreeNode
from dream_rsi.optimizer.optimizer import PolicyOptimizer
from dream_rsi.optimizer.policy import DynamicPortfolioPolicy, OptimalPolicy
from dream_rsi.replay.simulator import ReplaySimulator
from dream_rsi.storage.store import JsonFileHistoryStore


def create_deep_chain_tree(depth: int = 100) -> DiscoveryTree:
    root = TreeNode(
        node_id="root",
        parent_id=None,
        branch_id=0,
        depth=0,
        observation=Observation(branch=0, attempt=0, score=0.1, evaluated=True),
    )
    tree = DiscoveryTree(tree_id=f"deep_chain_{depth}", root_id="root")
    tree.add_node(root)
    prev = "root"
    for d in range(1, depth + 1):
        nid = f"node_{d}"
        node = TreeNode(
            node_id=nid,
            parent_id=prev,
            branch_id=1,
            depth=d,
            attempt_index=d,
            observation=Observation(
                branch=1,
                attempt=d,
                score=0.1 + (d * 0.005),
                evaluated=True,
                valid=True,
                fail_class="ok",
            ),
        )
        tree.add_node(node)
        prev = nid
    return tree


def create_wide_tree(num_branches: int = 50, depth: int = 20) -> DiscoveryTree:
    root = TreeNode(
        node_id="root",
        parent_id=None,
        branch_id=0,
        depth=0,
        observation=Observation(branch=0, attempt=0, score=0.1, evaluated=True),
    )
    tree = DiscoveryTree(tree_id=f"wide_{num_branches}x{depth}", root_id="root")
    tree.add_node(root)
    for b in range(1, num_branches + 1):
        prev = "root"
        for d in range(1, depth + 1):
            nid = f"n_b{b}_d{d}"
            node = TreeNode(
                node_id=nid,
                parent_id=prev,
                branch_id=b,
                depth=d,
                attempt_index=d,
                observation=Observation(
                    branch=b,
                    attempt=d,
                    score=0.1 + (d * 0.02) + (b * 0.001),
                    evaluated=True,
                    valid=True,
                    fail_class="ok",
                ),
            )
            tree.add_node(node)
            prev = nid
    return tree


def time_callable(
    fn: Callable[[], Any],
    iterations: int = 5,
    warmup: int = 1,
) -> dict[str, float]:
    for _ in range(warmup):
        fn()

    durations: list[float] = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        fn()
        durations.append(time.perf_counter() - t0)

    tracemalloc.start()
    tracemalloc.reset_peak()
    fn()
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return {
        "iterations": float(iterations),
        "mean_ms": statistics.mean(durations) * 1000.0,
        "median_ms": statistics.median(durations) * 1000.0,
        "min_ms": min(durations) * 1000.0,
        "max_ms": max(durations) * 1000.0,
        "std_ms": statistics.stdev(durations) * 1000.0 if len(durations) > 1 else 0.0,
        "peak_memory_kb": peak_bytes / 1024.0,
    }


def run_benchmark_suite(output_file: Path | None = None) -> dict[str, Any]:
    print("Preparing benchmark fixtures...")
    deep_tree = create_deep_chain_tree(depth=200)
    wide_tree = create_wide_tree(num_branches=25, depth=15)
    bench_trees = [
        generate_benchmark_discovery_tree("sum_difference", "tree_sd", num_branches=6, depth_per_branch=6),
        generate_benchmark_discovery_tree("circle_packing", "tree_cp", num_branches=6, depth_per_branch=6),
        generate_benchmark_discovery_tree("lasso", "tree_lasso", num_branches=6, depth_per_branch=6),
    ]

    temp_store_dir = Path("data/bench_store").resolve()
    temp_store_dir.mkdir(parents=True, exist_ok=True)
    bench_store = JsonFileHistoryStore(base_dir=temp_store_dir)
    for bt in bench_trees:
        bench_store.save_tree(bt)

    results: dict[str, Any] = {}

    print("Running Benchmark 1: Tree integrity validation (deep chain)...")
    results["tree_check_integrity_deep_chain_200"] = time_callable(
        lambda: deep_tree.check_integrity(),
        iterations=10,
        warmup=2,
    )

    print("Running Benchmark 2: Tree integrity validation (wide 25x15 = 376 nodes)...")
    results["tree_check_integrity_wide_376"] = time_callable(
        lambda: wide_tree.check_integrity(),
        iterations=10,
        warmup=2,
    )

    print("Running Benchmark 3: Storage get_manifest (3 benchmark trees)...")
    results["storage_get_manifest"] = time_callable(
        lambda: bench_store.get_manifest(),
        iterations=10,
        warmup=2,
    )

    print("Running Benchmark 4: Storage save_tree & get_tree...")
    results["storage_save_and_get_tree"] = time_callable(
        lambda: (bench_store.save_tree(bench_trees[0]), bench_store.get_tree(bench_trees[0].tree_id)),
        iterations=10,
        warmup=2,
    )

    print("Running Benchmark 5: ReplaySimulator run_episode (OptimalPolicy)...")
    simulator = ReplaySimulator()
    opt_policy = OptimalPolicy(config={"name": "opt", "beta": 0.6, "worker_cap": 8})
    results["replay_run_episode_optimal"] = time_callable(
        lambda: simulator.run_episode(opt_policy, bench_trees[0], max_budget=60),
        iterations=10,
        warmup=2,
    )

    print("Running Benchmark 6: PolicyOptimizer evaluate_frontier (3 trees, beta_steps=5)...")
    optimizer = PolicyOptimizer(simulator=simulator)
    results["optimizer_evaluate_frontier_3_trees"] = time_callable(
        lambda: optimizer.evaluate_frontier(bench_trees, beta_steps=5, worker_cap=8, max_budget=50),
        iterations=5,
        warmup=1,
    )

    print("Running Benchmark 7: PolicyOptimizer compare_policies...")
    cand_policy = DynamicPortfolioPolicy(name="cand", beta=0.8, worker_cap=8)
    base_policy = DynamicPortfolioPolicy(name="base", beta=0.4, worker_cap=8)
    results["optimizer_compare_policies"] = time_callable(
        lambda: optimizer.compare_policies(cand_policy, base_policy, bench_trees, max_budget=50),
        iterations=5,
        warmup=1,
    )

    # Cleanup temp store
    for f in temp_store_dir.glob("*.json"):
        f.unlink()
    try:
        temp_store_dir.rmdir()
    except OSError:
        pass

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(results, indent=2))

    return results


if __name__ == "__main__":
    out_path = Path("benchmarks_baseline.json").resolve()
    res = run_benchmark_suite(output_file=out_path)
    print("\n=== BENCHMARK RESULTS ===")
    for name, data in res.items():
        print(f"{name:45s}: {data['median_ms']:8.2f} ms (min: {data['min_ms']:8.2f} ms, peak mem: {data['peak_memory_kb']:7.1f} KB)")
