# How nobrainer-tech-flow works

The detailed product guide moved here from the README, which is now a short landing page.
Install steps are in [INSTALL.md](INSTALL.md), client evidence in
[COMPATIBILITY.md](COMPATIBILITY.md) and release history in
[RELEASE-NOTES.md](../RELEASE-NOTES.md).

## What a finished task looks like

- **A handoff you can check.** Each finished task lists what was delivered,
  which checks ran and what was not checked. An optional evidence receipt marks
  a check `STALE` once its input files change, and a behavior-preserving rewrite
  reports `PROVEN`, `PARTLY_PROVEN` or `NOT_PROVEN` for whether the tests would
  catch a change.
- **A pause before risky commands.** With the Git install, optional Claude Code
  guards ask before `git push --force`, `git reset --hard`, a recursive delete
  outside temporary folders, a production deploy or a publish. A turn that
  changed files and ends without a proof line or an explicit `UNVERIFIED` is
  sent back once. After compaction, resume or clear, the agent is pointed back
  to the active goal file. Opt-in, with preview and undo.
- **One main loop, workers only where they pay.** The main session does the work
  with skills and hands a part to a native worker only for parallel work, context
  isolation, independent review or specialization, then checks each result.

## From idea or plan to delivery

Small, clear tasks take the quick path. Larger work is scoped, carried through and verified, and the handoff says what was delivered, what was checked and what is left for you to decide.

