# Deploying the MCP server

The server is plain Vercel Functions (no Next.js), deployed only from the CLI with a local build and
a prebuilt upload, so no Vercel build minutes are used and no preview builds exist. It has no
native modules: the bundle is pure JavaScript plus JSON data.

Everything below runs from the `mcp/` folder of the repository.

## 1. One-time project setup

1. In the existing Vercel team, create the project `nobrainer-tech-flow-mcp`. Do not connect Git.
   - Framework preset: Other. Node.js version: 22.x. Build machine: Standard (do not enable
     Enhanced, Turbo or elastic selection). Fluid compute: on.
   - Region `iad1` and `maxDuration` (10 s for `/api/mcp`) come from `vercel.json`.
2. Link the folder: `vercel link --yes --project nobrainer-tech-flow-mcp --scope <team-slug>`.
3. Set environment variables (Production). Generate secrets into a private pipe; never print them,
   never write them to files, and back each one up through the shared Bitwarden workflow first.

| Variable | Required | Value |
|---|---|---|
| `FLOW_TOKEN_KEYS` | yes, Sensitive | `<kid>:<base64 of 32 random bytes>`; first entry signs, all verify. Start with kid `1`. |
| `ALLOWED_HOSTS` | recommended | `nobrainer-tech-flow-mcp.vercel.app` (and any other alias). `mcp.nobrainer.tech`, `VERCEL_URL`, `VERCEL_BRANCH_URL` and `VERCEL_PROJECT_PRODUCTION_URL` are always allowed. |
| `FLOW_RATE_LIMIT_ID` | recommended | ID of the Firewall rate-limit rule for the per-contract limit (section 4). Unset: best-effort in-memory limit per instance. |
| `OPENAI_APPS_CHALLENGE` | for OpenAI review | The domain-verification token from the OpenAI portal; served at `/.well-known/openai-apps-challenge` (404 while unset). |
| `ALLOWED_ORIGINS` | no | Overrides the default `https://chatgpt.com,https://claude.ai,https://platform.openai.com`. Requests without `Origin` are always allowed. |
| `SPEND_WEBHOOK_SECRET` | for the spend guard, Sensitive | The secret Vercel shows when you save the Spend Management webhook. |
| `FLOW_PAUSE_TOKEN` | for the spend guard, Sensitive | A Vercel access token that can pause this project, scoped as narrowly as Vercel allows. |
| `FLOW_PROJECT_ID`, `FLOW_TEAM_ID` | for the spend guard | This project's ID and the team ID. |
| `SPEND_PAUSE_PERCENT` | no | Threshold that pauses the project; default `75`. |

Key generation example (the value goes straight into the CLI, never to the terminal):

```bash
node -e "process.stdout.write('1:' + require('crypto').randomBytes(32).toString('base64'))" \
  | vercel env add FLOW_TOKEN_KEYS production --sensitive
```

Bitwarden item names (owner rule): `nobrainer-tech-flow-mcp | Production | Vercel env | FLOW_TOKEN_KEYS kid 1`,
`... | SPEND_WEBHOOK_SECRET`, `... | FLOW_PAUSE_TOKEN`. Back up through the approved private pipe and
read the item back by UUID before relying on it.

## 2. Build, check, deploy

```bash
npm ci
npm test                    # type check, content pin, unit, protocol, security, budget
npm run conformance         # official MCP conformance suite with the documented baseline
vercel pull --yes --environment=production   # project settings; Sensitive values are not downloaded
rm -f .vercel/.env.*.local                   # keep no pulled env file on disk
vercel build --prod
npm run check:output        # every function nodejs22.x and x86_64, no .node files, no darwin paths
npm run check:bundle        # loads mcp.func exactly as uploaded and answers initialize, tools/list, two tools
vercel deploy --prebuilt --prod --skip-domain
npm run smoke -- https://<deployment-url>/mcp     # see the note on Deployment Protection
vercel promote <deployment-url>
npm run smoke -- https://mcp.nobrainer.tech/mcp --challenge "<OpenAI token, once set>"
```

- The functions export `config = { architecture: "x86_64" }`, because `vercel build` otherwise uses
  the build machine's architecture (arm64 on Apple silicon). `check:output` fails if any function is
  not x86_64.
- No `deploymentId` or skew protection work is needed: there is no Next.js.
- Deployment Protection: if the team protects generated deployment URLs, the smoke test on the
  deployment URL gets a 401 from Vercel (the server itself never returns 401). Then either use a
  Protection Bypass for Automation secret in a header, or promote first and smoke the custom domain,
  rolling back on failure.
