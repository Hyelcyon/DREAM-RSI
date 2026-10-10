# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-10-10

### Features

- **core**: Implement Directed Acyclic Graph (DAG) `DiscoveryTree` and `TreeNode` models with topological cycle detection.
- **core**: Implement `TreeEvaluator` for oracle contracts, empirical scores, and Pareto reward metrics.
- **storage**: Implement `JsonFileHistoryStore` with atomic file persistence and strict path containment against directory traversal.
- **replay**: Implement offline `ReplaySimulator` and `QuestionPrefix` virtual execution environments with zero external LLM token expenditure.
- **optimizer**: Implement `DynamicPortfolioPolicy` balancing exploration width $W$ and depth $R$ via $\beta$ exploitation parameters.
- **optimizer**: Implement `PolicyOptimizer` for beta-sweep Pareto frontier calculation and candidate policy comparison.
- **mcp**: Expose 8 Model Context Protocol tools and 2 resources over STDIO JSON-RPC.
- **agent**: Expose agent configuration generators for Claude Code, Google Antigravity, and OpenAI Codex.
- **skills**: Author agent skills for `recursive-self-improvement` and `rsi-tool-design`.

### Documentation

- Add comprehensive multilingual READMEs (English, Korean, Japanese, Chinese).
- Add architecture diagram `docs/architecture.mermaid` and MCP contracts specification `docs/mcp-contracts.md`.
- Add `CONTRIBUTING.md`, `SECURITY.md`, and `AGENTS.md` guidelines.