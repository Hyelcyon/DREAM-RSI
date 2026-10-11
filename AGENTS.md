# Repository Guidelines

## Product and Authority

Dream-RSI is a cleanroom Python implementation of the Dream-RSI (Recursive Self-Improvement) search policy optimization framework, exposing engine capabilities through shared CLI and Model Context Protocol (MCP) STDIO workflows. It separates online discovery from offline policy improvement by simulating historical discovery trees as virtual execution environments without invoking external LLMs.

The simulation and evaluation engine operates strictly offline with zero external token expenditure. It has no authority to make external network requests, provision remote resources, or mutate outside filesystem trees. All exploration history is contained within local JSON stores governed by `DREAM_RSI_STORE_DIR` or the local `data/trees` directory.

The MCP adapter provides 11 tools and 3 resources over standard input and output (STDIO). It holds mutation authority solely over registered discovery trees within the designated store path. It must never print diagnostic messages to standard output; all diagnostic logging must route exclusively to standard error to preserve JSON-RPC transport integrity.

Preserve caller-selected budgets and policy hyperparameters, including worker caps, beta exploitation targets, and probe limits. Distinguish between verified empirical replay scores, mathematical Pareto rewards, and unverified candidate policies.

## Architecture and Cleanup

Dependencies flow inward: core domain models and validation rules, evaluation algorithms, replay simulation and oracle contracts, optimizer policies, storage adapters, and finally MCP and agent configuration adapters. Keep transport protocols and MCP server specifics out of the core domain and evaluation layers.

Give each domain entity a clear invariant owner. `DiscoveryTree` owns topological integrity and must strictly enforce parent-child acyclicity via cycle detection. `TreeNode` owns depth and attempt indices. `Observation` owns execution success classifications and repairability predicates.

Assess brittleness during implementation, review, and refactoring. Type checking operates in Pyright strict mode without `Any` bypasses. Use explicit Pydantic v2 schemas and typed dictionaries. Normalize boundary inputs once at the MCP server tool boundary before passing models to internal engines.

Atomic file operations must be enforced in `JsonFileHistoryStore`. Paths must be sanitized against directory traversal attacks via strict root confinement checks. Retain historical trees safely on failure; transient replays must not corrupt saved tree topologies.

## Development

Use `uv` and Python 3.10 or higher for the pinned toolchain.

- `uv sync`: install and sync locked dependencies from `uv.lock`.
- `uv run pytest`: execute all 48 unit and integration tests.
- `uv run pyright`: execute cached strict static type analysis.
- `uv run python scripts/verify_mcp.py`: execute live STDIO MCP protocol handshake and all 11 tool calls.
- `uv run dream-rsi`: launch the MCP server over STDIO.

Use relevant checks for changes. Fast verification combines `uv run pyright` and `uv run pytest`. Full verification requires `uv run python scripts/verify_mcp.py`.

`data/trees/`, `.pytest_cache/`, `.venv/`, `.vscode/`, and `__pycache__/` are ignored outputs. Never commit runtime JSON tree logs, local editor settings, virtual environments, or credentials.

## Tool and Test Changes

For tool changes, start from the agent decision workflow: list history, inspect tree topology, record online attempts, run offline virtual replays, evaluate Pareto frontiers, and plan deterministic search grids. Return clean JSON strings containing status codes, structured payloads, and human-readable error descriptions.

For test changes, maintain three verification tiers:
1. Unit tests: model acyclicity, observation predicates, storage containment, and evaluator math.
2. Integration tests: closed-loop recursive self-improvement monotonicity across multiple generations.
3. Protocol tests: live subprocess STDIO client testing covering MCP initialization, resource reading, and tool invocation.

Use Conventional Commit subjects and pull request titles. Describe architectural modifications, metric guarantees, and verified test scopes concisely.