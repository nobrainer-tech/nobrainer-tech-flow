# NoBrainer Tech Flow MCP server

A free, public, stateless remote MCP server for [nobrainer-tech-flow](https://github.com/nobrainer-tech/nobrainer-tech-flow).
It gives an AI agent one task contract, one evidence check and one done gate, the same in every MCP
client, plus guidance quoted from the pinned Flow release and a model advisor based on the
[NoBrainer AI benchmark](https://nobrainer.tech/ai/benchmark/).

- Endpoint: `https://mcp.nobrainer.tech/mcp`, Streamable HTTP, no sign-in.
- Stores nothing, runs no AI model, makes no outbound requests from tools.
- Protocol: MCP `2026-07-28` (stateless, `server/discover`) and 2025-era clients (`2025-11-25`,
  `2025-06-18`, ...) through a stateless JSON-only fallback on the same endpoint.

## Tools

| Tool | What it does |
|---|---|
| `start_flow_task` | Checks the outcome and definition of done (DoD), picks the quick or full path, lints vague items, routes Flow modules and owner gates, and returns item IDs (`AC01`...) with an HMAC-signed contract token to save in your goal file. |
| `get_flow_step` | Up to six rules for one stage, event or module, quoted verbatim from the pinned Flow release, with the source anchor. Works without a token. With a contract token and `event: "resume"` it returns two rules plus `goal_block`, ready to paste into the goal file: `GOAL_ID`, one DoD row per item (`- AC01 test, local: ACCEPTED`; statuses `OPEN`, `ACCEPTED`, `FAILED`, `STALE`), `STATUS`, `CHECKPOINT`, `NEXT_SAFE_ACTION` and the renewed token as `FLOW_CONTRACT`. `OUTCOME` and `NON_GOALS` stay placeholders because the server never repeats your text. |
| `check_flow_evidence` | Checks one to four evidence records: exit codes, the test-runner summary (pytest, unittest, node:test, Vitest, Jest, Mocha, Playwright, Go, cargo, RSpec, PHPUnit, dotnet), claimed counts, evidence level, URL host and status, file hashes. Marks earlier test results stale when a registered file changes, and returns `REPEATED_DEFECT` after a second failure. |
| `check_flow_done` | `DONE` only when every item has accepted, current evidence; `DONE_WITH_GAPS` when the rest are listed as unchecked with a reason; otherwise `NOT_DONE` with the exact missing items. |
| `draft_flow_handoff` | A final-report skeleton built only from the done receipt. |
| `recommend_flow_model` | A top-3 model shortlist for a data-backed task type (`orchestration`, `instructions`, `frontend`, `research`, `writing`, `terminal-coding`) from a pinned, dated benchmark snapshot, filtered by the providers, models or client apps you have (`have`), with an optional priority (quality, balanced, efficient) and role. The legacy `coding` alias is accepted case-insensitively (for example, `Coding`) and returns `task: "terminal-coding"` with a Terminal-Bench shortlist. Never invents scores and says when data is missing. Like the website, it refuses once the snapshot is 14 days past its fetch time (`expired: true`, `expires` date in every response). |

All six tools are read-only (`readOnlyHint: true`, `openWorldHint: false`). Results are one compact
JSON text block. Responses never echo your free text: only IDs, enums, digests and canonical Flow text.

The server checks consistency, not truth: it cannot see your machine, and evidence is reported by
the agent. Every handoff says so.

## Install

Server name: `nobrainer-tech-flow`. To try a local build instead, replace the URL with
`http://127.0.0.1:8787/mcp` (see "Run locally").

| Client | Status |
|---|---|
| Claude Code | Verified 2026-10-20 against the local server (Claude Code 2.1.303): connected over MCP 2026-07-28 and listed the six tools. |
| Codex CLI | Verified 2026-10-20 against the local server (codex-cli 0.163.0): connected over MCP 2025-06-18 and listed the six tools through the app server. |
| OpenCode | Verified 2026-10-23 against the public endpoint (OpenCode 2.0.32): `opencode mcp list` shows it connected. |
| Claude.ai / Claude Desktop, ChatGPT, Cursor, VS Code / Copilot, Gemini CLI, Cline, Windsurf, Zed | Not verified yet. Snippets follow each client's documentation. |

Claude Code:

```bash
claude mcp add --transport http nobrainer-tech-flow https://mcp.nobrainer.tech/mcp
# for all projects of this user:
claude mcp add --transport http --scope user nobrainer-tech-flow https://mcp.nobrainer.tech/mcp
```

Project file `.mcp.json`:

```json
{"mcpServers": {"nobrainer-tech-flow": {"type": "http", "url": "https://mcp.nobrainer.tech/mcp"}}}
```

Claude.ai and Claude Desktop (not verified): Customize > Connectors > Add > Add custom connector,
name `NoBrainer Tech Flow`, URL `https://mcp.nobrainer.tech/mcp`, No sign-in. On Team and Enterprise an
Owner adds it under Organization settings > Connectors first.

Codex CLI and IDE, `~/.codex/config.toml` (or `codex mcp add nobrainer-tech-flow --url https://mcp.nobrainer.tech/mcp`):

```toml
[mcp_servers.nobrainer-tech-flow]
url = "https://mcp.nobrainer.tech/mcp"
```

ChatGPT (not verified): open ChatGPT Plugins (`chatgpt.com/plugins`), select + > Add custom MCP
server, name it `NoBrainer Tech Flow`, enter the URL under Connection, choose no authentication and
select Create as a plugin. Workspace policies decide who can add custom MCP servers.

Cursor, `.cursor/mcp.json` or `~/.cursor/mcp.json` (not verified):

```json
{"mcpServers": {"nobrainer-tech-flow": {"url": "https://mcp.nobrainer.tech/mcp"}}}
```

VS Code / GitHub Copilot, `.vscode/mcp.json` (not verified):

```json
{"servers": {"nobrainer-tech-flow": {"type": "http", "url": "https://mcp.nobrainer.tech/mcp"}}}
```

Gemini CLI (not verified):

```bash
gemini mcp add --transport http nobrainer-tech-flow https://mcp.nobrainer.tech/mcp
```

or `settings.json`: `{"mcpServers": {"nobrainer-tech-flow": {"httpUrl": "https://mcp.nobrainer.tech/mcp"}}}`

Cline, `cline_mcp_settings.json` (not verified; set `type`, because a missing type means legacy SSE):

```json
{"mcpServers": {"nobrainer-tech-flow": {"type": "streamableHttp", "url": "https://mcp.nobrainer.tech/mcp"}}}
```

OpenCode (verified 2026-10-23 against the public endpoint, OpenCode 2.0.32: `opencode mcp list` shows it connected):

```bash
opencode mcp add nobrainer-tech-flow --url https://mcp.nobrainer.tech/mcp --global
```

Windsurf, `~/.codeium/windsurf/mcp_config.json`, then Refresh in Manage MCPs (not verified):

```json
{"mcpServers": {"nobrainer-tech-flow": {"serverUrl": "https://mcp.nobrainer.tech/mcp"}}}
```

Zed, Settings > AI > MCP Servers > Add Remote Server, or `settings.json` (not verified):

```json
{"context_servers": {"nobrainer-tech-flow": {"url": "https://mcp.nobrainer.tech/mcp"}}}
```

### Using it with local Flow skills

The server leads the gates; guidance already in context leads the guidance. If Flow skills are
installed locally, keep using them for stage guidance and call `get_flow_step` only for cards you
have not loaded. Pass your local Flow version as `local_flow`; when it is older than the server's,
the response says that gate rules follow the server's version.

In repository work, save the contract token in the Flow goal file as `FLOW_CONTRACT: nbf1...` so
another session or client can continue. To resume, call `get_flow_step` with that token and
`event: "resume"`: paste the returned `goal_block` into the goal file, fill in `OUTCOME` and
`NON_GOALS` yourself, and continue from `NEXT_SAFE_ACTION`. Its `FLOW_CONTRACT` line is the renewed
token. Each `check_flow_evidence` call or resume renews a token for 30 days, up to 90 days after
`start_flow_task`.

## Run locally

Node.js 22.18 or newer (TypeScript runs directly through Node's type stripping).

```bash
cd mcp
npm ci
npm run serve            # http://127.0.0.1:8787/mcp, loopback only, ephemeral signing key
npm test                 # type check, content pin, unit, protocol, security and budget tests
npm run conformance      # official MCP conformance suite (2025-11-25) with test/conformance-baseline.yml
npm run smoke -- http://127.0.0.1:8787/mcp
npm run transcripts      # rewrites docs/review/test-cases.md
npm run transcripts -- --in-memory  # SDK tool calls without an HTTP listener; transport is recorded
npm run plugin           # dist/nobrainer-tech-flow-<version>.zip for the OpenAI portal
```

Without `FLOW_TOKEN_KEYS`, the local server signs with a random key per start, so tokens do not
survive a restart. On Vercel the key is required.

## How it is built

```text
api/mcp.js          Vercel Function; logic compiled from src/ into dist/ by `npm run build`
src/rpcguard.ts     fixed-text answers for unknown tool/prompt/resource names, protocol error rewriting
src/http.ts         POST only, 32 KiB body cap, Host and Origin checks, JSON depth limit, one
                    content-free log line; 2026-07-28 traffic -> SDK handler (JSON responses),
                    2025-era traffic -> fresh stateless transport with JSON responses
src/server.ts       six tools, prompt `flow`, resource template `flow://card/{id}`, instructions
src/token.ts        176-byte max binary token, HMAC-SHA-256 (128-bit tag), key ring, expiry
src/evidence/       runner parsers, verdicts, staleness, failure budget, secret screening
src/rules/          levels, quick/full path, lint, module routing, owner gates
src/advisor/        model advisor over data/benchmark/snapshot.json
content/            SOURCE.json pin (tag, commit, file hashes) and cards.yaml
src/generated/      cards.json built by scripts/build-content.ts from the git tag
plugin/             OpenAI submission manifests (plugin.json, mcp.json)
```

Runtime dependencies: `@modelcontextprotocol/server` 2.3.1, `zod` 4.6.7, `@vercel/firewall` 1.2.6.
The spec proposed `mcp-handler`; it is a thin wrapper over the SDK's own `createMcpHandler`, so the
server uses the SDK directly (one dependency fewer, same dual-era behaviour).

### Updating Flow guidance

The module list comes from the release: `scripts/build-content.ts` enumerates `skills/*/SKILL.md` at
the pinned tag. A released module without a `cards.yaml` entry gets a description-only card and a
warning; a `cards.yaml` module entry that the release no longer has fails the build (this is how
a rename such as `nobrainer-codex-context` -> `nobrainer-context` surfaces). To move to a new
release: update `content/SOURCE.json` (tag, commit, hashes), fix `cards.yaml`, run
`npm run build:content` and `npm test`, then deploy.

### Updating the benchmark snapshot

`npm run refresh:benchmark -- --source <website>/public_html/ai/benchmark` regenerates
`data/benchmark/snapshot.json` and `SOURCE.json` deterministically. The website rule applies: a snapshot expires 14 days after its fetch time, so refresh and redeploy at least every 14 days or the advisor answers `expired: true` with an empty shortlist. See `data/benchmark/NOTICE.md`
for provenance and third-party licences.

## Documents

- [Deployment](docs/DEPLOY.md): build, checks, environment variables, rate limits, spend guard.
- [Security](docs/SECURITY.md): threat model and controls.
- [Privacy policy](docs/PRIVACY.md) and [terms](docs/TERMS.md), published at
  `https://nobrainer.tech/flow/privacy/` and `https://nobrainer.tech/flow/terms/`.
- [Review test cases](docs/review/test-cases.md) and [demo recording script](docs/review/demo-script.md).

Source code: MIT, see the repository [LICENSE](../LICENSE).
