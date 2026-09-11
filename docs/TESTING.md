# Testing and evaluation

The repository uses four evidence layers. A green lower layer never proves a
higher one.

## 1. Structure and public safety

- portable frontmatter, directory/name identity and exact active inventory;
- relative companion links and retired-name exclusion;
- public-clean text, manifest parsing and version consistency;
- installer conflict refusal, idempotence, readback, race-safe atomic restore and
  preserved migration/rollback recovery claims;
- secret scanning before publication.

Run:

```bash
python3 scripts/validate_skills.py
python3 scripts/validate_skills.py --suite
```

## 2. Deterministic behavior contracts

Unit tests pressure the routing, model-policy and safety invariants that can be
checked without an LLM: Ultra states, bounded-turn `SESSION_HEALTH_GATE`,
checkpoint/end-turn decisions, separate `RUNTIME_RELEASE`, session identity and
lease gates, SDD boundaries, trigger ownership, browser routing, adapter
registration and installer races.
Adapter tests execute every bootstrap mechanism that can run locally: the Claude
and Cursor SessionStart JSON shapes, OpenCode injection/deduplication, and Pi
discovery plus post-compaction re-injection. They also parse the portable Agent
Plugin, Gemini and Kimi manifests, reject invented Devin/Hermes adapters and
enforce the exact sixteen-skill inventory, correction hooks and workflow
diagram contract.

```bash
python3 -m unittest discover -s tests -v
```

### Session-lifetime smoke

[`tests/test_session_lifecycle.py`](../tests/test_session_lifecycle.py) is a
deterministic, model-free protocol smoke. It covers the nominal clean-session
trace, each health-gate event, configurable warning/hard limits, unknown and
unsupported signals with safe bounded continuation, strict-budget refusal, checkpoint plus `END_TURN` without authorized rotation,
`task_complete` with a live controlled worker followed by explicit release, and
empty-ready-set handling: wait for running work, audit reports, finish accepted
work, or surface a real owner decision. It also
proves that resume reads the durable Markdown goal instead of stale summary
text, and that host clear requires capability, no active writer and positive
readback; otherwise the contract ends the turn or requires manual action. It does
not prove that Codex, Claude Code,
OpenCode or another host exposes those signals; that requires the clean-session
readback below.

GitHub Actions runs these deterministic layers on Linux and macOS. It checks
Python, Node and shell syntax plus deterministic adapter contracts, and runs a
checksum-pinned Gitleaks tree scan on Linux. CI does not claim a client UI or
model followed a skill.

## 3. Forward behavior evaluation

Historical v1.6 runtime receipts bind the frozen source archive, not a changing
checkout. The test rejects missing, duplicate or altered archived entries and
continues checking the original case and output hashes. A later instruction
review is source-contract evidence unless fresh model runs are recorded for its
exact bytes; it cannot upgrade the release's runtime proof.

Behavior-shaping changes need a frozen scenario set, an unchanged baseline and
an independent judge. Keep development cases separate from final holdout cases;
do not tune against a failed holdout. Record accepted findings, null results,
digest, rollback and any model/harness substitutions.

Before baseline scoring, self-test the complete evaluator with known-good and
known-bad controls plus a deceptive control when the metric can be gamed.
Candidate writes must not reach the rubric, cases, score extractor or acceptance
harness. Bind each score to target/evaluator/case identities and raw evidence;
changed receipt fields require re-baselining. Predeclare equal repetitions for
stochastic comparisons and require at least three paired runs for a borderline
promotion claim.

The [v1.6.1 evidence](releases/v1.6.1.md) records fresh response simulations
and actual artifact execution, including failed behavioral gates. No measured
model-quality promotion is accepted. Artifact integrity and score arithmetic
are checked independently of those behavioral verdicts.

