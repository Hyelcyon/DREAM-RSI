---
name: rsi-tool-design
description: Design or change DREAM-RSI exploration tools, MCP contracts, replay simulation primitives, and storage invariants.
metadata:
  version: "1.0"
---

# DREAM-RSI Tool Design

Use this skill when introducing, refactoring, or extending DREAM-RSI MCP tools, storage backends, or evaluation primitives.

## Invariant Ownership

1. **Topological Integrity**:
   - `DiscoveryTree` owns the Directed Acyclic Graph structure.
   - Cycle detection must execute before mutating tree state on disk.
   - Trees must always originate from a single valid root node (`parent_id = None`).

2. **Boundary Normalization**:
   - Parse and validate incoming MCP arguments at the server boundary using explicit Pydantic schemas.
   - Core engines must never accept arbitrary untyped dictionaries.

3. **Offline Safety and Isolation**:
   - All replay simulation logic must remain strictly offline. Never introduce external network calls or remote dependencies.
   - File persistence in `JsonFileHistoryStore` must enforce strict path root confinement to prevent directory traversal vulnerabilities.
   - Storage writes must be atomic (write to temporary file, then atomic rename).

4. **Protocol Transport**:
   - Keep stdout clean for JSON-RPC messages. All logging, telemetry, and debugging must go to stderr.