- Rollback: `vercel rollback` to the previous production deployment, then the live smoke test.
- Deploy verified change sets only, not to try an idea.

## 3. Domain (owner step, production DNS change)

1. Add `mcp.nobrainer.tech` to the project and copy the CNAME value Vercel shows.
2. In the MyDevil DNS zone for `nobrainer.tech`, create an explicit `CNAME` record `mcp` with that
   value (an explicit record takes precedence over the wildcard).
3. Read back: `dig +short CNAME mcp.nobrainer.tech` shows the Vercel value; Vercel shows the domain as
   valid with a certificate; `curl -sI https://mcp.nobrainer.tech/` returns 200 from Vercel.

`nobrainer.tech` sends HSTS with `includeSubDomains; preload`, so do not share the subdomain until
the certificate is active.

## 4. Rate limiting

1. WAF rules (Firewall > Rules, before the function runs; fixed window, action 429):
   - Rule A: Anthropic egress `160.79.104.0/21` (and OpenAI egress ranges if published): 3,000
     requests per 60 s per IP.
   - Rule B: everything else: 120 requests per 60 s per IP.
2. Per-contract limit: a rate-limit rule whose condition is the `@vercel/firewall` rule ID you set in
   `FLOW_RATE_LIMIT_ID`, 60 requests per 600 s. The function passes `contract:<digest>` as the key,
   so many users behind one platform IP are limited per task, not together. If the ID is not found
   or the check fails, the function falls back to an in-memory limit per instance. Verify that custom
   keys work on the plan before relying on it.
3. Request caps in code: 32 KiB body, 10 DoD items, 4 evidence records, JSON depth 10, field limits.

## 5. Spend guard

1. Team settings > Billing > Spend Management: set the on-demand budget (owner chooses the ceiling)
   and add the webhook URL `https://mcp.nobrainer.tech/api/spend-hook`. Save, copy the secret into
   `SPEND_WEBHOOK_SECRET`.
2. The hook verifies `x-vercel-signature` (HMAC-SHA1 of the raw body). At `SPEND_PAUSE_PERCENT`
   (default 75 %) of the budget it calls `POST /v1/projects/{FLOW_PROJECT_ID}/pause?teamId=...`,
   which pauses only this project. Vercel checks spend every few minutes, so the pause can lag.
3. Keep **Pause Production Deployments** as the team-wide last resort at the owner's ceiling;
   it pauses every project in the team.
4. Resume after a pause: dashboard or `POST /v1/projects/{id}/unpause`.
5. Test once with a signed request against a throwaway project before relying on it.

## 6. Keeping the advisor current

The benchmark snapshot expires 14 days after its `fetched_at` (the website's own rule). After that,
`recommend_flow_model` returns `expired: true` and an empty shortlist. Every deploy should carry a
snapshot fetched within the last 14 days: `npm run refresh:benchmark -- --source <website>/public_html/ai/benchmark`,
`npm test`, commit, then build and deploy as in section 2. The snapshot in this release was fetched
2026-10-23 and expires 2026-11-06. The public task enum lists only tasks with measurements;
the legacy `coding` alias is accepted in any case and returns `task: "terminal-coding"` with
a Terminal-Bench shortlist. The smoke test checks this mapping through the SDK in both protocol eras.

## 7. After the first deploy

- Run MCP Inspector against production and call each tool with valid and invalid input.
- Connect each client from the README and record the result there.
- Rescan in the OpenAI portal after each deploy that changes tools.

## 8. Link preview card

`public/media/og-card.png` (1200x630) is the image in the `og:image` and `twitter:image` tags of both
landing pages. It is committed, not built, and Vercel serves it as a static file from `public/`. To
change it, edit `scripts/render-og-card.mjs`, run `node scripts/render-og-card.mjs` (needs Chrome or
Chromium; set `CHROME_BIN` if it is not in a standard place) and commit the PNG. X, Facebook and
LinkedIn cache previews by image URL, so if the card changes after the link was shared, give the file
a new name and update the tags.

After a deploy: `curl -s https://mcp.nobrainer.tech/ | grep -E 'og:|twitter:'` (and the same for
`/pl/`), `curl -sI https://mcp.nobrainer.tech/media/og-card.png` (200, `content-type: image/png`),
then refresh the cached preview in the Facebook Sharing Debugger and the LinkedIn Post Inspector and
paste the URL into an X draft post to see the card.
