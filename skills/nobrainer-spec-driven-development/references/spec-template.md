# Specification template

Reuse the project's established location and naming. If none exists, prefer a
small `docs/specs/<topic>.spec.md` convention. Replace placeholders before
approval; unknown safety- or acceptance-critical values remain explicit gates.

```markdown
# <title>

SPEC_ID: <stable ID>
VERSION: 0.1.0
STATUS: DISCOVERY | DRAFT | REVIEW | APPROVED | IMPLEMENTING | SPEC_CHANGE_PROPOSED | VERIFYING | ACCEPTED | BLOCKED | SUPERSEDED
OWNER: <person or role>
APPROVED_BY: NONE
APPROVED_AT: NONE
SPEC_HASH: NONE

## Outcome and audience

OUTCOME: <observable result>
AUDIENCE: <user/operator/system>
QUALITY_CONTRACT: <correctness, completeness, coherence, target review>

## Sources and rulings

| ID | Type | Source/evidence | Ruling |
|---|---|---|---|
| SRC-1 | OBSERVED / INFERRED / RECOMMENDED / UNKNOWN | <reference> | <effect> |

## Scope

IN_SCOPE:
- <item>

EXCLUDED:
- <item>

NON_GOALS:
- <item>

## Contract

### Inputs and validation

- <exact input, type, limits, trust boundary>

### Outputs and interfaces

- <observable output, schema/protocol compatibility>

### Invariants and side effects

- <state write, event, log, notification, cost>

### Failures and idempotence

- <error behavior, retry, resume, duplicate handling>

### Constraints

- SECURITY: <constraint or NOT_APPLICABLE>
- PRIVACY: <constraint or NOT_APPLICABLE>
- PERFORMANCE: <budget or NOT_APPLICABLE>
- COMPATIBILITY: <contract or NOT_APPLICABLE>
- OPERATIONS: <monitoring/runtime/deployment constraint>

## Components and write boundary

| Component | Allowed change | Owner | Dependency | Parallel-safe |
|---|---|---|---|---|
| <name> | <paths/interfaces> | <role> | <ID/NONE> | YES/NO |

## Requirements and ACCEPTANCE ledger

| REQ_ID | Requirement | ACCEPTANCE_ID | Evidence/command | Required gate |
|---|---|---|---|---|
| REQ-1 | <must be true> | ACC-1 | <test/verifier/readback> | LOCAL/RUNTIME/OWNER |

## Migration, recovery and ROLLBACK

- BASELINE: <current behavior and evidence>
- MIGRATION: <sequence or NOT_APPLICABLE>
- CHECKPOINT: <recovery point>
- ROLLBACK: <exact reversible procedure>
- ROLLBACK_READBACK: <proof that rollback worked>
- STOP_CONDITIONS: <conditions that forbid progress>

## Decisions and owner gates

| DECISION_ID | Question | Options/evidence | Owner | Status |
|---|---|---|---|---|
| DEC-1 | <question> | <bounded options> | <owner> | OPEN/RESOLVED |

## Review

- CONTRADICTION_SCAN: NOT_RUN
- COMPLETENESS: NOT_ASSESSED
- ACCEPTANCE_COVERAGE: 0%
- ROLLBACK_REVIEW: NOT_ASSESSED
- REVIEWERS: NONE

## Approval

- APPROVED_VERSION: NONE
- APPROVED_HASH: NONE
- IMPLEMENTATION_MAY_START: NO
```

Before setting `IMPLEMENTATION_MAY_START: YES`, ensure all acceptance-critical
unknowns are resolved or owner-gated, every requirement is covered, and the
stored hash matches the reviewed content.

`SPEC_CHANGE_PROPOSED` blocks implementation until the revised spec is reviewed
and approved.
