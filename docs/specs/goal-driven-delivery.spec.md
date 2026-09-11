# nobrainer-tech-flow: goal-driven delivery

SPEC_ID: FLOW-GDD-001
VERSION: 0.1.0
STATUS: APPROVED
OWNER: repository owner
APPROVED_BY: owner instruction to implement and release, recorded 2026-09-11
APPROVED_AT: authorization recorded 2026-09-11; source acceptance recorded in tracker
SPEC_HASH: see tasks/autopilot-delivery-audit.md (hash stored outside specification)

## Outcome and assumptions

OUTCOME: An agent takes an authorized whole-project request through measurable
milestones to the complete agreed result, with visible TODO and minimum owner
intervention. It uses inspected specialists and safe parallelism to shorten
critical-path work while retaining integration responsibility.
AUDIENCE: users of any model/client capable of reading instructions and executing
appropriate tools, including less capable models given precise bounded tasks.
QUALITY_CONTRACT: full acceptance coverage, verified results, useful failure
recovery, concise work communication, natural authored deliverables.

This is an instruction-driven workflow, not a daemon, model-quality guarantee,
permission bypass, or scheduler. Model/client capabilities vary. The portable
baseline is Markdown with sequential MAIN execution. Native goals, subagents,
UI tools, scheduling and telemetry are optional capability adapters.

## Sources and decisions

