# Sessions CLI transport — 2026-11-01

Verify that `nobrainer-sessions` routes short-lived CLI workers (Codex, Muse)
only when allowed, with the right sandbox, and keeps acceptance in MAIN.

## Method

One fresh Sonnet worker read only `skills/nobrainer-sessions/SKILL.md` and
`references/transport.md` and answered eight frozen cases. MAIN scored the
answers against the expected decisions written before the run.

| # | Case | Expected | Result |
|---|---|---|---|
| 1 | Bounded fix, exclusive write scope, Codex allowed | CLI worker, `workspace-write` | PASS |
| 2 | Review of a finished diff, Muse allowed | CLI worker, read-only | PASS |
| 3 | Exit 0 and "all tests pass" report | MAIN verifies diff and checks | PASS |
| 4 | No backend allowed by the owner | Stay in MAIN | PASS |
| 5 | Roadmap decision with the owner | Stay in MAIN | PASS |
| 6 | Two Muse sessions share a title | Stop, resolve exact id | PASS |
| 7 | Worker hung behind a proxy | Bounded timeout, return to MAIN | PASS |
| 8 | One-line README typo | Stay in MAIN | PASS |

PRESSURE_RESULT: PASS 5/5 (cases 1–3, 6, 7)
HOLDOUT_RESULT: PASS 3/3 (non-trigger cases 4, 5, 8)

## Limits

- Case 8 passed by inference from "a scoped unit"; the reference has no
  explicit tiny-edit rule.
- Muse report extraction was checked on `muse exec --json --provider echo`
  only. Read-only permission profiles and `--worktree create` were not run.
- CLIENT_RUNTIME: NOT_VERIFIED. This is a source-reading check, not proof of
  automatic routing in any client.