The v1.6 probes and their source bindings are in
[`releases/v1.6.0.md`](releases/v1.6.0.md). Source-only contract tests and
one behavioral trial are not a comparative benchmark. Earlier changed-control records are
[`evals/v1.3.0-harness-clarity-2026-08-30.md`](evals/v1.3.0-harness-clarity-2026-08-30.md),
[`evals/dispatcher-routing-v1.2.0-2026-08-28.md`](evals/dispatcher-routing-v1.2.0-2026-08-28.md)
and
[`evals/writing-density-v1.2.0-2026-08-28.md`](evals/writing-density-v1.2.0-2026-08-28.md).
The broader v1.1 routing baseline remains in
[`evals/core-routing-v1.1.0-2026-08-28.md`](evals/core-routing-v1.1.0-2026-08-28.md).
Do not mix scores across changed inventories, prompts or rubrics.

## 4. Client runtime acceptance

A client becomes runtime-verified only after a clean-session transcript proves
discovery and correct first actions. Follow
[`COMPATIBILITY.md`](COMPATIBILITY.md). Marketplace publication, production
behavior and buyer usefulness each require their own readback.

For a long-running probe, read back `SESSION_HEALTH_GATE` at `START`,
`AFTER_COMPACTION`, `MATERIAL_TRANSITION` and `BEFORE_CLOSEOUT`, including the
host policy and actual signal values. Read back `RUNTIME_RELEASE` separately;
`task_complete` is not evidence that task-owned browser, tool or subprocess
workers ended. A missing capability is `UNKNOWN` or `UNSUPPORTED`, lowers the
runtime proof, and must not be reported as a clean-runtime pass. Missing optional telemetry
does not block safe artifact delivery; missing enforcement of an explicitly
required hard budget blocks only work that depends on that guarantee.
Native goals are optional and require the host tool's authorization; a Markdown
goal is sufficient. Before a host clear, persist and read back `GOAL_FILE`, verify no task-owned
writer remains, record `CLEAR_MODE`, then prove clear completion. Start a fresh
turn by reading the same goal file and reconciling repository, checkout, state
and next safe action; transcript text alone is not recovery evidence.

For Codex, test explicit canonical invocation with `$nobrainer-ultra` and test
plain aliases separately as implicit-routing controls. Bind the transcript to
the exact installed skill hash and disable same-name user copies in an isolated
probe; two skills with the same name are not merged. An alias failure must not be
reported as a source-isolated behavior result.

Model-policy tests prove the portable `STANDARD`, `EXTENDED` and `ROUTED`
contract, including the no-silent-switch rule. They do not prove that a client
actually selects a provider model. That requires a clean-session readback of
requested versus actual model, effort, budget and escalation behavior.

## Release gate

A releasable commit requires:

- all deterministic checks green on the exact commit;
- no unresolved P0/P1 review finding;
- a public-clean and secret scan;
- a recorded behavior holdout for changed workflow controls;
- a review-failure scenario proving the route returns to Build with invalidated
  evidence;
- a public-surface coherence check: every affected README, doc, template and
  diagram is updated and read back, or `NOT_NEEDED` is recorded with a reason;
  flow changes refresh both the SVG and README Mermaid chart;
- honest compatibility labels;
- model names and marketing remain workflow-positioning claims unless direct
  runtime evidence exists;
- a rollback path;
- owner approval for merge and publication.

Scan the exact staged candidate with:

```bash
gitleaks git --pre-commit --staged --redact --no-banner --ignore-gitleaks-allow
```

A full-history finding is a separate history-remediation decision. Investigate
it explicitly; do not hide it behind a broad allowlist or treat it as proof that
the staged candidate introduced a secret.

## Session restart

`tests/test_restart_gate.py` invokes the shipped helper rather than a test-only
copy. It covers startup-cost payback, unknown economics, repeated restart without
progress, consent, unknown writers, stale checkpoints/ACKs, uncertain transport,
unsupported transfer and archive/takeover ordering. These are decision-level
tests; no real session is created or archived by the helper.

Native-adapter acceptance additionally requires an actual fresh target, visible
read-only ACK, authoritative conditional transfer, target takeover and exact old
session archive readback. Include a competing trigger and interrupted create.
Measure accepted work and total input/output/compaction/recovery usage before
and after; deterministic decisions do not establish token or quality gains.
