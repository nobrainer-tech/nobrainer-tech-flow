---
name: nobrainer-spec-driven-development
description: "Use when the owner says nb-sdd or when implementation needs a durable, reviewable specification because it changes architecture, public contracts, migrations, several dependent components, or work that may span sessions."
---

# NoBrainer Spec-Driven Development

Use spec-driven development to freeze what must be true before deciding how to
build it. This is not subagent-driven development. Session topology is handled
by `nobrainer-sessions`; implementation belongs to `nobrainer-build` and the
project's maintained engineering workflow.

Read [references/spec-template.md](references/spec-template.md) before writing a
new specification.

## Persist only when it pays

Create or update a durable spec when at least one is true:

- architecture, public behavior, data shape, external interface, or security
  boundary changes;
- migration, irreversible effect, expensive failure, or difficult `ROLLBACK`;
- several dependent components, phases, writers, or sessions share a contract;
- work may be resumed later and chat context would be unsafe;
- conflicting sources or unresolved assumptions can change acceptance.

Do not create a spec for a mechanical one-file correction whose target,
expected result, verification, and rollback are already unambiguous.

## Lifecycle

Use one explicit state:

`DISCOVERY -> DRAFT -> REVIEW -> APPROVED -> IMPLEMENTING -> VERIFYING -> ACCEPTED`

Alternative terminal states are `BLOCKED` and `SUPERSEDED`. Only the owner or
the project's designated authority can approve product, risk, or scope choices.

### `DISCOVERY`

Read current instructions, product sources, code contracts, tests, schemas,
runtime evidence, prior decisions, and existing specs. Mark every requirement
as `OBSERVED`, `INFERRED`, `RECOMMENDED`, or `UNKNOWN`. Surface contradictions;
do not silently select the convenient source.

### `DRAFT`

Write the smallest self-contained contract that an implementer and independent
reviewer can use without reconstructing the conversation. Include:

- `SPEC_ID`, version, status, owner, source references and assumptions;
- outcome, audience, scope, exclusions and non-goals;
- functional requirements, interfaces, invariants, side effects and failures;
- security, privacy, performance, compatibility and operational constraints;
- exact write surface or component boundaries;
- task graph, dependencies and safe parallelism when execution is multi-step;
- `ACCEPTANCE` IDs mapped to tests, verifier, build/runtime and evidence;
- owner gates, stop conditions, migration, recovery and `ROLLBACK`;
- unresolved decisions with one owner each.

Do not prescribe an implementation detail unless it is genuinely a constraint.

### `REVIEW` and `APPROVED`

Run a contradiction and completeness review against repository evidence. Every
requirement must map to at least one `ACCEPTANCE` criterion, and every criterion
must name reproducible evidence. Resolve or explicitly gate unknowns that can
change design, scope, safety, or acceptance.

Record approval identity, UTC time, version and a stable content hash. Freeze
that revision. A draft, an unbound hash, or approval from the implementer alone
does not authorize risky work.

Existing owner authorization counts: record the current task instruction when
it already defines and authorizes the scope. Do not demand another approval for
the same reversible implementation. Ask only for an unresolved product/risk
choice or consequential effect outside that authority.

### `IMPLEMENTING`

Derive bounded work units from the approved spec. The plan may describe order
and mechanics; it must not redefine the contract. Before each write, bind the
work unit to the current spec version/hash and allowed scope.

If implementation reveals a new requirement, side effect, contract change, or
truly out-of-scope file, stop at `SPEC_CHANGE_PROPOSED`. Routine file-list or
mechanical plan updates within the authorized outcome do not require new approval. Do not make code and spec
silently agree after the fact. Assess provisional changes and data effects,
update the spec, rerun review, obtain required approval, then resume from a new
frozen revision.

### `VERIFYING` and `ACCEPTED`

Verify each `ACCEPTANCE` ID against fresh target-workflow evidence. Local tests
do not prove deployment, production behavior, buyer usefulness, or external
readback. Record deferred checks and their owner; do not mark acceptance while a
required gate is unassessed.

Acceptance requires: spec revision/hash, requirement-to-evidence ledger, scope
diff, tests/verifier/build/runtime results, quality review, remaining
uncertainty, and tested `ROLLBACK` or a justified non-applicable result.

## Change control

Use semantic spec versions: patch for clarification without behavior change,
minor for backward-compatible contract growth, major for breaking contract or
migration semantics. The repository may define a different convention, but one
revision must remain canonical.

Never duplicate live execution state, session IDs, current leases, transient
blockers, or changing commit hashes inside the spec. Link to their canonical
ledger instead.

## Final response

Report lifecycle state, canonical spec path and version/hash, decisions made,
open owner gates, work units authorized, acceptance evidence, scope drift,
rollback, and one next action. Do not claim implementation acceptance merely
because the written spec looks complete.

## Review convergence

Follow the [delivery contract](../nobrainer-ultra/references/delivery.md#keep-review-proportional-to-progress)
for slice-sized review and correction. Repeated amendments do not reset the
review budget. Keep concrete safety and acceptance blockers open; proceed with
authorized independent work instead of restarting a whole-plan perfection loop.
