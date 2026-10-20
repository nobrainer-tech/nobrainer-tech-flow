# Security model

Report a vulnerability through the repository's [security policy](../../SECURITY.md).

## What the server is

A public, unauthenticated, stateless MCP server. It stores nothing, runs no model, executes no
command and makes no outbound request from any tool. The only outbound call in the code is the
optional Spend Management hook (`src/spend.ts`), which pauses this project and is not reachable from
MCP traffic.

## Threats and controls

| Threat | Control | Test |
|---|---|---|
| A model claims done without proof | Done gate, kind and level rules, test-summary parsing, count and exit consistency, staleness after a file change, failure budget | `test/unit/evidence.test.ts`, `test/protocol/security.test.ts` |
| Forged or edited token | HMAC-SHA-256 (128-bit tag) over the prefix and payload, constant-time compare, separate `nbf1`/`nbr1` prefixes, key ring with retirement | `test/unit/token.test.ts` (every single-bit flip), wire tests with a foreign key and an expired token |
| Secret leakage | Every string input is screened before any other processing; a hit rejects the call and names only the field; responses never echo free text; logs hold no content | `test/unit/secrets.test.ts`, wire test with a token in evidence, sentinel test over all inputs |
| Reflected prompt injection | Responses contain only item IDs, enums, digests, numbers and canonical Flow text. Unknown tool, prompt and resource names are answered before the SDK with fixed text; every SDK protocol error is rewritten to fixed text per code; the `flow` prompt takes no arguments; oversized JSON-RPC ids and batches are refused | sentinel test (all six tools, logs and console), `test/protocol/regressions.test.ts` |
| Caller text in logs | Log fields hold canonical method and tool names or a fixed marker (`other`, `unknown`, `redacted`); protocol versions must look like dates | `test/protocol/regressions.test.ts` |
| Flooding and cost abuse | WAF per-IP rules, per-contract limit, 32 KiB body cap, JSON depth limit, field limits, 10 s `maxDuration`, project-level spend pause | `test/protocol/protocol.test.ts` (413/415/400), rate-limit wire test, `test/unit/spend.test.ts` |
| Long-held connections | `subscriptions/listen` is refused at once (no SSE streams); responses are single JSON objects in both protocol eras | protocol tests |
| DNS rebinding | `Origin` must be absent or allow-listed (403 otherwise); `Host` must be the production host or the project's Vercel hosts; the local server accepts loopback only | protocol tests, official conformance `dns-rebinding-protection` |
| SSRF | No outbound requests from handlers | handler test with global `fetch` stubbed to throw |
| Supply chain | Three runtime dependencies, exact pins, lockfile, `npm ci`, `npm audit signatures` in CI | CI job `mcp-server` |
| Key compromise | Remove the kid from `FLOW_TOKEN_KEYS`: its tokens return `TOKEN_KEY_RETIRED`; rotate every 90 days | token tests |

## Honest limits

- The evidence text comes from the model. The HMAC proves that each verdict came from the server for
  the inputs it received, not that the inputs are true.
- A client can resend an older token that predates a change and so avoid a `STALE` mark. The handoff
  shows the contract and evidence digests so a person can compare.
- The file registry holds eight paths; a change to an evicted path is not detected.
- The change epoch caps at 255 changes per contract.
- Without `FLOW_RATE_LIMIT_ID`, the per-contract limit is per function instance.
- Secret screening is pattern-based; it lowers risk, it cannot catch every secret.

## Logging

One line per request: timestamp, route, HTTP status, RPC method, tool, result code, duration,
response size, protocol version, client name (from `clientInfo`, cut to 40 characters) and, for a
rejected `Origin`, its host. Never: request bodies, tool arguments, tokens, IP addresses, user agents.
