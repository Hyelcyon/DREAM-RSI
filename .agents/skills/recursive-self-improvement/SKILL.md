---
name: recursive-self-improvement
description: Optimize autonomous exploration policies using offline Monte Carlo replay over discovery trees with DREAM-RSI. Use when searching code, algorithm, or mathematical solution spaces across multiple attempts.
metadata:
  version: "1.0"
---

# Recursive Self-Improvement (DREAM-RSI)

Use DREAM-RSI when exploring complex algorithmic, mathematical, or scientific hypothesis spaces across multiple iterative steps. DREAM-RSI simulates past exploration trees as virtual offline execution environments, refining search policies with zero external LLM token overhead.

## Core Agent Workflow

```
1. Initialize/Resume Tree ───► 2. Record Attempt ───► 3. Offline Replay ───► 4. Plan Next Grid
   (dream_history_get_tree)     (dream_history_save_node)  (dream_replay_run)     (dream_policy_plan_grid)
```

### 1. Online Recording of Exploration Nodes

Whenever evaluating a candidate implementation, benchmark, or hypothesis, record the attempt into the discovery tree:

```json
{
  "tree_id": "sorting_algo_v1",
  "node_data": {
    "node_id": "step_1_attempt_2",
    "parent_id": "step_1_root",
    "branch_id": 1,
    "attempt_index": 2,
    "depth": 1,
    "observation": {
      "branch": 1,
      "attempt": 2,
      "score": 0.85,
      "evaluated": true,
      "valid": true,
      "fail_class": "ok"
    }
  }
}
```

- **Acyclicity Invariant**: Ensure `parent_id` refers to an existing node in the tree. Root nodes must have `parent_id: null`.
- **Failure Classification**: Categorize failures precisely (`syntax_error`, `runtime_error`, `shape_mismatch`, `timeout`, or `ok`).

### 2. Offline Policy Replay ("Dreaming")

When a task concludes or reaches a milestone, execute an offline virtual replay without spending LLM tokens:

- Call `dream_replay_run(tree_id, beta=0.5, worker_cap=10)` to assess trajectory yields under varying $\beta$ values.
- Call `dream_replay_get_frontier()` to compute the empirical Pareto frontier across all historical discovery trees.

### 3. Policy Comparison and Grid Planning

Before launching a new generation of exploratory attempts:

1. Compare policy alternatives using `dream_policy_compare(candidate_beta, baseline_beta)`.
2. Determine optimal branch width $W$ and refinement depth $R$ using `dream_policy_plan_grid()`.
3. Allocate your reasoning budget according to the recommended $(W, R)$ grid parameters.
