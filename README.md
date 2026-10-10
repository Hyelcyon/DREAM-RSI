<div align="center">

**English** · [한국어](docs/languages/README_kr.md) · [日本語](docs/languages/README_jp.md) · [中文](docs/languages/README_cn.md)

# DREAM-RSI: Recursive Self-Improvement Engine

### Offline Monte Carlo Replay & Search Policy Optimization MCP Server for AI Agents

**Simulate historical discovery trees. Optimize search policies offline with zero token expenditure.**

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![MCP Protocol](https://img.shields.io/badge/MCP-8_tools_%7C_2_resources-5c4ee5?style=flat-square)](docs/mcp-contracts.md)
[![Type Checked](https://img.shields.io/badge/types-pyright_strict-blue?style=flat-square)](pyrightconfig.json)
[![Tests](https://img.shields.io/badge/tests-23%20passed-success?style=flat-square)](tests)
[![License: MIT](https://img.shields.io/badge/license-MIT-f4c430?style=flat-square)](LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-2609.14858-B31B1B?style=flat-square)](https://arxiv.org/abs/2609.14858)

[Quick start](#quick-start) · [How DREAM-RSI works](#how-dream-rsi-works) · [MCP Tools](#mcp-tools) · [Mathematical Formulation](#mathematical-formulation) · [Development & Verification](#development--verification) · [Citation](#citation)

<code>uv run dream-rsi</code>

<br />

</div>

---

**DREAM-RSI** is an independent, cleanroom Python implementation of the *Dreaming While Exploring* recursive self-improvement framework (arXiv: 2609.14858). It exposes self-improving search policy optimization as a standard Model Context Protocol (MCP) server over standard input and output (STDIO).

Autonomous AI agents frequently explore high-dimensional code, mathematical, or scientific search spaces. Standard exploration strategies either waste compute by re-evaluating poor hypotheses or exhaust token budgets querying LLMs for meta-planning. DREAM-RSI decouples **online discovery** from **offline policy refinement**:

- **Zero Token Overhead**: Historical discovery trees serve as virtual replay environments. Offline policy optimization requires zero LLM API calls and zero external token consumption.
- **Topological Integrity**: Enforces strict Directed Acyclic Graph (DAG) contracts with cycle detection and atomic JSON persistence.
- **Dynamic Portfolio Optimization**: Solves the Pareto frontier between broad hypothesis branching ($W$) and deep iterative refinement ($R$).
- **Deterministic Grid Planning**: Dynamically schedules worker budgets and probe limits based on empirical replay performance.

---

## Quick start

### 1. Agent Configuration

DREAM-RSI connects natively to Claude Code, Antigravity, Cursor, and OpenAI Codex via standard STDIO MCP configuration.

#### Claude Code (`claude_desktop_config.json` or project MCP config)

```json
{
  "mcpServers": {
    "dream-rsi": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/DREAM-RSI", "dream-rsi"],
      "env": {
        "DREAM_RSI_STORE_DIR": "/absolute/path/to/DREAM-RSI/data/trees"
      }
    }
  }
}
```

#### Google Antigravity / Gemini CLI (`mcp_config.json`)

```json
{
  "mcpServers": {
    "dream-rsi": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/DREAM-RSI", "dream-rsi"]
    }
  }
}
```

#### OpenAI Codex (`config.toml`)

```toml
[mcp_servers.dream-rsi]
command = "uv"
args = ["run", "--directory", "/absolute/path/to/DREAM-RSI", "dream-rsi"]
```

### 2. Standalone Terminal Execution

Run the MCP server directly via `uv`:

```bash
uv run dream-rsi
```

All diagnostic output is routed strictly to standard error (stderr) to preserve JSON-RPC transport integrity across STDIO.

---

## How DREAM-RSI works

```
 ┌────────────────────────────────────────────────────────┐
 │                   Online Exploration                   │
 │   Agent attempts code/math hypothesis generation       │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼  dream_history_save_node
 ┌────────────────────────────────────────────────────────┐
 │                 Discovery Tree Storage                 │
 │   Local JSON DAG: Invariant validation & acyclicity    │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼  Offline Simulation ("Dreaming")
 ┌────────────────────────────────────────────────────────┐
 │                 Replay Simulation Engine               │
 │   Simulate execution paths from past discovery trees   │
 │   Zero external tokens, deterministic reward replay    │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼  dream_replay_get_frontier
 ┌────────────────────────────────────────────────────────┐
 │                 Pareto Policy Optimizer                │
 │   Compute empirical frontier across beta parameters    │
 └───────────────────────────┬────────────────────────────┘
                             │
                             ▼  dream_policy_plan_grid
 ┌────────────────────────────────────────────────────────┐
 │                Next Episode Grid Planner               │
 │   Determine optimal (W, R) allocation for next run     │
 └────────────────────────────────────────────────────────┘
```

1. **Online Recording**: During interactive reasoning sessions, the host agent records attempts using `dream_history_save_node`. Each node captures execution state, verification status, and error taxonomy.
2. **Offline Replay**: When the session pauses or completes, the agent invokes `dream_replay_run`. The simulator reconstructs past decision trajectories and replays them under varied $\beta$ exploitation parameters.
3. **Pareto Frontier Discovery**: The optimizer computes the trade-off curve across all historical trees using `dream_replay_get_frontier`.
4. **Adaptive Allocation**: The agent queries `dream_policy_plan_grid` to receive mathematical recommendations for branch width ($W$) and refinement depth ($R$) on subsequent exploration tasks.

---

## MCP Tools

DREAM-RSI registers 8 MCP tools and 2 MCP resources:

| Tool | Purpose | Key Parameters | Return Value |
| :--- | :--- | :--- | :--- |
| `dream_history_list` | List all registered discovery trees and sessions | None | JSON object with tree IDs and count |
| `dream_history_get_tree` | Retrieve complete node topology and metadata | `tree_id` | Full tree structure and node records |
| `dream_history_save_node` | Persist an exploration attempt node | `tree_id`, `node_data` | Confirmation with updated node count |
| `dream_replay_run` | Run offline virtual replay of a policy on a tree | `tree_id`, `beta`, `worker_cap`, `max_budget` | Replay episode metrics and max score |
| `dream_replay_get_frontier` | Compute beta-sweep Pareto frontier across all trees | `beta_steps`, `worker_cap`, `max_budget` | Array of Pareto frontier points |
| `dream_policy_compare` | Compare candidate policy against baseline policy | `candidate_beta`, `baseline_beta`, `worker_cap` | Win rate, score delta, recommendation |
| `dream_policy_plan_grid` | Plan deterministic branch count $W$ and depth $R$ | `context` (optional) | Recommended $W$ and $R$ grid parameters |
| `dream_status` | Query engine status and storage integrity | None | Health status and store path metadata |

### MCP Resources

- `dream://history/manifest`: Returns a summary manifest of all recorded discovery trees, best scores, and node counts.
- `dream://status`: Returns engine health diagnostics and storage directory verification.

---

## Mathematical Formulation

### Dual Exploration vs. Exploitation ($\beta$)

The dynamic portfolio policy samples exploration actions according to candidate quality scores and exploitation factor $\beta \in [0, 1]$:

$$P(\text{refine} \mid \text{node}_i) \propto \exp\left(\frac{\beta \cdot \text{score}_i}{\tau}\right)$$

- When $\beta \to 0$, the engine emphasizes wide diversity sampling across unverified branches.
- When $\beta \to 1$, the engine focuses computation on refining high-scoring candidate nodes.

### Search Grid Optimization $(W, R)$

Given worker budget $B$, DREAM-RSI plans the allocation between branch breadth $W$ and refinement depth $R$:

$$W \cdot R \le B, \quad \max_{W, R} \mathbb{E}\left[\max_{i \le W} S_i^{(R)}\right]$$

---

## Architecture and Safety Invariants

- **Offline Boundary**: Zero outgoing network requests or telemetry. Storage operations are confined strictly to the configured directory (`DREAM_RSI_STORE_DIR`).
- **Path Confinement**: Directory traversal patterns (`../`) are detected and rejected with explicit exceptions.
- **Atomic Persistence**: Discovery tree mutations use atomic filesystem writes to guarantee durability against unexpected crashes.
- **Strict Typing**: Type checking operates under Pyright strict mode without `Any` overrides.

---

## Development & Verification

DREAM-RSI uses `uv` and Python 3.10+.

### Setup

```bash
uv sync
```

### Run Tests

Execute the test suite covering unit models, evaluator math, and integration loops:

```bash
uv run pytest
```

### Static Type Analysis

Execute strict static typing analysis:

```bash
uv run pyright
```

### Live MCP Protocol Handshake Verification

Verify STDIO JSON-RPC handshake, schema enumeration, and live execution across all 8 tools:

```bash
uv run python scripts/verify_mcp.py
```

---

## Citation

If you use DREAM-RSI in your research or autonomous agent workflows, please cite the foundational research paper:

```bibtex
@article{zheng2026dreamrsi,
  title={Dreaming While Exploring: Recursive Self-Improvement in LLM-Based Discovery Systems},
  author={Zheng, Kid and collaborators},
  journal={arXiv preprint arXiv:2609.14858},
  year={2026}
}
```

---

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) and [NOTICE](NOTICE) for details.
