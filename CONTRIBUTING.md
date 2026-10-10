# Contributing to DREAM-RSI

DREAM-RSI welcomes focused bug fixes, mathematical policy optimizations, documentation improvements, and tests. For large architectural changes, explain the intended scope and link the relevant design discussion.

## Development Setup

DREAM-RSI uses `uv` with Python 3.10 or higher.

```bash
uv sync
uv run pytest
uv run pyright
uv run python scripts/verify_mcp.py
```

- `uv sync` installs and syncs dependencies from `uv.lock`.
- `uv run pytest` runs unit and integration test suites.
- `uv run pyright` runs strict static type checking.
- `uv run python scripts/verify_mcp.py` executes a live STDIO MCP protocol handshake and tool call sequence.

## Architecture and Repository Guidelines

Invariants and design rules are documented in [AGENTS.md](AGENTS.md):
- Keep transport protocols (MCP STDIO) isolated in the adapter layer.
- Core domain logic, simulation models, and storage adapters remain transport-agnostic.
- The simulation engine is strictly offline with zero external network access.
- All file mutations in `JsonFileHistoryStore` must enforce directory root confinement and atomic writes.

## Verification Tiers

Before submitting changes or opening a pull request, verify across three tiers:
1. **Static Analysis**: `uv run pyright` must pass with 0 errors in strict mode.
2. **Unit & Integration Tests**: `uv run pytest` must pass all test cases.
3. **Live Protocol Verification**: `uv run python scripts/verify_mcp.py` must pass the full 5-step handshake and tool execution.

## Commit Message Convention

Commits follow the Conventional Commits specification with lowercase imperative subjects:

```text
<type>(<scope>): <subject>

[optional body explaining rationale and problem context]

Verification: <verification commands executed>
```

- **Types**: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `build`, `chore`
- **Scopes**: `(core)`, `(replay)`, `(optimizer)`, `(storage)`, `(mcp)`, `(agent)`, `(docs)`
- **Subject**: Imperative mood without trailing period (e.g., `feat(mcp): add status resource endpoint`).