| ID | Type | Source | Ruling |
|---|---|---|---|
| SRC-1 | OBSERVED | Owner requests, 2026-09-11 | Universal contract, whole-SDD goals, TODO, BUDDY consent, max 15 useful subagents, skills.sh specialists |
| SRC-2 | OBSERVED | [Incident review](../reviews/2026-09-11-autopilot-delivery.md) | Avoid repeated plan review without accepted progress; do not generalize all blockers as false |
| SRC-3 | ATTRIBUTED | [OpenAI guidance](https://developers.openai.com/api/docs/guides/latest-model) | Conflicting instructions can cause early pauses; retain source hierarchy and prior authorization |
| SRC-4 | OBSERVED | [GoalKit](https://github.com/Nom-nom-hub/goal-kit), [goal-oriented requirements](https://www.cs.toronto.edu/pub/eric/REFSQ98.html) | GDD terminology and goal-oriented methods predate this design; no originality claim for the term |
| SRC-5 | DECISION | Current implementation | GDD belongs to Ultra delivery plus Team/Dispatcher/Review; no seventeenth skill or duplicate state store |

## Scope and ownership

| Component | Responsibility | Dependency |
|---|---|---|
| Ultra / delivery | Overarching goal, BUDDY, TODO, milestone acceptance and continuation | Owner outcome |
| SDD | Requirements, acceptance IDs, scope changes | Inspected requirements |
| Team | Installed inventory, inspected external skills, bounded specialist assignment | Ready work and capability gaps |
| Dispatcher | Ready set, parallel batches, capacity and write conflict checks | Accepted dependencies and Team plan |
| Build | Implementation and focused repair | Authorized work unit |
| Review / Security | Concrete findings and risk-appropriate verification | Exact artifact and acceptance |
| Sessions | Optional native transport/recovery | Supported capabilities and authority |

The SDD is the contract. The existing task tracker is the sole milestone state
owner; native goal state mirrors only supported lifecycle operations. Never place
live worker IDs or lease state in this specification.

Excluded: modifying consumer production, credentials, account limits, automatic
publication, host safety policies, or retroactively rewriting historical evidence.
Codex-only delegated preset: `gpt-5.6-luna` with `max`, independently of MAIN;
explicit owner overrides win. Use MAIN fallback if unavailable; never change
global config or silently substitute models. Other hosts retain portable policy.

Existing compatibility package IDs and skill names remain stable. Current display
name is `nobrainer-tech-flow`; `nb-flow` and `nb-ultra` remain input aliases.

## Execution contract

1. Inspect enough evidence to define outcome, full DoD and necessary actions.
2. BUDDY resolves material ambiguity and bundles missing consequential permissions
   with exact targets and ceilings. Prior permission is reused; routine choices
   remain agent work. A late novel consequence needs a new scoped decision.
3. Bind one whole-SDD goal; partition all acceptance IDs into milestones. Show TODO.
4. Compute ready work. Team resolves skill gaps from installed/project capabilities
   or skills.sh. Inspect source/ref, scripts and permission scope before use.
5. Dispatch up to min(host/model capacity, 15 live descendants, useful ready units).
   MAIN continues integration or dependency work. Unknown spawn results count as
   unresolved capacity until reconciled. No nested dispatch without a reserved slot.
6. Verify milestone artifacts and integration; update TODO and continue ready work.
7. Before BLOCKED, try relevant permitted methods. Never evade a tool/policy denial.
   Preserve blocked acceptance IDs and perform independent work.
8. Complete the overarching goal only when every required milestone and the full
   integrated DoD passes. A local test or planning milestone never substitutes for
   delivery. Host-only START, MFA and actual quota failures remain explicit limits.

GDD milestone states and transition requirements are defined in the
[delivery reference](../../skills/nobrainer-ultra/references/delivery.md#gdd-goal-driven-delivery-through-milestones).
Repetition does not improve evidence by itself. One bounded review and focused
repair is the default per stable slice; new material defects justify more work.
Real security/acceptance blockers cannot be waived by a review-count limit.

## Requirements and acceptance

| Requirement | ID | Check | Layer |
|---|---|---|---|
| Derive written goal/DoD without a separate prompt | AC01 | Whole-SDD scenario: all acceptance IDs covered | Behavioral |
| Native goal only with host-required authority | AC02 | Explicit request, unfinished-goal reuse and lifecycle-only native API | Behavioral |
| TODO updated after milestones; continue ready work | AC03 | Two dependent stages plus an independent stage | Behavioral |
| One BUDDY permission package; reuse consent | AC04 | Prior consent plus missing permission, refusal and late new consequence | Behavioral |
| Available tool fallback before manual handoff | AC05 | CLI unavailable, permitted authenticated UI available | Behavioral |
| Denial and physical MFA retain real boundaries | AC06 | Denied action not rerouted; independent tests continue | Behavioral |
| Team capacity globally <=15 and actual host limit | AC07 | Capacity 4, unknown spawn, nested reservations | Behavioral |
| Skills.sh source becomes scoped specialist | AC08 | Candidate inspection and no-trusted-candidate fallback | Behavioral |
| Review converges without dropping blockers | AC09 | Repeated review with auth defect and independent slice | Behavioral |
| Concise progress retains exact human unblock action | AC10 | Blocker includes action, destination and resume condition | Behavioral |
| Canonical naming, stable IDs, historical evidence | AC11 | Maintained source scan and protected history checks | Source |
| Source remains structurally valid | AC12 | Validators, full unittest suite, source secret scan | Local |
| Codex workers use Luna/max; MAIN and other clients retain policy | AC14 | Codex available/unavailable and non-Codex scenarios | Behavioral |
| No universal runtime/speed claim | AC13 | Evidence report scopes tested model/client and untested surfaces | Review |

## Implementation milestones for this repository

| ID | Result | Depends on | Acceptance |
|---|---|---|---|
| M1 | Evidence-backed incident and capability diagnosis | None | AC13 |
| M2 | Delivery, BUDDY, goal/TODO and blocker rules | M1 | AC01-AC06, AC10 |
| M3 | Team/Dispatcher specialist and capacity rules | M1 | AC07-AC08 |
| M4 | Review convergence and naming coherence | M1 | AC09, AC11 |
| M5 | Integrated scenario review and deterministic verification | M2, M3, M4 | AC01-AC14 |

Current progress and evidence live in [the tracker](../../tasks/autopilot-delivery-audit.md).
M5 accepts this local source change, not a deployment or universal runtime claim.

## Recovery and approval

BASELINE: 40dc199; active source restored separately after accidental old-main switch.
MIGRATION: source review first, then authorized release/install with source readback;
active consumer tasks require a fresh load. No mass consumer rewrite.
ROLLBACK: reverse only this scoped patch or use the baseline source in an isolated
checkout; preserve dirty work and existing branch history. Re-run baseline checks.
STOP_CONDITIONS: actual denied operation, unresolved writer ownership, unavailable
required human action or materially new unapproved consequence; independent work
continues. Host-native goal blocked thresholds remain authoritative.
APPROVAL: Owner authorized design and reversible implementation in the task.
Final specification acceptance requires scenario review and AC coverage in the
tracker. No release or production action is granted by this document.
