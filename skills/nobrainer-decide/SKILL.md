---
name: nobrainer-decide
description: "Use when choosing between options: just decide for a quick choice, decide or nb-decide for standard analysis, deep decide or deep-decide for deep analysis. Evaluate feasibility, reliability, total cost, delivery time, scale and reversibility."
---

# NoBrainer Decide

Deliver one ranked decision with evidence, confidence, watchpoints and kill
criteria. Do not hide behind several flavors of "it depends". This skill decides;
it does not diagnose an unknown failure or execute the chosen option.

Use `nobrainer-rca` first when the unresolved question is causal. Use
`nobrainer-research` when current external facts or a broader option space must
be established before scoring.

## Select the requested depth

Do not run a panel for a factual lookup, an already-made choice, or an obvious
reversible edit.

Match the owner's invocation, case-insensitively, longest phrase first:

| Invocation | Rigor | Work and output |
|---|---|---|
| `just decide`, `just-decide` | LIGHT | One pass; compare the credible alternatives and status quo; choice, decisive reason, main risk and next action in a short paragraph. No mandatory scorecard or panel. |
| `decide`, `nb-decide`, `nobrainer-decide` | STANDARD | Compare at least three distinct mechanisms including status quo; feasibility screen, compact comparison, challenge the leader and recommend one next action. |
| `deep decide`, `deep-decide` | HIGH | Standard analysis plus future scenarios, sensitivity, strongest counterargument, exit plan and bounded evidence gathering. |

Treat phrases as instructions only when the owner invokes them, not when they
occur in a quotation, filename or a request to edit this skill. An implicit
decision request defaults to STANDARD. A later explicit depth choice overrides
an earlier one. Depth never changes the selected model, permissions or budget.

Use MAIN by default. Independent native subagents can strengthen HIGH analysis
when authorized, available and worth their cost; do not require a fixed panel
size. Preserve the owner's model and effort. Never create visible conversations
as substitutes. If independent review is unavailable, complete the analysis in
MAIN and disclose that limitation; self-review is not an independent review.
The blind attack and fresh review below apply only to actual independent runs;
otherwise perform their checks once in MAIN without claiming blindness.

Set a finite analysis budget appropriate to stakes and the owner's deadline.
Default to one comparison and one challenge/revision cycle; further research
needs a named uncertainty that could change the choice. Stop when the choice is
stable, the evidence budget is exhausted or a decisive fact remains unavailable.
LIGHT still checks hard constraints and serious downside. For a high-stakes
quick request, give a concise conditional recommendation or bounded next check;
do not silently launch HIGH or manufacture certainty to finish quickly.

## 1. Frame the actual decision

Restate:

- decision, owner, deadline and observable outcome;
- baseline/status quo and what happens if nothing changes;
- hard constraints, reversible vs irreversible effects, and owner gates;
- evidence freshness and consequential unknowns.

Rewrite the problem once without project nouns. Ask "what system property makes
this decision necessary?" until symptom and root cause are separated. If a
candidate appears immediately, record it as an anchor to challenge, not the
answer.

Ask at most one focused clarification round. Then either decide or identify the
single missing owner choice/evidence that truly blocks a decision.

## 2. Generate different shapes

For STANDARD and HIGH produce at least three mechanisms, not parameter variants. Always include the
status quo. Include at least one shape from outside the user's initial frame:

- measure first;
- fix the systemic cause;
- remove the requirement;
- accept and observe within an explicit budget.

For every option state mechanism, expected benefit, key dependency, worst
failure, reversibility and earliest useful evidence. Reject duplicate shapes.

## 3. Score transparently

Before ranking, mark each option FEASIBLE, INFEASIBLE or UNVERIFIED against the
owner's hard limits: delivery deadline, implementation effort, available skills,
budget and minimum reliability. Reliability must mean an observable requirement
appropriate to the decision (for example acceptable downtime, error rate,
recovery time or loss). Never invent a threshold or treat an unknown as passing.
An infeasible option cannot win through points elsewhere. If no option passes,
recommend one bounded experiment or identify the constraint that needs changing;
do not relax it silently.

