# DREAM-RSI MCP Tool & Resource Contracts

This document specifies the Model Context Protocol (MCP) tool schemas and resources exposed by DREAM-RSI over STDIO JSON-RPC.

## Diagnostic Logging

All diagnostic and error output is written strictly to `stderr`. Standard output (`stdout`) is reserved exclusively for JSON-RPC transport frames.

---

## Tools

### 1. `dream_history_list`
Lists all discovery trees registered in the local storage directory.

- **Parameters**: None
- **Response Schema**:
  ```json
  {
    "status": "success",
    "total_trees": 12,
    "tree_ids": ["tree_001", "tree_002"]
  }
  ```

### 2. `dream_history_get_tree`
Retrieves complete topological structure and node observation data for a specific tree.

- **Parameters**:
  - `tree_id` (`string`, required): Identifier of the target discovery tree.
- **Response Schema**:
  ```json
  {
    "status": "success",
    "tree": {
      "tree_id": "tree_001",
      "root_id": "node_0",
      "nodes": { ... },
      "branches": { ... },
      "created_at": 1740000000.0,
      "metadata": { ... }
    }
  }
  ```

### 3. `dream_history_save_node`
Appends a newly evaluated online exploration node to the specified tree.

- **Parameters**:
  - `tree_id` (`string`, required): Target discovery tree ID.
  - `node_data` (`object`, required): Node schema conforming to `TreeNode`.
    - `node_id` (`string`, required)
    - `parent_id` (`string | null`, required)
    - `branch_id` (`integer`, optional, default `0`)
    - `attempt_index` (`integer`, optional, default `0`)
    - `depth` (`integer`, optional, default `0`)
    - `observation` (`object`, required)
- **Response Schema**:
  ```json
  {
    "status": "success",
    "tree_id": "tree_001",
    "node_id": "node_1",
    "total_nodes": 2
  }
  ```

### 4. `dream_replay_run`
Executes an offline virtual simulation episode on a historical tree using a Dynamic Portfolio policy.

- **Parameters**:
  - `tree_id` (`string`, required): Discovery tree to replay.
  - `beta` (`number`, optional, default `0.5`): Exploitation factor $\in [0, 1]$.
  - `worker_cap` (`integer`, optional, default `10`): Maximum concurrent worker simulation.
  - `max_budget` (`integer`, optional, default `100`): Maximum attempt budget for the episode.
- **Response Schema**:
  ```json
  {
    "status": "success",
    "result": {
      "policy_name": "portfolio_beta_0.5",
      "tree_id": "tree_001",
      "attempts_used": 15,
      "max_score": 0.92,
      "replay_score": 1.15
    }
  }
  ```

### 5. `dream_replay_get_frontier`
Computes the Pareto frontier by sweeping $\beta$ values across all stored discovery trees.

- **Parameters**:
  - `beta_steps` (`integer`, optional, default `5`): Discretization steps for beta sweeping.
  - `worker_cap` (`integer`, optional, default `10`): Maximum concurrent worker simulation.
  - `max_budget` (`integer`, optional, default `100`): Budget per simulation.
- **Response Schema**:
  ```json
  {
    "status": "success",
    "trees_evaluated": 5,
    "frontier": [
      { "beta": 0.0, "mean_score": 0.72, "mean_cost": 10.0 },
      { "beta": 0.5, "mean_score": 0.88, "mean_cost": 14.5 }
    ]
  }
  ```

### 6. `dream_policy_compare`
Statistically compares a candidate policy against a baseline policy across stored discovery trees.

- **Parameters**:
  - `candidate_beta` (`number`, required): Candidate exploitation factor.
  - `baseline_beta` (`number`, optional, default `0.5`): Baseline exploitation factor.
  - `worker_cap` (`integer`, optional, default `10`): Maximum concurrent worker count.
  - `max_budget` (`integer`, optional, default `100`): Simulation attempt budget.
- **Response Schema**:
  ```json
  {
    "status": "success",
    "comparison": {
      "candidate_mean": 0.91,
      "baseline_mean": 0.85,
      "delta": 0.06,
      "win_rate": 0.75,
      "recommendation": "adopt_candidate"
    }
  }
  ```

### 7. `dream_policy_plan_grid`
Determines optimal search parameters (branch width $W$ and depth $R$) deterministically for subsequent live tasks.

- **Parameters**:
  - `context` (`object`, optional): Historical context summary.
- **Response Schema**:
  ```json
  {
    "status": "success",
    "plan": {
      "width_W": 15,
      "depth_R": 3,
      "total_budget": 45,
      "rationale": "High historical branching yield indicates wide exploration priority"
    }
  }
  ```

### 8. `dream_status`
Queries engine health, registered tree counts, and active storage path.

- **Parameters**: None
- **Response Schema**:
  ```json
  {
    "status": "healthy",
    "engine": "Dream-RSI Cleanroom v1.0",
    "total_trees": 1,
    "storage_dir": "data/trees",
    "manifest": { ... }
  }
  ```

---

## Resources

### `dream://history/manifest`
Returns a JSON summary manifest of all discovery trees, including node counts, best recorded scores, and timestamps.

### `dream://status`
Returns real-time health status, engine version, and active tree count.
