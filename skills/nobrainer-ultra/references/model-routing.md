# Model policy and routing

`nobrainer-ultra` owns the model policy. This contract is portable:
clients may execute it, expose a model choice, or report `UNSUPPORTED`;
no provider is assumed. A model name, manifest or default setting is not
runtime proof.

For Codex delegated execution, apply the [Codex preset](codex-routing.md) unless
the owner overrides it. MAIN remains host-selected; other clients keep the
portable default below. Client detection and model availability require readback.

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

- Outside the Codex delegated preset, if no policy is supplied, use `STANDARD` with the owner- or
  host-selected model; never infer `ROUTED`.
- `STANDARD` uses the owner- or host-selected model and effort. It is
  the default for small, reversible work and unknown cost.
- `EXTENDED` keeps that identity while allowing a larger declared
  effort, context, time or cost budget and bounded extra verification. A
  stronger model is an explicit policy change with an exact model and gate; it
  is never a hidden retry.
- `ROUTED` is the bounded auto-routing mode: it selects a capability
  tier before execution from the models the host actually advertises. Record
  the exact model, effort and budget
  before dispatch. If the target is unavailable, return
  `MODEL_ESCALATION_PROPOSED` or require `OWNER_APPROVAL`;
  do not silently substitute another model. The Codex preset explicitly permits
  pre-send MAIN fallback; uncertain delivery must first be reconciled.

## Routing heuristics

- Use the cheapest capable model for reconnaissance, formatting and bounded
  read-only checks.
- Use the host-selected/default capable model for ordinary implementation.
- Request a stronger tier only when ambiguity, security, architecture, failed
  proof or a declared quality bar justifies its added budget.
- Delegate only a disjoint scout, checker or bounded implementation. Pass the
  frozen policy to the worker; it cannot choose a successor or escalate itself.
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
