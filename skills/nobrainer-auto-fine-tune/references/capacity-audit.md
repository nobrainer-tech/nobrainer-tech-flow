# Client capacity and update audit

Use this on first project setup, after a client/model update, or when a
measured task repeatedly hits a context or worker ceiling. Start read-only.

## Separate four evidence layers

Record the running client/version, selected MAIN model and effort, effective
profile/provider, and source of each value. For context, keep
`CONFIGURED_LIMIT`, `CATALOG_ADVERTISED_LIMIT`,
`PROVIDER_DOCUMENTED_LIMIT` and `RUNTIME_OBSERVED` separate. A larger model
card or API window does not prove that the client grants it. Do not promote
a claimed million-token window or a proposed 872,000-token setting into a
verified runtime fact.

For workers, record native spawn support, exact model IDs, per-worker effort
support, configured concurrency, actual successful concurrent launches,
current running workers and practical integration cost. A config value such
as 15 is a ceiling, not observed capacity. Use ordinary useful work to test
capacity; do not create filler probes or exceed host restrictions.

Check whether the running client has an eligible update through its native
version/status channel when available. Treat `AVAILABLE`, `UP_TO_DATE`,
`BUSY`, `UNAVAILABLE` and `UNKNOWN` as different outcomes. Do not equate
Flow's daily release check with a client-app update. Never download or restart
a user's app from a read-only check.

## Client adapters

- **Codex:** inspect the selected profile as well as base config, local model
  catalog, effective session status, worker configuration and native app update
  status. The optional [NoBrainer Codex](https://github.com/nobrainer-tech/nobrainer-codex)
  installer can provide a Codex-specific `install.py --check` preflight.
  It is a separate product; its planned setting is not runtime proof.
- **Claude Code:** inspect available subagent models, effort and capacity from
  the active client and its current settings. A named model file or allowlist
  is not proof that the worker actually ran on that model.
- **OpenCode and other clients:** inspect their effective model/provider
  selection, agents and plugin settings through supported native means. A
  lightweight default or title-generation model is not automatically an
  eligible task worker.

Recommend a larger context or worker ceiling only when the active model,
provider and client all support the exact value and a real task benefits.
Prepare the smallest settings diff and rollback. Apply only within the
owner's authorization and client-supported mechanism, then read back the
saved value, selected MAIN model/effort and a representative runtime task.
If effective settings or actual runtime capacity cannot be observed, report
`CONFIGURED_ONLY` or `UNKNOWN` rather than claiming improvement.
