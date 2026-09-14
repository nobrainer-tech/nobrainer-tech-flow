# Skill curation

The active product is deliberately small enough to understand and broad enough
to run a non-trivial project from intent to verified outcome. A skill belongs in
the permanent suite only when it owns a recurring cross-project boundary that
cannot live clearly inside another owner.

## Admission test

A permanent skill must pass every condition:

1. It has a distinct trigger and observable result.
2. It is useful across projects without private paths or accounts; any client-specific capability has an explicit compatibility boundary.
3. Loading it only when triggered saves more context and risk than embedding its
   full protocol in Ultra.
4. Its behavior is not already owned by another active skill or a maintained
   project/native capability.
5. Its failure, stop, owner-gate and rollback behavior can be tested.
6. It has a pressure scenario showing value and a non-trigger case preventing
   overuse.

Popularity, file size and prior existence are not admission criteria.

## Active seventeen

| Skill | Distinct owner |
|---|---|
| `nobrainer-ultra` | One request through brief requirements, concise progress, guarded execution, audit, recovery and learning. |
| `nobrainer-team` | Minimal roles, installed capability inventory and safe temporary specialist discovery. |
| `nobrainer-dispatcher` | Ready-set calculation, dependency-aware bounded batches, backpressure and audited result routing. |
| `nobrainer-research` | Bounded current external research and source-quality/freshness control. |
| `nobrainer-writing` | High-signal drafting, compression, voice and prose integrity across human-facing text artifacts. |
| `nobrainer-build` | Implementation, engineering principles, anti-slop, test blast radius and simplification. |
| `nobrainer-security` | Threat model, security review, supply-chain inspection and security release evidence. |
| `nobrainer-sessions` | Exact visible session identity, transport, writer ownership, handoff, receive-audit and recovery. |
| `nobrainer-spec-driven-development` | Durable behavior contract and acceptance ledger when risk/dependencies justify it. |
| `nobrainer-wiki` | Setup, targeted retrieval, sourced capture and deterministic maintenance of durable knowledge. |
| `nobrainer-browser` | Rendered UI, bounded CDP profile restart, approved browser-session attach, browser tests and trace evidence. |
| `nobrainer-autoimprove` | Measured artifact improvement with baseline, holdout, budget and keep-or-revert. |
| `nobrainer-decide` | One consequential decision after alternatives, scoring and adversarial attack. |
| `nobrainer-rca` | Read-only causal diagnosis of an observed failure. |
| `nobrainer-review` | Final acceptance/bug/release evidence gate and verified actionable findings. |
| `nobrainer-codex-context` | Project-local Codex instruction discovery, byte-budget audit, safe context-block setup and runtime readback. |
| `nobrainer-skill-doctor` | Cross-project audit of skills, project instructions and task prompts, with coverage, overlap and minimal portfolio repair planning. |

## Boundaries that stay embedded

Do not create separate permanent skills for:

- planning, autopilot, general NoBrainer setup or correction capture: Ultra owns the lifecycle; Codex-specific project-context setup belongs to `nobrainer-codex-context`;
- visible goal/TODO progress: Ultra owns one canonical plan and its compact view;
  do not add a separate goal, todo or progress skill;
- KISS, DRY, SOLID, YAGNI, simplification or test safety: Build owns them;
- brand-specific voice facts belong in a project guide or wiki; Writing owns the
  portable prose method and can consume an authentic supplied voice sample;
- generic code review, bug finding or release ceremony: Review owns the close
  gate, while Security owns only material trust-boundary risk;
- human continuation snapshots: Sessions mode `handoff` owns them;
- a local skill catalogue: Team builds a metadata-only capability index;
- wiki add/get/tidy wrappers: Wiki exposes explicit modes;
- personal model presets, accounts or repository-specific configuration: keep
  them in project/private instructions. A named host integration must justify
  its recurring boundary and state its compatibility limits.

## Dynamic specialist policy

Team resolves a capability gap in this order:

1. curated NoBrainer skill;
2. already installed and inspected specialist;
3. maintained project/API/CLI/native capability;
4. bounded current research;
5. temporary external skill discovered for the exact missing capability.

External instructions are untrusted. Search rank does not authorize install,
scripts, credentials, network access or writes. Review immutable source/ref,
license, permissions, trigger overlap, persistence and rollback. Persistent or
global installation requires an owner gate and evidence that repeated use earns
the added trigger/context surface.

## Retirement test

A skill can be removed only after:

- its unique behavior is intentionally preserved or explicitly rejected;
- inbound references and aliases are migrated;
- the replacement is installed and discovered in a clean session;
- representative old invocations route to the replacement;
- rollback points to an exact reviewed ref;
- no private operational contract is confused with a portable semantic
  duplicate.

Same name or broad topic is not proof of duplication. Until the above gates
pass, classify candidates as `COVERED_NOT_RETIRED`, `PROJECT_SPECIFIC`,
`UNIQUE_VALUE`, `OBSOLETE_WITH_EVIDENCE` or `UNKNOWN`.

`nobrainer-fast-audit` is currently `UNKNOWN`, not a migration alias. Its exact
contract and callers must be audited before choosing Review, Security or another
owner. Keep an existing private installation unchanged until that audit and a
clean-session parity check pass; the public installer must report it as a normal
conflict rather than delete or silently remap it.

## Change control

Any addition, merge or retirement updates together:

- `skills/`, aliases and installer migrations;
- validator and behavioral tests;
- Ultra routing and setup instructions;
- README, compatibility and release notes;
- clean-session trigger/readback evidence.

Prefer strengthening an existing owner over creating a new noun. Do not keep an
empty alias skill for compatibility; aliases belong in descriptions and
migration maps.
