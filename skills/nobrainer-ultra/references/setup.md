# Setup and upgrade protocol

Use this reference when the owner asks to set up, install, upgrade, repair or
reconcile NoBrainer workflows. Setup is a repeatable diff-and-readback operation,
not a one-time scaffold.

## 1. Discover before writing

Read the repository root, nearest instructions, dirty state, active client files,
skill locations, current specs/plans/wiki, tests, runtime and installed
capabilities. Classify each component:

- `CURRENT`: present, canonical and verified;
- `DRIFTED`: present but stale, duplicated or contradictory;
- `MISSING`: justified and absent;
- `NOT_NEEDED`: ceremony without a current use;
- `OWNER_GATE`: requires login, credential, marketplace action, consequential
  overwrite or another explicit decision.

Do not create SDD, a wiki, session registry, lease or adapter merely because a
template exists.

Use the smallest existing structure:

| Need | Artifact decision |
|---|---|
| One clear answer or edit | No new workflow files |
| Several steps in one session | Existing TODO or inline checklist |
| Safe resume after interruption | One existing tracker or task-local Markdown goal |
| Public contract, migration or dependent phases | Existing spec/ADR; a small new spec only if missing |
| Reusable decisions across tasks | Existing docs/wiki first; add an index only when retrieval needs it |

Reuse Spec Kit or another maintained project workflow when already present;
do not install a framework just to use SDD. TDD is useful when a reliable failing
test can expose changed behavior; use existing tests or direct artifact readback
for changes where a new test adds no evidence.

Choose and record `LEARNING_WRITE_POLICY: AUTO_SCOPED | ASK | OFF` for the
project. Use `AUTO_SCOPED` only with explicit standing owner authorization and a
resolved project-local wiki/instruction boundary. It never grants commit, push,
public disclosure or global-instruction authority.

## 2. Reconcile project instructions

Before adding rules, reconcile obsolete, duplicate and conflicting guidance
within the authorized project scope. Check approval pauses, default effort,
delegation and repeated verification. A model upgrade does not authorize a
global rewrite; use Ultra's instruction hierarchy and pause explanation.

Preserve existing content and managed blocks. Add or update exactly one marked
block only when equivalent durable routing is missing. Replace project-specific
placeholders with verified paths/commands and remove duplicate lines:

```markdown
<!-- NOBRAINER-WORKFLOW:START -->
## NoBrainer delivery

- Route non-trivial work through `nobrainer-ultra`; keep one-step tasks direct.
- Read the actual checkout, instructions, relevant wiki knowledge and tests first.
- Use one short requirements gate, freeze the minimum change and run the
  approved scope autonomously. Show a compact Progress checklist at meaningful
  transitions. Keep one canonical TODO owner.
- Use a detailed ledger only for multi-session, dependency-rich,
  consequential or explicitly resumable work; ordinary single-session work
  keeps the short checklist.
- Prefer the smallest complete change. Apply KISS and YAGNI; deduplicate owned
  knowledge, not incidental similarity; preserve cohesive dependency boundaries.
- Use `nobrainer-team`, `nobrainer-dispatcher` and `nobrainer-sessions` only for
  real capability, queued independent work, isolation, handoff, resume or
  critical-path parallelism.
- Research current material unknowns from primary sources; mark blocked research
  and never manufacture certainty.
- `PROBLEM_GATE`: start from the literal local failure and smallest reproducer;
  query only related wiki decisions when useful. Use current primary-source
  research when the remedy depends on an external, current, niche, uncertain or
  high-stakes fact. A stable local failure does not require browsing first. If
  required internet research is unavailable, return `RESEARCH_BLOCKED` and
  choose no remedy that depends on the missing evidence.
- Route material user-facing prose through `nobrainer-writing`; keep a tiny
  answer direct when it is already clear, specific and complete.
- Route authentication, authorization, secrets, sensitive data, untrusted input
  and supply-chain boundaries through `nobrainer-security`.
- Audit delegated results and verify the target workflow before completion.
- On an explicit owner decision change, update the canonical requirement,
  invalidate dependent TODO/evidence and re-plan from the earliest affected step.
- On an agent correction, fix the result, then follow the correction hooks and
  recorded `LEARNING_WRITE_POLICY`: `AUTO_SCOPED` may persist one authorized,
  project-local prevention rule; `ASK` prepares an exact diff; `OFF` persists
  nothing. Wiki promotion remains separately sourced, classified and governed.
- A failed review routes back through implementation and fresh verification;
  never reuse invalidated proof.
- Merge, deploy, publish, spend, delete, credentials and production mutation
  remain explicit owner gates unless exact authority is already recorded.
- Persist only authorized durable sourced learning; never secrets or live task state.
<!-- NOBRAINER-WORKFLOW:END -->
```

Require exactly one START and END marker in the correct order before replacing a
managed block. Preserve surrounding bytes. If instruction files must be equal,
compare them byte-for-byte after the change.

## 3. Install one canonical source

Prefer the active client's native plugin or Agent Skills mechanism. For a local
checkout, dry-run `scripts/install_skills.py`, inspect every target, then apply.
Existing foreign targets are conflicts, never overwrite candidates.

Install the complete curated fifteen-skill set unless the owner deliberately
requests an exact subset. Restart the client, read back loaded skills and run the
clean-session acceptance in `docs/COMPATIBILITY.md` when available. Files on
disk and an installer exit code prove installation only, not routing.

Do not retain an old private wrapper for a canonical public trigger. Before
removing one, verify semantic coverage, clean source history, the new runtime
target and a rollback ref. Remove only exact reviewed paths, never a broad
skills directory.

## 4. Reconcile capabilities

Use `nobrainer-team` to compare the fifteen curated skills, project-native tools
and active runtime. A missing specialist may be evaluated temporarily through
the open skills ecosystem only after source/ref, instructions, scripts, license,
permissions, network/credential behavior, trigger overlap and rollback are
reviewed. Persistent/global installation is an owner gate.

## 5. Choose justified artifacts and sessions

- Add a durable spec only for contracts, dependencies, migration, risk or
  resumability.
- Add a wiki only for reusable sourced knowledge beyond normal project docs.
- Create or reuse visible sessions only after an explicit owner request or an
  authorized MAIN restart. Independent work, isolation, handoff, resume or a
  warm specialist alone do not authorize a sidebar conversation; use native
  subagents or MAIN.
- Keep specification, detailed execution state, reports/evidence and wiki as
  separate owners; link rather than duplicate mutable facts.

## 6. Close with readback

```text
MODE: SETUP | UPGRADE | REPAIR
NOBRAINER_SOURCE:
SOURCE_REF:
CLIENTS_CONFIGURED:
SKILL_COUNT:
PROJECT_INSTRUCTIONS:
DETAILED_LEDGER: CURRENT | CREATED | UPDATED | NOT_NEEDED
SDD: CURRENT | CREATED | UPDATED | NOT_NEEDED
WIKI: CURRENT | CREATED | UPDATED | NOT_NEEDED
LEARNING_WRITE_POLICY: AUTO_SCOPED | ASK | OFF
CORRECTION_HOOKS: CURRENT | CREATED | UPDATED | NOT_NEEDED
TEAM_DISPATCHER_SESSIONS: CURRENT | CREATED | UPDATED | NOT_NEEDED
STATIC_CHECKS:
RUNTIME_CHECKS:
OWNER_ACTION_REQUIRED:
UNVERIFIED:
ROLLBACK:
```

Do not mark setup complete while required client discovery, routing behavior or
owner action is unknown. Separate local preparation from verified live runtime.
