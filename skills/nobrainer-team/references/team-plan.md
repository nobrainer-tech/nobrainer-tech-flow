# Team plan template

Use this only after work units and acceptance exist. Keep one canonical plan;
do not duplicate live state or session IDs in unrelated documents.

```text
TEAM_PLAN_ID:
OUTCOME:
ACCEPTANCE:
MAIN_SESSION_TITLE: <repo> | MAIN
SESSION_MODE: MAIN | MULTI_SESSION
MAX_ACTIVE_WORKERS:
ATTENTION_BUDGET:

WORK_UNITS
  - ID:
    OUTCOME:
    METHOD: NOBRAINER_SKILL | PROJECT_NATIVE | TEMPORARY_REVIEWED_SKILL | DIRECT
    CAPABILITY:
    CAPABILITY_SOURCE_REF:
    OWNER_ROLE:
    SESSION_TITLE:
    DEPENDENCIES:
    PARALLEL_GROUP:
    INPUTS:
    WRITE_SCOPE:
    EXCLUDED_SCOPE:
    ACCEPTANCE:
    EVIDENCE:
    REPORT_TO:
    STOP_CONDITION:
    ROLLBACK:

CAPABILITY_GAPS:
EXTERNAL_SKILL_AUDITS:
REJECTED_ROLES_AND_REASON:
EXPECTED_CRITICAL_PATH_GAIN:
COORDINATION_COST:
OWNER_GATES:
```

For each external candidate record exact source/ref, discovered name, inspected
files, scripts not run, permissions, network/credential behavior, trigger
overlap, license, temporary-use method and removal/rollback.
# Capability coverage for durable plans

Use the existing plan to record: needed capability, applicable dimension,
searched candidate IDs, selected ID/source/ref, rejected IDs with reasons,
reviewed-file hashes, evidence and unresolved gap. Record `UNKNOWN` for a need
not yet checked, `CAPABILITY_GAP` for a checked need with no suitable capability,
and `NOT_APPLICABLE` for a dimension deliberately excluded. Review architecture,
runtime, framework, domain, data, integrations, tests, security, UX, operations and maintenance when
they apply. A selected skill name alone cannot close the coverage row.

Do not create a durable selection artifact for one obvious local operation.
On later reuse, compare reviewed source/ref and hashes before trusting a
selection. Hash every reviewed file with SHA-256, including unexecuted references
and scripts. Keep this record with the approved plan and evidence, not a separate
mutable catalog that can drift from the actual assignment.
