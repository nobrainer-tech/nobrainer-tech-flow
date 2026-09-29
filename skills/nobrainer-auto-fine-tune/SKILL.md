---
name: nobrainer-auto-fine-tune
description: "Use when setting up nobrainer-tech-flow for the first time, when the owner says nb-auto-fine-tune, or when client capabilities, model routing, context or useful parallelism need recalibration."
---

# nobrainer-tech-flow: Orchestration Calibration

Run this skill as the standard first-setup step for nobrainer-tech-flow. Discover the current client's and project's actual capabilities, evaluate whether delegation helps, and record evidence-backed recommendations. Read [capacity and update audit](references/capacity-audit.md) at project setup or when limits are in question. Read [benchmark routing](references/benchmark-routing.md) when the owner wants ready-made worker routing from the published benchmark setups, or asks to refresh or apply it; only verified local outcomes may re-order that prior. It does not train or fine-tune model weights, choose a replacement for MAIN, create sessions, schedule workers, or run an open-ended optimization loop.

## Preserve the owner's choice

Treat the model and effort selected for MAIN as fixed for this task. Do not lower or replace them to save cost. Recommend separate worker models and effort only for bounded delegated work, using currently available evidence. If the selected MAIN identity or effort is not observable, preserve the current runtime and report `UNKNOWN`; do not infer it from a saved preference, prior task, or model catalog.

## Discover this client's actual capabilities

Inspect the current harness and relevant project/client configuration for:

- models and exact model identifiers the client advertises;
- models and effort levels the current runtime can actually request;
- native subagent creation, isolated worktrees, concurrency limits, and available transport/readback;
- active client version/update status; effective profile, selected provider, configured versus catalog-advertised versus observed context window;
- any trustworthy latency, token, or cost telemetry and its measurement scope.

Keep advertised, configured, callable, and successfully invoked capabilities distinct. Verify a capability with a read-only or harmless probe only when supported and useful. Never make a paid benchmark call merely to prove a model exists. Record unavailable, hidden, or unverified fields as `UNKNOWN` or `UNSUPPORTED`. Do not hardcode model names, rankings, prices, concurrency, or provider behavior. A model name suggested in a prompt is not proof that the host honored it.

## Decide whether calibration is worth doing

For a one-off, low-risk task, use the owner's selected MAIN and current known tools; skip benchmarking and state that routing is uncalibrated. For a recurring workflow, material model choice, or task with meaningful quality/latency/cost tradeoffs, define a small bounded comparison before spending resources.

Classify the work by required expertise, context, accuracy, latency, cost sensitivity, confidentiality, dependence between units, and integration effort. Delegate only independent units with measurable acceptance and disjoint write scope. Estimate speed benefit from the critical path and observed concurrency, accounting for setup, review, and integration. Parallelism is useful when it improves time to a checked outcome or provides independent quality evidence; it is not a target by itself.

## Run a bounded, comparable calibration

Before comparing worker routes, freeze:

- the task category and representative cases, including an ordinary case and a relevant edge or non-trigger case;
- identical inputs, instructions, tools, output contract, and acceptance rubric for each candidate;
- the quality gates and any minimum acceptable score;
- the latency measurement boundary, such as request-to-complete, and the available cost/token source;
- a small call and time budget, retry rule, and stop condition.

Run candidates on the same cases. Blind or shuffle outputs for subjective review when practical. Score acceptance and factuality first; then compare measured latency and cost among routes that meet quality gates. Use repeated paired trials only when variability could change the routing decision and budget allows. Do not fabricate costs from public list prices, estimate latency from model labels, cherry-pick retries, or treat a worker's self-report as independent evaluation. If telemetry is absent, report that dimension as `UNMEASURED`.

Stop when evidence identifies an adequate route, the result is inconclusive, the budget is reached, or a quality/safety gate fails. Return `NO_CHANGE` when no candidate demonstrates a useful improvement. Calibration evidence applies only to the tested client, task category, settings, and period; it is not a universal model ranking.

## Produce a routing policy

Return a concise policy with:

```text
CLIENT_AND_RUNTIME:
MAIN_MODEL_AND_EFFORT: PRESERVED | UNKNOWN
CAPABILITIES: ADVERTISED / CONFIGURED / CALLABLE / VERIFIED, with exact IDs and evidence
TASK_CATEGORY_AND_CASES:
CANDIDATE_ROUTES_AND_SETTINGS:
QUALITY_RESULT:
LATENCY_RESULT: measured boundary and result | UNMEASURED
COST_OR_TOKEN_RESULT: source and result | UNMEASURED
PARALLELISM: useful slots, dependencies, write isolation, integration cost | UNKNOWN where unverified
CONTEXT: configured / catalog-advertised / provider-documented / runtime-observed
CLIENT_UPDATE: UP_TO_DATE | AVAILABLE | BUSY | UNAVAILABLE | UNKNOWN
RECOMMENDATION: route by task category; retain MAIN choice
LIMITS_AND_EXPIRY:
PERSONALIZATION_CHANGE: NOT_PROPOSED | PREPARED_FOR_REVIEW | APPLIED_WITH_EXPLICIT_AUTHORIZATION
```

State the next calibration trigger, such as a runtime/model catalog change, a material quality regression, or a changed workload. Do not retain secrets or unnecessary user data in the policy.

## Keep the Flow skill boundaries

- `nobrainer-team` owns capability-to-role design and assignment contracts. Give it this skill's verified candidate evidence; do not duplicate its roster planning.
- `nobrainer-dispatcher` owns ready-set selection, batch ordering, and backpressure. Give it measured concurrency and critical-path findings; do not dispatch workers here.
- `nobrainer-sessions` owns visible session identity, transport, restart, archive, leases, and receive-audit. Recommend a restart or archival only through its lifecycle rules and current authorization; this skill never creates, restarts, or archives a session.
- `nobrainer-autoimprove` owns frozen baseline/candidate/holdout experiments for changing prompts, skills, or durable artifacts. Route artifact tuning there; this skill may provide the routing benchmark contract but does not tune its own rubric or promote a candidate.
- The user owns persistent client/global personalization. Discover the appropriate documented settings surface and use the existing authorization for Flow setup when it covers that surface. Preview the smallest exact change, preserve unrelated instructions, make a recoverable backup, and verify the saved value by readback. If the scope is not authorized or materially ambiguous, ask for that decision. Prefer the client's global instruction surface for portable Flow awareness and a project instruction file for project-specific choices; never claim one client setting applies to another tool. Reuse the managed personalization installer rather than writing an untracked second configuration path.

## Closeout

Report the exact capabilities verified, the comparison performed or why it was skipped, measured results versus unknowns, the recommended task-specific routing, whether any setting was changed, and the next evidence needed. A configured preference, model listing, queued task, or worker report alone does not prove a callable or better route.
