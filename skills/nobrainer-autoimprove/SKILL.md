---
name: nobrainer-autoimprove
description: "Use when the owner says nb-autoimprove, deep-autoresearch, code-autoresearch, nobrainer-capture-lesson, or nobrainer-continuous-improvement; asks to improve a skill or prompt; or wants a measurable bounded baseline-variant-evaluation loop instead of one subjective rewrite."
---

# NoBrainer Autoimprove

Improve one artifact only when a frozen evaluation proves a candidate better.
This independent adaptation applies Andrej Karpathy's
[autoresearch](https://github.com/karpathy/autoresearch) measure-change-keep loop
to skills, prompts, instructions and other reviewable artifacts; it is not an
official Karpathy project.

## Route the smallest fix

Fix an obvious typo, dead link or deterministic defect directly and cover it
with the normal test. Do not start an experiment when the objective cannot be
measured, target/evaluator isolation is impossible, or the change needs an
unapproved production, credential, publishing, safety or irreversible action.

Treat owner correction as evidence, not permission for a global rewrite:

- task-local clarification stays in the task;
- a repeatable behavior gap becomes a regression scenario;
- a verified durable fact or preference follows `LEARNING_WRITE_POLICY`:
  `AUTO_SCOPED` writes one minimal sourced rule to one canonical store, `ASK`
  prepares one exact diff, and `OFF` keeps it task-local: do not create a durable
  diff in `AGENTS.md`, `tasks/lessons.md` or a wiki.

On `AGENT_ERROR_CORRECTED`, preserve the failing scenario and error fingerprint,
fix the active result first, then test the smallest reusable prevention. One
anecdote never justifies a broad user trait or unrelated write.

## Frame before mutation

Freeze this contract before changing the target:

```text
TARGET: <one artifact and allowed write scope>
OBJECTIVE: <one observable improvement>
BASELINE_VERSION: <commit/hash/copy>
DEVELOPMENT_EVAL: <representative iteration cases>
HOLDOUT_EVAL: <unseen promotion cases>
HARD_GATES: <format, safety and deterministic checks>
SCORE: <criteria, aggregation, direction and meaningful delta>
EVAL_INTEGRITY: <separate owners, access and calibration controls>
SCORE_RECEIPT: <append-only trial identity, provenance, raw evidence and decision>
NOISE_POLICY: <paired repetitions, dispersion and retry rule>
BUDGET: <finite variants, rounds, repetitions, retries, time and resources>
PLATEAU: <minimum delta and dry rounds>
ROLLBACK: <retained baseline, restore and readback>
OWNER_GATES: <action, owner and recorded evidence>
```

Preserve the baseline in an isolated copy, branch or worktree. One coordinator
owns the champion and log; candidates never race on the same file.

## Return a complete initial plan

An initial plan comes from a completed experiment contract, not a summary of
this skill. Resolve every field internally; the owner-facing plan need not mirror
internal labels. Never omit a hard gate or replace exact evidence with
"immutable receipt", "bounded budget" or similar shorthand.

The plan must operationalize:

- an observable access boundary: candidate write scope excludes evaluator
  inputs, labels, logic, extractor, cases and holdout;
- ordinary positive, known-bad and tailored deceptive controls for the literal
  gaming, omission and unsafe-abstention risks;
- fixed baseline/candidate identity, exact paired run count, blind or shuffled
  presentation, seeds or sampling rule, dispersion, score math and threshold;
- the complete per-trial receipt fields, not a mutable aggregate;
- a disjoint holdout frozen before tuning, opened once, never reused for
  iteration, with measurable primary delta, uncertainty rule and protected
  usefulness, safety or regression guardrails;
- every supplied ceiling or an explicit stricter one, honest terminal states,
  and each named owner's approval identity, scope, timestamp/evidence and next
  gate. An experiment win grants no live or durable authority.

A ceiling needs a concrete quantity and unit; a label or promise to predeclare
one later is not a ceiling.

Unless the owner supplies another terminal, end plan-only output with
`STATUS: READY_FOR_OWNER_REVIEW | BLOCKED` and `EXECUTION: NOT_STARTED`. Pending
future gates normally mean ready for review. Use `BLOCKED` only when a missing
fact, boundary or decision prevents a valid proposal. Never imply that
calibration, trials or approval ran. Any owner-defined exact terminal values,
including experiment-result terminals, suppress canonical status and execution.

`STRICT_CAP` makes the owner's word limit a hard gate. Before applying either
formula, if `limit <= 40` with a counter or `limit <= 50` without one, skip the
reserved-offset formula and use the owner's actual cap for a minimal complete
answer. Return `BLOCKED` within the cap only when required facts cannot fit;
small limits alone are not a blocker. Otherwise apply the existing formula. At 250 words or
fewer, budget the draft to `min(limit - 40, 140)` words in at most six nonblank lines.
With a counter, compress until the owner limit passes; without one, target
`min(limit - 50, 130)` and never claim an exact count. Print no heading, blank
line, internal form, rollback explanation or duplicate terminal. Group only:
access; sets/controls; trials/receipt; holdout/decision; limits/stops; gates.
Preserve exact numbers, owners and negations; invent no optional mechanism.
Treat scope and timing qualifiers, closed field sets and terminal value domains as
non-compressible: reuse their literal wording instead of a plausible synonym.
When a qualifier applies to each role or item, repeat it for each; collective
shorthand is not equivalent.
If the owner gives a word range or minimum, its lower bound is also a hard gate
and overrides the compact budget. For an exact range, count the final draft with
an available whitespace counter and adjust once. Without one, target the range
midpoint and tally whitespace-delimited words before sending. For a bare minimum,
leave at least 10% headroom. Never exceed a stated maximum.
Count exact final text. For a serialized draft, pipe it through the bundled
`scripts/count_words.py --escaped-newlines`; a raw `%s` count is invalid evidence.

Run `CAP_AUDIT` before compact output: preserve disjoint one-time holdout and
open-once semantics; reproduce an exact receipt field list with no additions;
retain `immediately` when stops are immediate; and when the owner defines exact
terminal values, append no canonical status or execution field. If required
facts cannot fit, return `BLOCKED` within the cap rather than omitting them.
Scan the complete draft once more: no later duty may contradict a role's `only`
boundary, and every closed value domain retains its literal `only` or `no other`
qualifier.

## Protect evaluator integrity

The evaluator owner and candidate owner must be separate. Candidate write scope
excludes the rubric, development/holdout cases, score extractor and acceptance
harness; keep them read-only and outside the candidate workspace when possible.
A prompt-only prohibition is insufficient when the generator can mutate the
score path. Record weaker isolation and do not promote a gameable result.

Before baseline scoring, calibrate the complete path on ordinary positive,
known-good, known-bad and tailored deceptive controls. It must rank good above
bad, reject deceptive metric gaming, and self-test score extraction and hard
failures. Trace every rubric requirement to the frozen request; a hidden
judge-only requirement invalidates the evaluator. Missing ground truth or failed
calibration is `BLOCKED`.

Bind every score to an append-only immutable receipt containing: experiment and
round ID; candidate ID and target hash; case-set, evaluator, rubric and extractor
hashes; judge version/settings; seed or sampling policy and call order;
input/data snapshot and configuration; timestamp, repetition ID, environment and
budget identity; raw evidence; criterion vector, hard gates, inclusion,
retry/error/stop and resulting decision; aggregation formula, inputs, math and
aggregate. Content-address it and forbid post-hoc edits. Changed provenance makes
results non-comparable: re-baseline instead of carrying a score forward.

Predeclare at least three paired repetitions under identical conditions and
compare aggregated gain with measured dispersion. Forbid cherry-picking and
favorable retries. Retry only one predeclared transient failure; receipt and
count it, never retry to change a result. A calibrated deterministic evaluator
may run once when its receipt proves determinism.

Production deployment, credentials, publishing, security or system changes,
external contact, spend, destructive actions, durable policy, lessons or wiki
writes remain named owner gates. Record the owner, decision and evidence
reference before action; experiment success grants none of them.

## Run the bounded loop

`FRAME -> CALIBRATE -> BASELINE -> GENERATE -> HARD_GATE -> DEV_SCORE -> SELECT -> FINAL_HOLDOUT -> PROMOTE_OR_REVERT`

Use development cases for common, edge, adversarial and non-trigger behavior.
Prefer one behavioral change per round and three to six genuinely different
candidate hypotheses. Run deterministic, public-clean and security gates before
judge spend. A hard-gate failure, missing receipt or failed calibration is
disqualified, not averaged down.

Score on the unchanged development eval. Select only beyond measured noise; on
a near-tie keep the simpler, shorter, lower-risk artifact. One optional graft may
combine distinct strengths from a losing candidate, then rerun every gate.

Open the sealed holdout exactly once for the unchanged baseline and champion.
Promotion requires all hard gates, the predeclared meaningful primary gain, no
protected regression, target-workflow review when subjective, retained baseline
and tested rollback. A holdout loss is `REVERTED`; never tune on that holdout.
Any next attempt needs a new holdout, new baseline and new experiment record.

When nested under `nobrainer-ultra`, update its one canonical TODO after each
auditable round and final holdout; do not create a second status owner.

## Stop the experiment, not the outcome

Stop the current experiment on its predeclared decision, failed evidence or
safety anomaly, configured dry rounds, practical score ceiling, exhausted
budget, converged candidates, hard-gate regression, holdout loss, or changed
target/constraints/authorization. A null result retains the baseline.

These stops do not close a still-open owner outcome. If proved improvement is
still required, diagnose frozen evidence once, choose the smallest high-leverage
change and start a fresh bounded experiment. Never reuse a failed holdout or
substitute blind retries. Apply Pareto discipline: remove the largest observed
failure before polishing lower-impact criteria. Close only when DoD passes or a
concrete authority, access, budget or distinct-hypothesis blocker is reported.

## Final report

Return winner/baseline identity, development and holdout scores, criterion
vectors, hard-gate output, noise/dispersion, calibrated evaluator status, budget,
stop reason, diff, rollback and uncertainty. End with:

```text
PROMOTION: PROMOTED | NO_CHANGE | REVERTED | BLOCKED
CHAMPION: <version/ref or BASELINE>
HOLDOUT_RESULT: PASS | FAIL | NOT_RUN
EVALUATOR_STATUS: CALIBRATED | FAILED | UNVERIFIED
SCORE_RECEIPT: <immutable receipt ref or NONE>
NOISE_RESULT: <replications, dispersion and comparable delta or NOT_APPLICABLE>
```

Use `NO_CHANGE` when no candidate proves better, `REVERTED` after holdout loss,
and `BLOCKED` when a gate prevents a valid experiment. Never claim `PROMOTED`
without paired comparable scores and a successful holdout.
