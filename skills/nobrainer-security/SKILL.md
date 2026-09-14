---
name: nobrainer-security
description: "Use when the owner says nb-security or security-review, requests a threat model or security review, or when a change crosses authentication, authorization, secrets, untrusted input, sensitive data, dependency, installer, or production trust boundaries."
---

# NoBrainer Security

Find exploitable security defects and missing controls in one frozen scope, then
separate proven risk from checklist noise. Default to `READ_ONLY`. This skill
does not authorize attacking a live target, retrieving secrets, weakening a
control, changing credentials or implementing a fix.

## Choose one mode

- `THREAT_MODEL`: map assets, actors, entry points, trust boundaries, abuse
  paths and required controls before a consequential design is frozen.
- `SECURITY_REVIEW`: trace an exact diff, component, endpoint or data flow and
  report only reachable, actionable defects.
- `SUPPLY_CHAIN`: inspect an exact dependency, installer, plugin, script,
  workflow or external skill for provenance, pinning, permissions and execution
  risk.
- `RELEASE_GATE`: verify required security controls, tests, migration safety and
  rollback evidence before a high-risk release.

If the owner does not name a mode, infer from scope:

- an exact diff, component, endpoint or data flow -> `SECURITY_REVIEW`;
- a pre-freeze design -> `THREAT_MODEL`;
- a dependency, installer, plugin or workflow -> `SUPPLY_CHAIN`;
- pre-release acceptance -> `RELEASE_GATE`.

When modes overlap, choose the primary mode from the requested outcome and state
that choice; include relevant checks from adjacent modes without expanding scope.
Ask one focused clarification only if unresolved ambiguity materially changes
the outcome or authority. Continue independent read-only inspection meanwhile.

Use `nobrainer-review` for a general closeout with no material security boundary.
Use `nobrainer-rca` when the question is what caused an observed incident.

## Freeze scope and authority

Record:

```text
MODE:
SCOPE: <exact diff/files/component/endpoint/artifact>
ASSETS_AND_DATA:
TRUST_BOUNDARIES:
ATTACKER_CAPABILITIES:
ENVIRONMENT_AND_VERSION:
WRITE_AUTHORITY: READ_ONLY unless explicitly expanded
LIVE_TEST_AUTHORITY: NONE unless exact target and actions are approved
OWNER_GATES:
```

Resolve actual checkout, dirty state, deployed/runtime distinction, data
classification and existing controls. Never place credentials, full tokens,
private payloads or exploit-ready production details in prompts or reports.

Do not test a live target, scan infrastructure, create an account, send a
payload, access another user's data or install/run untrusted code without exact
authorization. Prefer local fixtures, static traces and isolated reproductions.

## Trace the trust boundary

Follow each relevant flow from attacker-controlled or externally supplied input
through validation, canonicalization, authorization, state changes and output.
For every boundary, establish:

- who controls the input and what identity/account/tenant it represents;
- parsing, normalization and validation order;
- authorization decision and its ownership point;
- storage, logging, cache, queue and retry behavior;
- sensitive output, side effect and failure mode;
- current guard and evidence that it runs on the real path.

Prioritize classes that fit the actual boundary: broken access control, confused
deputy, injection, SSRF, unsafe path handling, secret exposure, insecure
deserialization, XSS/CSRF, request smuggling, race/idempotence, unsafe defaults,
dependency or workflow substitution, and rollback bypass. Do not paste a generic
vulnerability list into findings.

When a material claim depends on current standards, advisories, dependency
behavior or vendor guidance, invoke `nobrainer-research` and prefer primary
sources for the exact version. If required current evidence is inaccessible,
return `RESEARCH_BLOCKED`; memory is not a security proof.

## Mode-specific evidence

### `THREAT_MODEL`

Produce a compact data-flow/trust-boundary map. For each plausible abuse path,
state precondition, attacker action, affected asset, existing control, residual
risk and one testable requirement. Rank by expected loss and reachability, not
by dramatic wording.

### `SECURITY_REVIEW`

Inspect the full changed function plus callers and consumers. Trace negative
paths and concrete boundary values. Run the smallest safe test or reproduction
that would distinguish a defect from a false alarm. A scanner result, model
finding or dependency label is only a candidate.

### `SUPPLY_CHAIN`

Resolve exact source, version/ref, integrity/pinning, release provenance,
license, install scripts, hooks, network calls, requested permissions,
credential access, write targets, update channel and rollback. Review the actual
artifact before executing it. Prefer temporary isolated use over global or
persistent installation.

### `RELEASE_GATE`

Map each security acceptance item to current code/config, a focused test,
runtime or migration evidence, and rollback. Static validation does not prove a
deployed control. Unknown production state remains unknown.

## Finding and false-positive gate

Report a defect only when all are present:

- severity with impact and realistic preconditions;
- exact location or trust boundary;
- attacker-controlled input/state/sequence;
- reachable code or runtime path;
- observable confidentiality, integrity or availability impact;
- why current controls fail;
- smallest ownership-correct fix contract;
- regression or verification proof.

Run a false-positive pass against every candidate: seek the guard, caller
constraint, deployment setting, parser behavior or version fact that would make
the path unreachable. Reject generic hardening, style preferences, stale
advisories for another version and speculative chains missing a necessary step.

## Handoff and remediation

Security review ends with evidence and a fix contract. If remediation is in
scope, route each accepted finding to `nobrainer-build` as a bounded stage with
a failing regression, allowed write scope and rollback. Then repeat the relevant
security trace with fresh evidence. Consequential fixes still require an
independent `nobrainer-review` or release gate; self-authored code is not
self-approved.

## Final report

```text
MODE: THREAT_MODEL | SECURITY_REVIEW | SUPPLY_CHAIN | RELEASE_GATE
SCOPE_AND_AUTHORITY:
ASSETS_AND_TRUST_BOUNDARIES:
FINDINGS: <severity, location, path, impact, fix contract, proof>
REJECTED_CANDIDATES:
TESTS_AND_SOURCES:
UNTESTED_OR_INACCESSIBLE_SURFACE:
OWNER_GATES:
ROLLBACK_OR_CONTAINMENT:
RESULT: FINDINGS | CLEAN | PARTIAL | BLOCKED | RESEARCH_BLOCKED
```

Return `CLEAN` only for the complete frozen scope with required evidence. A
partial review, inaccessible runtime or unverified external claim cannot be
green.
