# AI-native SDLC playbook: gap map — 2026-11-02

Source: Anthropic, "The AI-native SDLC playbook" (claude.com/resources/articles/the-ai-native-sdlc-playbook).
Baseline: nobrainer-tech-flow v2.9.3 plus the Sessions transport branch.
Method: one fresh reader mapped every play to the skill that owns it, with file
evidence, before any change. The "Fix" column names the change made in v2.10.0.

| Play | Status at 2.9.3 | Flow owner | Flow equivalent | Fix in 2.10.0 |
|---|---|---|---|---|
| Plan: capture as `intent.md` | PARTIAL | `nobrainer-tech-flow` BUDDY, `idea-to-delivery.md` | scope contract, ISSUE brief | intent record step with Problem, Proposed outcome, Affected users and systems, Constraints, Open questions |
| Design: `spec.md`, policy owners, go/no-go | PARTIAL | `nobrainer-spec-driven-development` | spec, AC ledger, DEC table, approval hash | `INTENT_REF` and a policy-review table in the spec template |
| Build: plan mode and `plan.md` | PARTIAL | `nobrainer-tech-flow` scope block | Outcome…Done clean, canonical TODO | `Risks:` field in the scope block |
| Build: auto mode once guardrails mature | PARTIAL | `autopilot.md` | AUTOPILOT | autonomy tiers by environment in `delivery.md` |
| Build: `CLAUDE.md` shape | PARTIAL | `nobrainer-context` | inspect/consolidate | instruction-file content checklist in `consolidate.md` |
| Build: skills as institutional knowledge | COVERED | portfolio, `correction-hooks.md` | persistence gate | — |
| Build: hooks as build-time guardrails | PARTIAL | `flow_guard.py` (Bash only, ask only) | seatbelt guards | Edit/Write guard for protected paths, secret-looking content and test files during a fix |
| Build: parallel sessions and subagents | COVERED | `worktrees.md`, `delivery.md`, Review, Research | coordinated team execution | — |
| Test: one feedback command | PARTIAL | `nobrainer-build` focused proof | verifier | named in the instruction-file checklist |
| Test: commands with healthy output | MISSING | — | — | instruction-file checklist |
| Test: quantifiable done criteria | COVERED | DoD, `start_flow_task` lint | AC IDs, contract token | — |
| Test: failing test first, no test edits during fix | PARTIAL | `nobrainer-build` FAILING_PROOF_BEFORE | — | fix-mode guard on test paths |
| Test: browser loop for UI | COVERED | `nobrainer-browser`, `delivery.md` | rendered evidence | — |
| Test: literal evidence in done | COVERED | handoff block, `check_flow_done` | Checked line, DONE_WITH_GAPS | — |
| Test: continuous evals in CI | PARTIAL | `docs/TESTING.md`, `docs/evals/` | manual eval records | standing scenario set, eval-coverage check on changed skills and hooks, corrections add a frozen scenario |
| Deploy: AI in the PR review loop | PARTIAL | `nobrainer-review` | CLOSEOUT, BUG_HUNT, RELEASE_GATE | project `REVIEW.md`, compliance pass, IMPORTANT/NIT with nit cap, repeat findings promoted |
| Deploy: hooks as approval gates | PARTIAL | `flow_guard.py` ask on prod commands | owner gates | strict mode that denies production deploy patterns |
| Deploy: CI/CD integration | PARTIAL | read-only CI, unattended-run readback | rollback readback | headless judgment-step pattern, dev/staging/prod tiers |
| Maintain: closing the loop | MISSING | — | — | `closing-the-loop.md`: rolling baseline, deterministic detector, tiered bands, intent record per finding, eval per fix |
| Maintain: recurring security scans | PARTIAL | `nobrainer-security` on demand | SECURITY_REVIEW | scheduled scan scoped to changes since the last scanned SHA |
| Maintain: on-call post-mortems | PARTIAL | `nobrainer-rca` report, `tasks/lessons.md` | RCA report | report persisted under `docs/incidents/`, detection gap becomes a regression or eval |
| Cross: committed artifact chain | PARTIAL | spec hash, head SHA, evidence receipt | — | intent and incident records close both ends |
| Cross: one source of truth per artifact | COVERED | `long-run-state.md`, persistence gate | — | — |
| Cross: leading and lagging measures | PARTIAL | `flow_report.py` | quality report | not changed; candidate for a later release |

Limits: this map reads skill text, not client behavior. CLIENT_RUNTIME: NOT_VERIFIED.
