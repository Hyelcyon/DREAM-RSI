<div align="center">

<p>
  <img src="assets/logos/google.svg" alt="Google" height="26" align="middle">
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logos/google-deepmind-dark.svg">
    <img src="assets/logos/google-deepmind-light.svg" alt="Google DeepMind" height="22" align="middle">
  </picture>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logos/umd-dark.svg">
    <img src="assets/logos/umd-light.svg" alt="University of Maryland, College Park" height="26" align="middle">
  </picture>
  &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logos/uva-dark.svg">
    <img src="assets/logos/uva-light.svg" alt="University of Virginia" height="28" align="middle">
  </picture>
</p>

**English** · [한국어](docs/languages/README_kr.md) · [日本語](docs/languages/README_jp.md) · [中文](docs/languages/README_cn.md)

# DREAM-RSI: Recursive Self-Improvement Engine

### Self-improving search policy optimization across discovery trees for AI agents.

**Record exploration attempts. Replay trajectories offline. Optimize search policy allocations.**

[![Release](https://img.shields.io/github/v/release/Hyelcyon/DREAM-RSI?style=flat&color=cb3837)](https://github.com/Hyelcyon/DREAM-RSI/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/Hyelcyon/DREAM-RSI/ci.yml?branch=main&style=flat&label=CI)](https://github.com/Hyelcyon/DREAM-RSI/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![MCP Protocol](https://img.shields.io/badge/MCP-11_tools_%7C_3_resources-5c4ee5?style=flat)](docs/mcp-contracts.md)
[![License: MIT](https://img.shields.io/badge/license-MIT-f4c430?style=flat)](LICENSE)
[![arXiv](https://img.shields.io/badge/arXiv-2609.14858-B31B1B?style=flat)](https://arxiv.org/abs/2609.14858)

[Quick start](#quick-start) · [MCP Tools](#mcp-tools) · [Mathematical Formulation](#mathematical-formulation) · [Verification](#development--verification) · [FAQ](#faq) · [Citation](#citation)

<code>uv run dream-rsi</code>

<br />

</div>

---

**DREAM-RSI** is a Python implementation of the *Dreaming While Exploring* recursive self-improvement framework (arXiv: 2609.14858), exposed as a Model Context Protocol (MCP) STDIO server.

Autonomous agents exploring algorithmic synthesis, mathematical optimization, or system code generate extensive trial-and-error discovery trees. Evaluating new search policies online requires repeated token expenditure and environment interactions. DREAM-RSI decouples **online tree expansion** from **offline policy evaluation**:

1. **Discovery Trees as Virtual Simulators**: Historical execution traces form a Directed Acyclic Graph (DAG) with execution outcomes and verification signals. The replay engine treats past discovery trees as a simulation environment without invoking external LLMs.
2. **Offline Replay ("Dreaming")**: Alternative search policies replay past state-action transitions over the graph to evaluate how different exploration-exploitation balances ($\beta$) perform.
3. **Multi-Objective Frontier Evaluation**: The engine computes empirical trade-offs between exploration breadth ($W$) and refinement depth ($R$) using Pareto efficiency metrics.
4. **Recursive Search Improvement**: The policy recommended by offline replay schedules subsequent online exploration rounds, populating richer discovery trees for future replay cycles.

---

## Quick start

### 1. Configure Your Agent

#### Automated Cross-Client Setup

Run the configuration script to automatically register DREAM-RSI in Claude Desktop, Claude Code, OpenAI Codex, and Antigravity:

```bash
uv run python scripts/configure_clients.py --all
```

#### Manual Configuration

##### Claude Desktop & Claude Code (`claude_desktop_config.json` or `.mcp.json`)

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

##### OpenAI Codex (`config.toml`)

```toml
[mcp_servers.dream-rsi]
command = "uv"
args = ["run", "--directory", "/absolute/path/to/DREAM-RSI", "dream-rsi"]
startup_timeout_sec = 60

[mcp_servers.dream-rsi.env]
DREAM_RSI_STORE_DIR = "/absolute/path/to/DREAM-RSI/data/trees"
```

##### Google Antigravity / Gemini CLI (`mcp_config.json`)

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

##### Cursor (`.cursor/mcp.json`)

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

### 2. Ask Your Agent

During or after an exploratory task, ask your agent to inspect, replay, and optimize:

```text
Record our current exploration tree with dream_history_save_node, run an offline replay across beta values, and compute the Pareto frontier to schedule the worker grid for the next iteration.
```

### 3. Standalone Terminal Execution

Run the MCP server directly via `uv`:

```bash
uv run dream-rsi
```

Diagnostic logs route strictly to standard error (stderr), keeping standard input and output clean for JSON-RPC transport frames.

---

## MCP Tools

DREAM-RSI provides 11 MCP tools and 3 MCP resources:

| Tool | Purpose | Key Parameters | Return Value |
| :--- | :--- | :--- | :--- |
| `dream_history_list` | List all registered discovery trees and sessions | None | JSON object with tree IDs and count |
| `dream_history_get_tree` | Retrieve complete node topology and metadata | `tree_id` | Full tree structure and node records |
| `dream_history_save_node` | Persist an exploration attempt node | `tree_id`, `node_data` | Confirmation with updated node count |
| `dream_replay_run` | Run offline virtual replay of a policy on a tree | `tree_id`, `beta`, `worker_cap`, `max_budget` | Replay episode metrics and max score |
| `dream_replay_get_frontier` | Compute beta-sweep Pareto frontier across all trees | `beta_steps`, `worker_cap`, `max_budget` | Array of Pareto frontier points |
| `dream_policy_compare` | Compare candidate policy against baseline policy | `candidate_beta`, `baseline_beta`, `worker_cap` | Win rate, score delta, recommendation |
| `dream_policy_plan_grid` | Plan deterministic branch count $W$ and depth $R$ | `context` (optional) | Recommended $W$ and $R$ grid parameters |
| `dream_policy_select_beta` | Calculate cross-cycle default beta adaptation | `history_scores`, `current_beta`, `worker_cap` | Next cycle beta, delta, and rationale |
| `dream_benchmark_evaluate` | Evaluate candidate construction on scientific tasks | `problem`, `payload` | Validation flag, metrics, and score |
| `dream_benchmark_create_tree` | Generate benchmark-grounded discovery tree | `problem`, `tree_id`, `num_branches`, `depth_per_branch` | Tree ID, problem type, and node count |
| `dream_status` | Query engine status and storage integrity | None | Health status and store path metadata |

### MCP Resources

- `dream://history/manifest`: Returns a summary manifest of all recorded discovery trees, best scores, and node counts.
- `dream://status`: Returns engine health diagnostics and storage directory verification.
- `dream://benchmarks/catalog`: Returns catalog of scientific discovery tasks and verification criteria.

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


## Development & Verification

DREAM-RSI uses `uv` and Python 3.10+.

### Setup

```bash
uv sync
```

### Static Type Analysis

```bash
uv run pyright
```

### Test Suite Execution

```bash
uv run pytest
```

### Live STDIO Protocol Verification

```bash
uv run python scripts/verify_mcp.py
```

---

## FAQ

<details>
<summary><strong>Which agents can use DREAM-RSI?</strong></summary>

Any agent supporting the Model Context Protocol (MCP) over STDIO. This includes Claude Code, Google Antigravity, Cursor, OpenAI Codex, and custom MCP clients.
</details>

<details>
<summary><strong>Does offline replay require external LLM calls or network access?</strong></summary>

No. Offline replay uses historical execution graphs and deterministic verification oracles recorded during online sessions. It evaluates policy choices mathematically without external network requests or language model inference.
</details>

<details>
<summary><strong>How are exploration trees stored?</strong></summary>

Discovery trees are serialized as Directed Acyclic Graphs in local JSON files under `DREAM_RSI_STORE_DIR` (or `data/trees/`). Writes are atomic, preventing partial file corruption.
</details>

<details>
<summary><strong>What do W and R represent in grid planning?</strong></summary>

$W$ represents the number of parallel exploration workers or hypothesis branches, while $R$ represents the refinement depth or iteration budget per branch. The grid planner optimizes this trade-off under a total budget $B$.
</details>

---

## Citation

If you reference DREAM-RSI in your research or agent workflows, please cite the foundational paper:

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
