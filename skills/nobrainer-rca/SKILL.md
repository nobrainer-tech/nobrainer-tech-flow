---
name: nobrainer-rca
description: "Use when the owner says nb-rca or deep-rca, or requests an evidence-bound diagnosis of what caused a specific observed incident, regression, test failure, outage, wrong value, or unexpected system behavior before proposing a fix."
---

# NoBrainer Root Cause Analysis

Explain a specific observed failure with a continuous evidence chain. Diagnose
before proposing or implementing a fix. Use the project's maintained debugging
and tracing capabilities for reproduction and hypothesis tests; this skill owns
incident framing, adaptive independent investigation, evidence reconciliation
and a durable RCA verdict.

Do not use for broad code auditing, risk review, or choosing among already-known
solutions. Those are different tasks.

## Investigation contract

Freeze the incident before searching:

```text
SYMPTOM: <literal observation>
EXPECTED: <contract or baseline>
WHEN: <timestamp/window/version>
ENVIRONMENT: <runtime, release, region/account boundary>
REPRODUCTION: REPRODUCIBLE | INTERMITTENT | NOT_REPRODUCED
IMPACT: <users/data/money/availability>
LAST_KNOWN_GOOD: <version/time or UNKNOWN>
FROZEN_INPUTS: <logs, commit, config snapshot, request IDs or UNKNOWN>
WRITE_AUTHORITY: READ_ONLY unless explicitly expanded
```

Ask one focused clarification only when a missing value changes where or how to
investigate. Otherwise mark it `UNKNOWN` and gather evidence. Never put secrets
or full sensitive payloads in prompts or reports.

## Calibrate investigation breadth

Default to one primary investigator. Add independent perspectives only when the
system boundary or evidence warrants them:

- `LIGHT`: one deterministic local failure with a short trace and one subsystem.
- `STANDARD`: three to five bounded perspectives for multiple layers, timing,
  state, configuration or external dependencies.
- `HIGH`: five to eight perspectives for production incidents, data/money,
  intermittent concurrency, security boundaries, or conflicting evidence.

Possible perspectives are forward trace, backward data lineage, timeline/logs,
configuration/state, dependency boundary, cache/concurrency/timing, hypothesis
killer, and similar-incident history. Assign only relevant ones. Ten generic
agents are not rigor; coverage of real uncertainty is rigor.

Each investigator gets the same frozen incident identity but a disjoint question
and returns `FINDING`, literal `EVIDENCE`, source/time, confidence, alternatives
disproved, and blind spots. A timeout, malformed response, stale log, partial
trace, or inaccessible runtime is missing evidence, not agreement.

## Evidence pipeline

### 1. Establish the baseline

Read repository instructions, actual checkout, dirty state, release/commit,
current config schema, tests, logs and incident artifacts. Distinguish the code
now on disk from what ran during the incident. Do not treat documentation or
memory as runtime state.

Reproduce the symptom with the smallest safe input when possible. A production
write, credential use, external message, destructive query or instrumentation
that changes behavior requires its normal owner gate.

### 2. Build a causal graph

Trace from trigger to symptom and backward from bad output to source. At every
component boundary record:

- input value and timestamp;
- transformation/decision and exact code/config version;
- output value and destination;
- evidence reference and remaining gap.

Build a timeline when chronology, cache, retry, race, scheduling or deployment
can matter. Do not invent timestamps or fill gaps with narrative.

### 3. Test hypotheses

State one falsifiable hypothesis at a time: "X caused Y because Z." List the
evidence that would confirm and disprove it, then run the smallest safe test that
changes one variable. A failed hypothesis becomes recorded evidence; do not pile
additional guesses onto it.

After three failed fix-like experiments, stop and question the architecture
with the owner. RCA itself does not implement a fix.

### 4. Reconcile perspectives

Deduplicate findings by causal link, not wording. Prefer evidence from the exact
incident/version over newer generic behavior. For conflicts, compare source,
time window, checkout and command. Run one bounded tie-breaker that seeks a
single discriminating observation.

Do not force one root cause when the evidence chain has a real gap. Use:

- `CONFIRMED`: continuous chain and alternatives materially disproved;
- `PROBABLE`: strongest supported cause with explicit missing evidence;
- `INCONCLUSIVE`: no cause crosses the proof threshold.

Contributing factors explain why impact was possible or worse; they are not
automatically the initiating root cause.

## RCA report

```text
RCA RESULT: CONFIRMED | PROBABLE | INCONCLUSIVE
RIGOR: LIGHT | STANDARD | HIGH

SYMPTOM / EXPECTED / IMPACT
  <frozen incident statement>

ROOT CAUSE
  <one cause, or NOT PROVEN>

EVIDENCE CHAIN
  1. <trigger/source + literal evidence reference>
  2. <transformation/boundary + evidence>
  3. <observable symptom + evidence>

TIMELINE
  <ordered events or NOT_APPLICABLE>

DISPROVED HYPOTHESES
  - <hypothesis + discriminating evidence>

CONTRIBUTING FACTORS
  - <factor + evidence>

DETECTION GAP
  <why existing test/monitor/guard did not catch it>

RECOMMENDED FIX CONTRACT
  <behavior to change, regression test and verification; no implementation>

CONFIDENCE / BLIND SPOTS
  <level, missing evidence, stale/inaccessible sources, failed investigators>

RECOVERY
  <incident containment already observed, rollback candidate, owner gate>

NEXT_ACTION
  <one exact diagnostic, approval, or separate fix task>
```

Every causal claim must be tagged as observed evidence or an inference from
named evidence. Never write "checked" without the command/readback or source
reference. Preserve sensitive details outside the public report.

## Stop boundary

End after diagnosis and fix contract. Do not silently change code, configuration,
data, production, credentials, monitoring, or retry policy. If the owner asks to
fix after accepting the RCA, start a separate bounded implementation with a
failing regression test through `nobrainer-build`, then return for fresh
verification and review.
