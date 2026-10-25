# Privacy Policy: NoBrainer Tech Flow MCP server

Version 1.0. Effective date: 21 October 2026.
Published at https://nobrainer.tech/flow/privacy/

## 1. Who is responsible

The data controller and operator is mastalerz.it Arkadiusz Mastalerz, a Polish sole trader registered in CEIDG, ul. Krasnowolska 18E, 02-849 Warszawa, Poland. Contact: hello@nobrainer.tech.

## 2. What this service is

The NoBrainer Tech Flow MCP server (the server at mcp.nobrainer.tech; endpoint https://mcp.nobrainer.tech/mcp) is a free, public, stateless remote MCP server. AI clients such as Codex, Claude Code or Cursor call it to get guidance for the NoBrainer Tech Flow method.

- No accounts, no sign-in, no OAuth.
- No stored task content.
- No AI model inference on the server.
- No outbound requests to third parties from tool handlers.
- No paid tier.

It offers six read-only tools: start_flow_task, get_flow_step, check_flow_evidence, check_flow_done, draft_flow_handoff and recommend_flow_model (the model advisor).

## 3. Personal data and other data we process

### 3.1 Tool inputs (processed in memory only)

- Flow tools: task outcome, definition-of-done text, non-goals, command text, command output excerpts, file paths and SHA-256 hashes, URLs and HTTP status codes, notes.
- Model advisor: a task type, a list of AI providers, models or client apps you can use (for example Codex, Claude Code, Cursor), and an optional priority (quality, balanced or efficient) and role.

This data is processed in memory to compute the response and is discarded at the end of the request. It is not written to logs, not stored, not used to build profiles. Responses never echo free text.

We do not want credentials. Inputs that look like secrets (API keys, private keys, passwords) are rejected without being stored. Please do not send secrets or personal data in any input. These tools do not need them.

### 3.2 Contract token and receipt

The server returns a contract token or receipt to your client. It contains only truncated hashes, enum values, counters and timestamps, signed with HMAC. It contains no plaintext from your inputs. The server keeps no copy. Tokens expire after 30 days of inactivity and at most 90 days after creation.

### 3.3 Technical data

When you call the server, the hosting provider processes your IP address, user agent, request time, path and HTTP status. This is used to deliver the request, for security (firewall) and for rate limiting. Rate limiting is applied per IP address and per contract, using the contract's pseudonymous hash digest as the key.

Many users of one AI platform share that platform's IP addresses, so the IP address you see on our side is often the platform's, not yours. This depends on your client.

### 3.4 Application logs

The application writes one content-free line per request with: timestamp, route, RPC method, tool name, result code, duration, response size, MCP protocol version and the client application name as reported by the client (for example "claude-code", truncated to 40 characters).

The application never logs request bodies, tool arguments, tokens, IP addresses or user agents.

## 4. Purposes and legal basis

| Purpose | Data |
|---|---|
| Provide the tool results you request | Tool inputs (in memory) |
| Protect the service: security, rate limiting, abuse prevention | Technical data, contract hash digest |
| Operate and debug the service | Content-free application logs |

Legal basis: GDPR art. 6(1)(f), our legitimate interest in providing and securing a service that you chose to call. We process only the minimum needed for these purposes.

## 5. Recipients and transfers

- Vercel Inc. (United States) hosts the server and acts as our processor. Because Vercel is in the USA, data is transferred there under the transfer mechanisms in Vercel's data processing addendum.
- Your AI client provider (for example OpenAI, Anthropic, Google, GitHub, Cursor) sends the request to us and receives the response under its own privacy policy. It is not a recipient chosen by us, and we do not control its handling of your data.

We do not sell data and do not share it with anyone else. No analytics, no cookies, no tracking, no advertising, no profiling, no model training, no log drains.

## 6. Retention

| Data | Retention |
|---|---|
| Tool inputs | None beyond the request |
| Contract token or receipt | Not kept by us; held by your client; expires as in 3.2 |
| Application logs and Vercel runtime logs (Vercel's request entries include path, status, host, region and user agent) | 1 day: the Vercel Pro runtime log retention (https://vercel.com/docs/logs/runtime, checked 2026-10-20). Longer retention requires Observability Plus, which this service does not use. |
| Hosting-provider firewall and security records | Per Vercel's own retention, which Vercel sets and we do not control |

## 7. Model advisor

The advisor ranks models from a pinned snapshot of the public NoBrainer AI benchmark (https://nobrainer.tech/ai/benchmark/), which includes third-party benchmark data under its own licences. Its inputs are processed in memory only and discarded after the response. Its output is informational, may be outdated (the snapshot date is shown) and is not a guarantee of model quality or price.

## 8. Your controls and rights

- Stop calling the server or remove it from your client at any time.
- Do not include secrets or personal data in inputs.
- Nothing is stored, so there is nothing to export or delete. You can still send a request for access, rectification, erasure, restriction or objection, or a complaint, to hello@nobrainer.tech. We will answer it.
- You have the right to lodge a complaint with the Polish supervisory authority: Prezes Urzedu Ochrony Danych Osobowych (UODO), or with the authority in your own EU country.

Providing technical data is necessary to use the server. We do not make automated decisions that have legal or similarly significant effects on you.

## 9. Children

The service is a developer tool and is not directed at children under 16 in the EU (the GDPR default age in article 8, which Poland did not lower), or under 13 elsewhere.

## 10. Changes

The version and effective date are at the top of this page. We announce material changes on this page and in the release notes.
