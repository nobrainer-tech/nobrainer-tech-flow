## Problem

<!-- Describe the observed failure, missing workflow, or user friction. -->

## Scope and exclusions

<!-- Name the exact skills, adapters, scripts, or docs changed and what is out. -->

## Authoring environment

| Field | Value |
|---|---|
| Human or agent author | |
| Harness and version | |
| Model | |
| Relevant plugins | |

## Behavior evidence

<!-- For skill changes: baseline failure, changed behavior, adversarial controls, holdout. -->

## Compatibility evidence

<!-- SOURCE_VALIDATED, REPOSITORY_CHECKED, CLIENT_LOADED, RUNTIME_VERIFIED, or DISTRIBUTED. -->

## Verification

- [ ] `python3 scripts/validate_skills.py --suite`
- [ ] `python3 -m unittest discover -s tests -v`
- [ ] Changed scripts ran with their real interpreters
- [ ] Public-clean and secret scan completed
- [ ] Complete diff reviewed

## Public-surface coherence

- [ ] `PUBLIC_SURFACE: UPDATE` lists affected README/docs/templates/assets/flow, or `PUBLIC_SURFACE: NOT_NEEDED` includes a reason
- [ ] Every affected public surface was updated and read back
- [ ] Public contract, routing, workflow or portfolio changes refresh and read back both the workflow SVG and README Mermaid flow
- [ ] Unrelated diagrams and assets were not regenerated

## Risks, uncertainty, and rollback

<!-- State what is not proven and the exact rollback. -->

## Definition of Done

<!-- One status per gate: VERIFIED, GAP, UNKNOWN or N/A, with the evidence, next action
or scope reason. Missing access is UNKNOWN, never N/A. Gates:
skills/nobrainer-review/references/pr-definition-of-done.md. Refresh this block after
every push: a status for a replaced head is stale. -->

- Reviewed head:
- Requirements coverage:
- Target freshness:
- Local checks:
- Tests executed:
- Evidence:
- PR description:
- Review:
- Tracker records:

**Verdict:** <!-- Ready, Not ready or Readiness unknown, then the single next action. -->

## Owner gate

- [ ] A human owner has reviewed this complete PR before merge or publication
