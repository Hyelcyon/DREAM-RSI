# Changelog

## [0.2.0] - 2026-10-10

### Features

- **benchmarks**: Implement 4 paper scientific discovery benchmarks:
  - Lasso Regularization Path with coordinate descent reference solver, KKT $10^{-6}$ tolerance verification, and geometric mean runtime metric $R_{\text{search}}$.
  - Sum-Difference sets with $\Gamma(A) = \frac{\log(|A+A|/|A|)}{\log(|A-A|/|A|)}$ and MSTD seed generator.
  - Circle Packing in a Unit Square with pairwise disjointness and boundary confinement validation.
  - Autocorrelation Inequalities with trapezoidal autoconvolution mass normalization and functional ratios $\Phi_1, \Phi_2, \Phi_3$.
  - Benchmark discovery tree generator for bootstrapping discovery trees.
- **optimizer**: Implement paper-exact `OptimalPolicy` matching Listing 2 with 5-step batch portfolio allocation, prefix trajectory ranking, and ancestor-conflict prevention.
- **optimizer**: Implement cross-cycle default beta adaptation with plateau detection and Pareto sweep adjustments.
- **core**: Implement `BranchTrajectory` tracking prefix history, prompt signals (`branch_promising`, `branch_failed_hard`, `probe_improved_vs_parent`, `probe_improved_vs_baseline`), and failure taxonomy.
- **replay**: Enhance `QuestionAPI` with prefix-only simulation, legal roots, opened branches, $O(1)$ child indexing, and dynamic batch reveals.
- **mcp**: Expand MCP server with 3 new tools (`dream_policy_select_beta`, `dream_benchmark_evaluate`, `dream_benchmark_create_tree`) and `dream://benchmarks/catalog` resource, totaling 11 tools and 3 resources.

### CI/CD

- **ci**: Add GitHub Actions CI workflow across Ubuntu, Windows, and macOS with Python 3.10 through 3.13.
- **release**: Add automated release publication workflow with verification gate and conventional changelog generation.
- **dependabot**: Add automated dependency updates for uv and GitHub Actions.

### Documentation

- **docs**: Update README, Korean translation, and MCP contracts specifications to reflect 11 tools and 3 resources.
- **badges**: Update test pass badge to 38 passed and MCP badge to 11 tools and 3 resources.

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