Prefer the simplest feasible solution that achieves the outcome. Estimate total
cost over the same stated horizon: build, migration, operation, maintenance,
attention, failure recovery and exit. Use ranges and sources; label estimates.
Include time to first useful result and time to a reliable finished solution.
Do not equate a cheap subscription with low total cost.

For HIGH compare current demand, plausible growth and an adverse scenario.
State capacity evidence, likely bottleneck and the measurable trigger for an
upgrade. Preserve a practical migration path instead of paying now for imagined
scale. A staged decision (X now, Y after threshold Z) is a valid single choice.

Define criteria from the actual outcome before scoring. The default ledger is:

| Criterion | Default weight |
|---|---:|
| outcome/metric movement | 3 |
| correctness and evidence | 3 |
| optionality and lock-in | 3 |
| downside/antifragility | 3 |
| production or operational readiness | 2 |
| recurring cost and attention tax | 2 |
| simplicity and maintainability | 2 |
| reversibility | 1 |
| one-time cost | 1 |
| time to useful result | 3 |

Change weights only with an explicit reason. Score 1–5 and show weighted totals,
source quality, sensitivity to uncertain assumptions, one-time and recurring
cost. Use a qualitative comparison when numeric scores would imply unsupported
precision. Numbers do not auto-select the winner; they expose the tradeoff.
Accept ties. Prefer the simpler, cheaper-to-reverse feasible option when evidence
does not distinguish them; state that tie-break. Do not re-score to force a gap.

Distinguish robustness (survives stress), resilience (recovers) and antifragility
(improves through bounded exposure and feedback). Redundancy alone proves none
of the improvement claim. Name the feedback mechanism and measurable improvement
before crediting antifragility. Never introduce harmful stress or uncontrolled
downside to earn that label. Check correlated failures and costly exit paths.

## 4. Attack the leader

A blind attacker receives the problem, evidence and leading option but not the
scorer's rationale. It must answer:

1. What if the problem framing is wrong?
2. Which rejected option deserves the strongest steelman?
3. Is the leader winning because it is familiar or easy?
4. Which assumption can reverse the ranking?
5. Is this systemic, a fallback, or a workaround?

Re-score when an attack changes a criterion or assumption. A fallback may win,
but name the systemic alternative and the trigger for revisiting it.

## 5. Cold review and commitment

A fresh reviewer sees the original decision, evidence and options, not prior
reasoning. It checks missing shapes, stale evidence, score sensitivity,
operational burden, rollback and owner gates. The synthesizer reconciles both
attacks and selects exactly one option.

Do not turn a recommendation into execution authority. Publishing, spending,
merging, deployment, credentials, production mutation, destructive action, and
safety changes remain explicit owner gates.

## Decision record

Use the short output above for LIGHT. For STANDARD keep only useful fields;
HIGH uses the fuller record below. Include feasibility, delivery range, total
cost horizon and reliability evidence in the comparison. Separate confirmed
facts, assumptions and forecasts. Confidence reflects evidence and ranking
stability, not the number of agents. An unresolved decisive fact permits a
conditional choice or time-boxed experiment, not an unsupported commitment.

```text
DECISION
  Choice: <one option>
  Confidence: LOW | MEDIUM | HIGH - <reason>
  Why it beats #2: <one evidence-bound sentence>
  Type: SYSTEMIC | FALLBACK | WORKAROUND
  Rigor: LIGHT | STANDARD | HIGH

SCORECARD
  <criteria, weights, scores, totals, sensitivity>

WATCHPOINTS
  - <metric + threshold + review/action>
  - <metric + threshold + review/action>

KILL_CRITERIA
  - If <observable condition> by <time/event>, stop or revert to <option>.

ROLLBACK
  - <procedure, owner, and readback>

REJECTED_OPTIONS
  - <option>: <decisive reason and revisit trigger>

OPEN_ASSUMPTIONS
  - <at most two genuinely decision-relevant assumptions or NONE>

OWNER_GATE
  - <exact approval needed before action or NONE>
```

End with one next action. Preserve the decision and evidence in the project's
existing durable record only when it will guide future work; do not create a
second source of truth.