For an idea, [SDD](../skills/nobrainer-tech-flow/references/idea-to-delivery.md)
turns the agreed scope into a spec and checkable acceptance criteria. Ask for
end-to-end delivery, and those criteria stay attached to execution and evidence.
Routine choices need no extra prompt; material unknowns stay visible.
[Try idea to delivery](TRY_IT.md#from-an-idea-to-a-working-result).

For a supplied or generated plan, [autopilot](../skills/nobrainer-tech-flow/references/autopilot.md)
works through ready tasks, checks each result, corrects confirmed defects and
continues to the whole goal. Blocked work stays visible while independent tasks
advance. [Try a small approved plan](TRY_IT.md#carry-an-approved-plan-through-autopilot).

## The workflow in detail

New AI skills, workflows and add-ons keep arriving. nobrainer-tech-flow curates
the useful parts into one maintained path from task to a checked finish.

Say **“Use nobrainer-tech-flow”** (or invoke the technical entrypoint by the exact name your client lists for it) to fix code, prepare
an everyday document, or investigate a problem. Clear tasks go straight to execution;
meaningful ambiguity gets one focused question round. Done means the agreed
criteria are met and the result is checked. A real blocker is reported with the
next unblock action.

A quick answer stays a quick answer. The model-neutral workflow uses one plan,
bounded corrective attempts and a Markdown checkpoint for longer work. Native
goals, telemetry and client-specific tools are optional. Available native workers
take a unit only when it pays; unavailable workers leave the work in MAIN.

**One model is enough.** Optional Jev (remote) and Laya (local) profiles add
typed suggestions for bounded classification, ranking and evaluation. Setup
remembers your choice; the default makes no provider calls. Missing access or
failed requests return to the core workflow. See [setup and usage](../skills/nobrainer-tech-flow/references/optional-decisions.md)
for configuration, data approval and tested platform limits.

Team checks whether a task has the capabilities it needs. Research records
which sources were actually checked; Build names any known limit in an
accepted simplification. The current task stays central while specialist
tools remain optional.

New source links, public package/plugin IDs and checkout paths use
`nobrainer-tech-flow`. Existing installations with the previous
`nobrainer-tech-skills` ID need the reviewed migration path; an installed
legacy package does not automatically become the new package. See the
[migration guide](MIGRATION_TO_FLOW.md) and [naming map](NAMING.md).

## Delegation, output and language

Since 2.7.0, Flow delegates only where it pays (see [What a finished task looks like](#what-a-finished-task-looks-like)); the 2.3.0 note below is kept as history.

In **2.3.0**, non-trivial work delegates every useful independent ready unit to
native workers within verified capacity and authorized usage. MAIN coordinates,
advances the critical path, integrates and checks the results. Each audited
completion can release the next ready unit while other workers continue.
See the [delegation contract](../skills/nobrainer-tech-flow/references/delivery.md#coordinated-team-execution).

In **2.2.0**, simple answers stay text. Small diagrams explain relationships;
interactive HTML is used when controls help you explore a result. The closeout
states what was delivered, the inspected proof and any unfinished requirement.
There is no new module, renderer or service. See the
[communication policy](../skills/nobrainer-tech-flow/references/communication.md)
and [verification record](releases/v2.2.0.md).

Agents use plain technical English for operational exchanges; you receive
natural replies in your requested language. Explicit language and format
requests take precedence, with commands, conditions and evidence kept intact.

Writing defaults to [plain technical English](../skills/nobrainer-writing/references/plain-technical-english.md) for English technical artifacts:
clear steps and consistent terms while keeping exact commands, conditions and uncertainty.
The mode is informed by ASD-STE100; it does not claim full standard compliance.

## Astra Ready, portable by design

Since version **1.6**, ordinary work has no client-specific prerequisites.
OpenAI [introduced GPT-6 Astra](https://openai.com/index/gpt-6-astra/) on
September 3, 2026. The suite keeps the host-selected model and uses the same
plain-text instructions with other models; it does not pin a provider or choose
an expensive tier automatically.

[Compatibility](COMPATIBILITY.md) separates available models, tested
behavior, client loading and source distribution. Local smoke evidence covers
only its recorded source and scenarios. It is not a universal compatibility,
quality or token-savings benchmark.

User authority, transparent pauses and sufficient verification apply across
models. Historical runtime proof stays tied to the tested release bytes.

```text
Small task       -> direct result + relevant check
Larger task      -> clarify if needed + short TODO + execute + verify
Resumable task   -> same workflow + one Markdown goal/checkpoint
Independent work -> dispatch all useful ready native units; MAIN integrates and audits
```

Load specialists only when needed. Reuse the project's instructions, tests,
specs and wiki. Choose SDD for durable contracts and TDD when a failing test
would expose the behavior; neither requires installing a framework.

## Start with one skill

Use nobrainer-tech-flow through the canonical skill
[`nobrainer-tech-flow`](../skills/nobrainer-tech-flow/), for setup or any non-trivial
outcome. A small reversible edit without a public contract, routing, workflow or
portfolio change can use its quick path; other changes use the full path and its
coherence gate.
In Codex, type the exact name it lists for the module: `$nobrainer-tech-flow:nobrainer-tech-flow` after the installer, a plugin install or the npm package, and `$nobrainer-tech-flow` for a copy made with `install_skills.py --mode copy`. Say
`Use NBFlow`, `Use NBF` or `Use nobrainer-tech-flow` in natural language;
older trigger phrases are migration context only and
depend on a client's implicit description matching.

```text
DRIFT_CHECK -> BUDDY -> SCOPE -> AUTOPILOT -> VERIFY -> RECEIVE_AUDIT -> LEARN
```

- `BUDDY` is the first and only ordinary clarification stage.
- `SCOPE` freezes outcome, non-goals, expected files, proof, untouched work,
  minimum solution, test decision and clean completion before a non-trivial write.
- One canonical plan owns TODO state; the owner sees only a compact Progress
  checklist and one next action.
- A durable ledger adds exact identity, dependencies, checkpoints, retries and
  rollback only for cross-session, dependency-rich or consequential work, or
  when the owner keeps adding requests in one long conversation.
- `AUTOPILOT` continues through routine approved work without repeated check-ins.
- Work in one MAIN loop with skills. Delegate a unit to a native worker only for parallel
  work, context isolation, independent review or specialization, under the
  [delegation contract](../skills/nobrainer-tech-flow/references/delivery.md#coordinated-team-execution).
  MAIN coordinates, integrates and verifies. Team supplies
  capabilities; Dispatcher schedules real queues. Visible sessions require an
  explicit owner request or authorized MAIN restart.
- Failed review returns to `nobrainer-build`; changed code invalidates old proof.
- Merge, deploy, publishing, spending, credentials, destructive operations and
  production mutation remain owner gates unless exact authority is already
  recorded.

The two execution axes stay independent:

```text
CONTROL_MODE: BUDDY -> AUTOPILOT
SESSION_MODE: MAIN | MULTI_SESSION
```

For resumable or delegated work, `SESSION_HEALTH_GATE` uses available,
configured limits. Missing optional telemetry lowers the health claim and still
allows bounded safe work. An explicitly required hard budget must be enforceable.
`RUNTIME_RELEASE` concerns actual task-owned workers; a completed result does not
prove they stopped. `GOAL_FILE` is optional Markdown recovery state. A native goal
mirrors the DoD where the host offers one; the file alone suffices.

Autopilot works with one visible MAIN coordinator and bounded native workers.
Ordinary native assignments use the compact packet in the delegation contract,
exact returned IDs, observable completion and reviewed artifacts. Use persistent
sessions and a Dispatcher only when a real handoff or dependent queue needs them.
Native delegation does not authorize a new visible conversation.

## Eighteen skills, distinct ownership

Aliases are compatibility trigger phrases, not product names or duplicate
directories. Each skill owns one
recurring boundary:

| Skill | Alias | Responsibility |
|---|---|---|
| [`nobrainer-tech-flow`](../skills/nobrainer-tech-flow/) | `NBFlow`, `NBF` | Technical entrypoint for end-to-end setup and delivery: one requirements gate, concise progress, bounded execution, recovery, audit and learning |
| [`nobrainer-auto-fine-tune`](../skills/nobrainer-auto-fine-tune/) | `nb-auto-fine-tune` | Read-only capability audit and route calibration: verified host models, effort, context and useful parallelism while MAIN keeps the owner's model |
| [`nobrainer-context`](../skills/nobrainer-context/) | `nb-context` | One set of project instructions for every coding agent: what Codex, Claude Code, Gemini CLI, Cursor, Copilot and OpenCode load, size limits, duplicates and contradictions, one source of truth with pointers after approval, and readback |
| [`nobrainer-skill-doctor`](../skills/nobrainer-skill-doctor/) | `nb-skill-doctor` | Cross-project audit of skills, project instructions and task prompts: trigger overlap, excessive process, coverage and minimal portfolio repair planning |
| [`nobrainer-team`](../skills/nobrainer-team/) | `nb-team` | Capability selection and bounded native assignments, installed-skill inventory and safe temporary specialist discovery |
| [`nobrainer-dispatcher`](../skills/nobrainer-dispatcher/) | `nb-dispatcher` | Dependency-aware ready-set scheduling, bounded dispatch, backpressure and audited result routing |
| [`nobrainer-research`](../skills/nobrainer-research/) | `nb-research` | Bounded current research from primary sources with facts separated from inference |
| [`nobrainer-writing`](../skills/nobrainer-writing/) | `nb-write`, `nb-brief` | High-signal drafting, compression and short human-sounding comments, issues and stories that preserve meaning, evidence, voice and action |
| [`nobrainer-build`](../skills/nobrainer-build/) | `nb-build` | Smallest verified implementation using calibrated KISS, DRY, SOLID, YAGNI and anti-slop gates |
| [`nobrainer-security`](../skills/nobrainer-security/) | `nb-security` | Threat models, security review, supply-chain audit and high-risk release evidence |
| [`nobrainer-sessions`](../skills/nobrainer-sessions/) | `nb-sessions` | Named visible sessions, exact identity, isolated writers, audited handoff, lease and recovery |
| [`nobrainer-spec-driven-development`](../skills/nobrainer-spec-driven-development/) | `nb-sdd` | Durable specification and acceptance ledger when contracts, risk or resumability justify it |
| [`nobrainer-wiki`](../skills/nobrainer-wiki/) | `nb-wiki` | Targeted retrieval and sourced durable knowledge without hidden memory or live task state |
| [`nobrainer-browser`](../skills/nobrainer-browser/) | `nb-browser` | Playwright-first rendered inspection, bounded CDP profile restart, approved session attach, browser tests and trace evidence |
| [`nobrainer-autoimprove`](../skills/nobrainer-autoimprove/) | `nb-autoimprove` | Measured baseline/variant/eval/holdout improvement with keep-or-revert |
| [`nobrainer-decide`](../skills/nobrainer-decide/) | `just decide` / `just-decide` / `decide` / `nb-decide` / `nobrainer-decide` / `deep decide` / `deep-decide` | Quick, standard or deep decisions; feasibility, reliability, total cost, delivery time and practical growth before commitment |
| [`nobrainer-rca`](../skills/nobrainer-rca/) | `nb-rca` | Read-only causal diagnosis with a continuous evidence chain and explicit uncertainty |
| [`nobrainer-review`](../skills/nobrainer-review/) | `nb-review` | Acceptance trace, adversarial bug hunt and release close gate without speculative findings |

The [curation audit](SKILL_CURATION.md) records why each skill exists and
what belongs in another skill instead of becoming an unnecessary trigger.

## SDD and GDD

SDD specifies what must work. GDD (Goal-Driven Development) executes it through
accepted milestones under one overarching goal. See the [product specification](specs/goal-driven-delivery.spec.md).

For substantial work, `nobrainer-tech-flow` derives the outcome and DoD and keeps
one task owner without waiting for a separate planning request. Native goal
creation still follows the host's explicit-request requirement. Autopilot checks
available authorized UI/API/CLI steps before handing an obstacle to the owner,
continues independent work, and bounds review to concrete executable slices.
Explicit `yolo` requests select the same persistence contract, without changing
permissions or bypassing a denial. See the [delivery contract](../skills/nobrainer-tech-flow/references/delivery.md).
These are agent instructions, not an enforcement daemon or a promise to run
while the host is paused or out of quota.

## Correct once, improve permanently

nobrainer-tech-flow contains portable semantic hooks for four events:

- `OWNER_DECISION_CHANGED` updates the canonical decision, marks the old value
  superseded and invalidates dependent TODO items and evidence;
- `AGENT_ERROR_CORRECTED` fixes the active result and classifies one minimal
  prevention candidate: `AUTO_SCOPED` may persist it to one governed canonical
  project-local store, `ASK` prepares one exact diff, and `OFF` keeps it
  task-local without a durable diff;
- `REVIEW_FAILED` creates a bounded Build correction and sends fresh evidence
  back to Review;
- `REPEATED_DEFECT` stops blind retries and invokes RCA with the prior failure
  fingerprint.

Only durable, sourced, authorized and non-secret knowledge is promoted through
`nobrainer-wiki`. One mutable fact has one canonical owner; the system does not
append contradictory copies to the plan, instructions and wiki.
Project setup records `LEARNING_WRITE_POLICY: AUTO_SCOPED | ASK | OFF`, so an
owner can enable automatic project-local learning without granting global or
publishing authority.

## Quality without AI slop

The shared delivery contract operationalizes:

- `KISS`: the simplest complete design wins;
- `YAGNI`: no speculative extension points or future options;
- `DRY`: deduplicate owned knowledge and state, not incidental similarity;
- `SOLID`: cohesive responsibilities and stable boundaries without class or
  interface ceremony;
- evidence: no invented APIs, fake runtime claims, placeholder logic, swallowed
  errors, generic prose, broad unrelated rewrites or mock-only confidence;
- content quality: purpose, audience, correctness sources, completeness,
  coherence and target-workflow usefulness are frozen before execution.

If a decision-relevant fact may be current, niche, uncertain, high-stakes or
source-attributed, nobrainer-tech-flow routes the smallest sufficient check through Research.
A stable local syntax, import, test or configuration error starts from local
evidence instead of an automatic wiki/web detour. If required primary evidence
is unavailable, it says `RESEARCH_BLOCKED` instead of guessing.

## Compatibility is a proof ladder

All clients consume the same `skills/` tree. Thin adapters cover Claude Code,
Codex, Cursor, OpenCode, Gemini CLI, Kimi Code and Pi; the portable Agent Plugin
manifest and project instructions are the fallback for other Agent Skills
consumers.

Compatibility claims use six distinct levels:

```text
SOURCE_VALIDATED -> REPOSITORY_CHECKED -> CLIENT_LOADED
                 -> RUNTIME_VERIFIED_EXPLICIT -> RUNTIME_VERIFIED -> DISTRIBUTED
```

A valid manifest does not prove clean-session routing. A local test does not
prove production. See [Compatibility](COMPATIBILITY.md) for current proof
and [Testing](TESTING.md) for acceptance evidence.

## One source, thin adapters

```text
skills/               canonical portable behavior
adapters/bootstrap.md small session-start route to nobrainer-tech-flow
hooks/                tested client lifecycle adapters
scripts/              validation and conflict-safe installation
tests/                deterministic and behavior-contract gates
docs/                 compatibility, curation, eval and release evidence
assets/               brand and workflow diagrams
```

Client-specific forks of a skill are prohibited. Team fills a capability gap
with a task-local specialist brief for a native worker; it never searches for,
installs or runs third-party skills. Installing anything is the owner's own
separate decision.

## Adaptive session restart

On explicit task invocation, nobrainer-tech-flow immediately names the conversation
`<task title> | started DD-MM` using its verified creation date and preserves it
on resume. It assesses context before work, after compaction and at accepted
milestones. Adaptive care uses recorded task authority and respects `off` and
stricter host rules; installing the package alone enables no session mutation.

A pressured session with a materially smaller full startup can rotate even when
token payback is unknown. Age and compaction count alone do not force rotation.
nobrainer-tech-flow preserves progress in the task file, verifies successor takeover and archives
the source only when authorized. The full timestamp, timezone and exact session
ID stay authoritative. Unsupported clients receive an explicit manual handoff.

This belongs to [Sessions](../skills/nobrainer-sessions/references/session-restart.md),
not a separate skill. The optional stdlib [decision helper](../skills/nobrainer-sessions/scripts/restart_gate.py)
can serve a client hook without requiring one. Automatic startup care has shipped since v1.10.0;
native transport and all-client savings are not implied. See [session restart](SESSION_RESTART.md).

## Attribution

- `nobrainer-autoimprove` is an independent adaptation of Andrej Karpathy's
  [autoresearch](https://github.com/karpathy/autoresearch) measure-change-keep
  loop.
- `nobrainer-wiki` is an independent adaptation of Andrej Karpathy's
  [LLM wiki concept](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f).
- Other external design sources remain cited inside the exact skill where they
  influenced a behavior contract.
