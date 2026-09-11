---
name: nobrainer-build
description: "Use when the owner says nb-build, engineering-standards, or nobrainer-simplifier, or asks to implement or simplify an approved bounded code, configuration, documentation, or test change after outcome and acceptance are clear; apply the smallest verified edit with calibrated KISS, DRY, SOLID, YAGNI and anti-slop gates."
---

# NoBrainer Build

Implement one bounded work unit without expanding the product or hiding weak
evidence behind polished output. This skill owns the edit loop. Route ambiguous
requirements to `nobrainer-ultra`, causal diagnosis to `nobrainer-rca`, and the
independent close gate to `nobrainer-review`.

## Start gate

Use the actual task workspace, including an ordinary folder without Git. Repository,
branch, commit and build fields are `NOT_APPLICABLE` when absent; do not initialize
Git or request a repository merely to deliver an artifact. Verify documents through
their source facts, acceptance and content/rendered readback.

Before the first write, resolve:

- observable outcome and acceptance IDs or checks;
- exact repository, checkout, dirty state, write scope and exclusions;
- expected files with one reason each, plus protected untouched files;
- relevant instructions, current callers/consumers and baseline behavior;
- cheapest useful failing proof, target tests, broader verifier/build/runtime;
- side effects, owner gates, rollback and the `Done clean` condition.

Preserve unrelated changes. Use an isolated worktree or disjoint write scope
when another writer is active. If a missing requirement changes architecture,
scope, public behavior or safety, stop at `SPEC_CHANGE_PROPOSED`; do not invent it
inside the patch.

## Engineering gate

Apply these principles as decision rules, not slogans:

- `KISS`: choose the simplest complete design that satisfies acceptance.
- `YAGNI`: do not add extension points, compatibility layers or options for an
  unproven future requirement.
- `DRY`: keep each rule and mutable fact under one owner, but do not abstract
  incidental similarity. Duplication can be cheaper than the wrong coupling.
- `SOLID`: preserve cohesive responsibilities and stable dependency boundaries;
  this is not a mandate for object-oriented ceremony, tiny classes or needless
  interfaces.

Before writing, stop at the first complete option that satisfies acceptance:

1. skip or delete work when the outcome already exists or the artifact is unnecessary;
2. reuse existing code or a maintained project capability;
3. use the standard library or native platform;
4. use an already-installed dependency;
5. add the minimum local implementation.

Configuration owns values that vary by environment or run; code owns invariants.

A new shared abstraction requires two real current callers or an explicit
acceptance contract that needs the boundary. A hypothetical future caller does
not justify it. If inspection expands the expected file set, update scope before
editing the newly required file.

## Anti-slop gate

Reject a patch that contains any of the following without explicit acceptance:

- invented APIs, packages, commands, files, facts or runtime claims;
- placeholder logic, fake data, swallowed errors or success on partial output;
- comments that restate visible code, generic generated documentation or
  self-congratulatory best-practice prose;
- broad renames, formatting churn or neighboring refactors unrelated to the
  work unit;
- duplicate state owners, speculative abstractions or fallback stacks that make
  failure ambiguous;
- tests that only assert a mock/fixture while the real contract remains
  unexercised.

Names should explain intent. Comments should explain only non-obvious why,
constraints, risk or tradeoffs. Do not create a new README, framework or process
artifact merely to make the change look substantial.

## Build loop

1. Re-open the relevant source and tests from disk. Trace the affected behavior
   through its caller and consumer boundary.
2. For a behavior change, create a failing proof before implementation when it
   is feasible and reliable. Otherwise record why and preserve the closest
   reproducible baseline.
3. Make the smallest coherent patch. Keep one behavioral concern per change and
   update the expected file set for routine changes within the approved outcome;
   stop only when the actual approved scope or consequences change.
4. Run the focused proof, then affected baseline tests and the repository's
   required verifier/build/runtime in increasing cost order.
   Once acceptance and required checks pass, broaden or repeat only for a new
   change, failure or unresolved concern.
   Before changing shared fixtures, runners, mocks, defaults or test
   infrastructure, inventory all consumers and run at least one representative
   suite per affected behavior class. A test-helper cleanup must not silently
   change unrelated projects' defaults.
5. Re-read the final diff and run an acceptance trace from promised outcome back
   through output, state, caller, validation and source data.
   Perform a behavior-preserving simplification pass: remove unused indirection,
   duplicate state and needless fallback layers only when references and tests
   prove the simpler path. Do not compress readable code merely to reduce lines.
   Check `Done clean`: actual files match the expected scope, no unexpected
   status entry remains, and no placeholder or speculative layer survived.
   If a pull request is part of the authorized delivery, bind its reported checks
   and review state to the exact current head SHA; evidence from a replaced head is
   stale.
6. Route a consequential or user-requested final gate to `nobrainer-review`.
   Every fix invalidates earlier evidence for the changed path and must be
   rechecked.

A command exit code proves only that command. Distinguish static validation,
local runtime, deployed runtime, production behavior and user usefulness.

If the work crosses authentication, authorization, secrets, sensitive data,
untrusted input, dependency installers or another trust boundary, add a bounded
`nobrainer-security` stage before final acceptance.

## Stop and owner gates

Pause the affected operation on changed frozen inputs, conflicting writer, failed required check,
unknown destructive effect, missing credentials/toolchain or a scope-changing
decision. Merge, deploy, publish, spend, delete, migrate data, change credentials,
mutate production or weaken safety controls only with their explicit authority.

A failed check routes to repair; a missing tool or credential routes through
[delivery obstacle resolution](../nobrainer-ultra/references/delivery.md). Check
permitted alternatives and continue independent work before reporting BLOCKED.

Do not push through three failed fix-like attempts. Preserve the failing proof,
return to `nobrainer-rca` or revise the design with the owner.

## Build report

This schema is an audit input for Ultra or another machine handoff. In ordinary
conversation, translate it into a short natural-language outcome, evidence,
uncertainty, rollback and next action instead of dumping the form.

```text
RESULT: FINISHED | BLOCKED | FAILED | SPEC_CHANGE_PROPOSED
WORK_UNIT:
FILES_CHANGED:
ACCEPTANCE_TRACE:
FAILING_PROOF_BEFORE:
TARGETED_CHECKS:
BROADER_CHECKS:
RUNTIME_EVIDENCE:
REVIEW:
SIDE_EFFECTS:
UNVERIFIED:
ROLLBACK:
NEXT_ACTION:
```

Report `FINISHED` only when the approved work unit and required evidence pass.
Do not claim merge, deployment or production state without readback from that
system.
