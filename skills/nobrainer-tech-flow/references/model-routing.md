# Model policy and routing

`nobrainer-tech-flow` owns the model policy. This contract is portable:
clients may execute it, expose a model choice, or report `UNSUPPORTED`;
no provider is assumed. A model name, manifest or default setting is not
runtime proof.

MAIN keeps the model and effort selected by the user in every client. Use the
[Codex adapter](codex-routing.md) only for Codex-specific capability discovery,
not as a universal model preset. Client detection and model availability
require readback. Use [Auto Fine Tune](../../nobrainer-auto-fine-tune/SKILL.md)
when repeated work warrants measured route calibration.

## Freeze one policy before work

Record the policy in the canonical plan and copy it into each delegated work
unit. Use the smallest policy that meets the acceptance bar:

```text
MODEL_POLICY: STANDARD | EXTENDED | ROUTED
MODEL: HOST_SELECTED | <exact supported id> | UNKNOWN
EFFORT: DEFAULT | <exact supported setting> | UNKNOWN
BUDGET: tokens=<n>; time=<duration>; cost=<limit> | UNKNOWN
ESCALATION: NONE | PROPOSE | OWNER_APPROVAL
ROUTE_REASON: <risk, complexity, latency or evidence reason>
```

- If no policy is supplied, keep the owner- or host-selected MAIN model.
  Use `STANDARD` for a clear one-unit task or a client without native
  workers. Use `ROUTED` by default for substantial work with useful
  independent units and verified native worker support.
- `STANDARD` uses the owner- or host-selected model and effort. It remains
  the complete fallback for small work, unknown worker capacity or one-model hosts.
- `EXTENDED` keeps that identity while allowing a larger declared
  effort, context, time or cost budget and bounded extra verification. A
  stronger model is an explicit policy change with an exact model and gate; it
  is never a hidden retry.
- `ROUTED` is the bounded default for useful parallel work: it selects a
  capable worker for each independent unit from models the host actually
  exposes. Prefer a smaller, quicker route when the task's acceptance can
  still be met. Record the exact model, effort and budget
  before dispatch. If the target is unavailable, use an already verified
  capable worker route within the same authority or continue in MAIN; report
  the degraded mode. An uncertain send must be reconciled before retry.

## Routing heuristics

- For each independent ready unit, choose a smaller or faster worker only when
  the current host advertises it, the assignment accepts it, and the expected
  setup plus audit cost is lower than the critical-path benefit. Use measured
  cost and latency when available; otherwise mark them unknown.
- Default to useful native parallelism when the task splits cleanly. A second
  perspective may catch defects, and a smaller worker may avoid repeating
  MAIN's full context. These are mechanisms to evaluate, not universal
  measured improvements in quality, speed or token use.
- Use the host-selected/default capable model for ordinary implementation.
- Request a stronger tier only when ambiguity, security, architecture, failed
  proof or a declared quality bar justifies its added budget.
- Delegate disjoint research, implementation and review units proactively
  when useful. Use the maximum verified *useful* concurrency up to the host
  limit, with one exact write owner per file. MAIN integrates results while
  workers run. Pass the frozen policy to each worker; it cannot choose a
  successor, recursively delegate or escalate itself without assignment authority.
- Escalate only when new evidence changes the cost or acceptance decision.
  State the blocker, target tier, expected benefit, added budget and approval
  gate before starting the next attempt.

## Proof and limits

Record `MODEL_REQUESTED`, `MODEL_ACTUAL`,
`EFFORT`, budget and provider/client version when the host exposes
them. `UNKNOWN` or `UNSUPPORTED` keeps the runtime claim
`UNVERIFIED`. This is a portable policy, not a cross-provider model
gateway; a client may implement `ROUTED`, but the skills cannot claim
automatic switching until a clean runtime readback proves it.
