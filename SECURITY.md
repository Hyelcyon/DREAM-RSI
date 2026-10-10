# Security Policy

## Supported versions

Security fixes are provided for the latest published version of Dream-RSI. Upgrade to the latest release before reporting a problem that may already have been resolved.

## Reporting a vulnerability

Do not disclose vulnerabilities, proof-of-concept exploits, credentials, or private exploration tree data in a public issue.

Use **Report a vulnerability** in the repository's **Security** tab to submit the report privately. Do not open a public issue to request a private contact channel.

Include the affected Dream-RSI version, operating system, Python runtime version, impact, reproduction conditions, and any suggested mitigation in the private report. Remove credentials, proprietary code snippets, private task observations, and unrelated local filesystem paths from logs or examples.

The maintainer will acknowledge the report, assess its scope, and coordinate remediation and disclosure timing with the reporter. Please allow time for environment-dependent behavior to be reproduced safely.

## Security boundary

Dream-RSI operates as a local subprocess communicating via JSON-RPC over standard input and output (STDIO) through the Model Context Protocol (MCP). It does not bind to network interfaces, open remote listening sockets, or expose HTTP endpoints. This execution model inherits the operating system permissions of the invoking agent host process (such as Claude, Antigravity, or Codex). It is not an OS sandbox and does not protect against malicious processes already running under the same user identity.

Storage operations are strictly confined within the designated tree store root, configured through `DREAM_RSI_STORE_DIR` or defaulting to `data/trees`. The storage engine enforces path containment by rejecting directory traversal sequences and verifying that all resolved destinations remain under the designated base directory. Attempted escapes outside this root raise explicit `PermissionError` or `ValueError` exceptions. File updates are written atomically to prevent partial writes and corruption.

The simulation and policy optimization engines run completely offline without external network egress. Dream-RSI makes no remote API calls, transmits no telemetry, and contacts no cloud endpoints. Discovery trees, score records, and trajectory curves remain exclusively on the local machine.

Dream-RSI evaluates pre-recorded observations and manages search policies; it does not compile or execute untrusted code strings passed through tool arguments. Code verification authority belongs entirely to the host agent and its execution environment.