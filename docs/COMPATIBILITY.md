# Compatibility evidence

NoBrainer Tech Flow keeps one portable `skills/` source, but portability is
not the same as a proven client integration. Record these levels separately:

1. `SOURCE_VALIDATED` — the portable `SKILL.md` folders pass repository
   validators; this makes no client claim.
2. `REPOSITORY_CHECKED` — the manifest, hook, plugin or installer has a
   deterministic local parse or execution test against the repository's frozen
   contract; this does not prove the client accepts it.
3. `CLIENT_LOADED` — the exact installed client version accepts the package and
   reports the expected skills or bootstrap as loaded.
4. `RUNTIME_VERIFIED_EXPLICIT` — a clean client session loads and follows the
   canonical body under explicit invocation; this does not prove discovery.
5. `RUNTIME_VERIFIED` — a clean client session discovers and follows
   `nobrainer-ultra` without manually pasting its body.
6. `DISTRIBUTED` — the exact release is available through the claimed public
   marketplace or install channel and was read back after installation.

Never promote one level from evidence belonging to another.
Merge is a repository delivery state, not a client-compatibility level; release
evidence records it separately.

The current source version is **1.9.0**. Its scope and installation metadata are
recorded in the [v1.9.0 release record](releases/v1.9.0.md). The naming migration
remains documented in the [migration guide](MIGRATION_TO_FLOW.md), and the
unchanged command runner keeps its [v1.7.0 evidence](releases/v1.7.0.md). The
published `v1.8.0` release remains the rollback anchor; this source update does
not claim a GitHub release, client loading or marketplace distribution.

The [1.6.1 instruction review](reviews/2026-09-05-astra-instructions.md)
clarifies skill precedence and sufficient verification. Its evidence is a
source-contract review; the v1.6 runtime results apply only to the archived
release bytes. It adds no model-wide or cross-client runtime claim.

The source channel was `DISTRIBUTED` for `v1.5.0`, with its exact historical
merge, tag and installation in the [publication evidence](releases/v1.5.0-publication-readback.md).
That record and [v1.3.1](releases/v1.3.1-publication-readback.md) remain rollback evidence. Pin a reviewed full
commit SHA when immutability matters. Neither source publication nor an installed
folder proves marketplace acceptance or model behavior.

## Model-neutral readiness

`WORKFLOW_READY` is a product-positioning label, not a seventh compatibility
level. It means the portable policy can carry a selected model, effort, budget
and escalation gate; it does not prove that a provider exposes or follows that
policy.

| Model / family | Workflow posture | Runtime evidence |
|---|---|---|
| GPT-6 Astra | `WORKFLOW_READY`: host-selected policy, optional native capabilities | Bounded v1.6 Codex behavioral probes; exact source and limits in the [release evidence](releases/v1.6.0.md) |
| Other OpenAI models | Same portable instructions and policy | Only exact tested model IDs in the release evidence; no family-wide pass |
| Claude models | Same portable instructions and policy | Historical explicit client evidence below; no automatic claim for a new model |
| Other models / clients | Portable Markdown plus available tools | Unverified until tested in that host |

OpenAI [announced GPT-6 Astra](https://openai.com/index/gpt-6-astra/) on
2026-09-03. Names and access change; inspect the host's actual model list rather
than treating this document as a model catalogue. No provider is a dependency.

`v1.0.0` remains a separately verified nine-skill rollback anchor with its own
[publication readback](releases/v1.0.0.md).

The v1.3.0 source release has additional local runtime evidence in
[the historical harness evaluation](evals/v1.3.0-harness-clarity-2026-08-30.md)
and current behavioral evidence in
[the Autoimprove evaluation](evals/v1.3.0-autoimprove-integrity-2026-09-01.md).
The older client transcripts remain hash-scoped and do not silently upgrade to
marketplace or automatic-routing claims. Both clients retain explicit-runtime
evidence only; automatic routing and client publication remain unverified.

## Adapter contracts and historical client evidence

`REPOSITORY_CHECKED` below means deterministic repository tests passed. It does
not mean the external client's parser accepted or loaded the package.

| Client / harness | Source | Repository contract | Client load | Runtime | Distribution |
|---|---|---|---|---|---|
| Claude Code | `SOURCE_VALIDATED` | `REPOSITORY_CHECKED`: manifest, portable installer and Claude SessionStart output | `CLIENT_LOADED`: CLI `2.1.241`, isolated plugin, namespaced explicit invocation | `RUNTIME_VERIFIED_EXPLICIT`: final Ultra routed to and read canonical Autoimprove; automatic routing remains unverified | `NOT_PUBLISHED` |
| Codex | `SOURCE_VALIDATED` | `REPOSITORY_CHECKED`: accepted manifest schema and portable installer | `CLIENT_LOADED`: CLI `0.149.1`, repo-scoped copy, explicit canonical invocation | `RUNTIME_VERIFIED_EXPLICIT`: final Luna cases and isolated implementation passed; automatic and alias-only routing remain unverified | `NOT_PUBLISHED` |
| Cursor | `SOURCE_VALIDATED` | `REPOSITORY_CHECKED`: manifest path and Cursor SessionStart output | `NOT_VERIFIED` | `NOT_VERIFIED` | `NOT_PUBLISHED` |
| OpenCode | `SOURCE_VALIDATED` | `REPOSITORY_CHECKED`: skills registration plus idempotent first-user transform | `NOT_VERIFIED` | `NOT_VERIFIED` | `NOT_PUBLISHED` |
| GitHub Copilot CLI | `SOURCE_VALIDATED` | `REPOSITORY_CHECKED`: portable installer and repository instructions; no bootstrap | `NOT_VERIFIED` | `NOT_VERIFIED` | `NOT_PUBLISHED` |
| Gemini CLI | `SOURCE_VALIDATED` | `REPOSITORY_CHECKED`: extension manifest and owned context include | `NOT_VERIFIED` | `NOT_VERIFIED` | `NOT_PUBLISHED` |
| Kimi Code | `SOURCE_VALIDATED` | `REPOSITORY_CHECKED`: canonical skills path, Ultra session-start field and native-tool boundary | `NOT_VERIFIED` | `NOT_VERIFIED` | `NOT_PUBLISHED` |
| Devin CLI | `SOURCE_VALIDATED` | no dedicated adapter | `NOT_VERIFIED` | `NOT_VERIFIED` | `NOT_PUBLISHED` |
| Pi | `SOURCE_VALIDATED` | `REPOSITORY_CHECKED`: package resources, dedupe, lifecycle reset and post-compaction transform | `NOT_VERIFIED` | `NOT_VERIFIED` | `NOT_PUBLISHED` |
| Hermes Agent | `SOURCE_VALIDATED` | `REPOSITORY_CHECKED`: root Agent Plugins v1 manifest only; no bootstrap | `NOT_VERIFIED` | `NOT_VERIFIED` | `NOT_PUBLISHED` |
| Antigravity and other plugin hosts | `SOURCE_VALIDATED` | no host-specific contract | `NOT_VERIFIED` | `NOT_VERIFIED` | `NOT_PUBLISHED` |
| Generic Agent Skills consumers | `SOURCE_VALIDATED` | canonical folders only | `NOT_VERIFIED` | `NOT_VERIFIED` | `NOT_PUBLISHED` |

Adapter checks apply to the current source. The client/runtime cells retain their
recorded historical versions and hashes; they do not silently transfer to v1.6.
Consult the v1.6 evidence for new probes. There is deliberately no blanket “works everywhere”
badge: an unknown harness gets portable skill folders, then needs its own
discovery/bootstrap proof before promotion.

## Adapter contract

All adapters point at the same fifteen directories. They may expose discovery and
one small `NOBRAINER_BOOTSTRAP_V1` routing context, but they must not copy or
rewrite skill bodies.

- Claude and Cursor hooks emit exactly one platform-specific JSON field.
- OpenCode and Pi inject once per relevant context and detect their marker;
  Pi permits one re-injection after compaction.
- Gemini includes an extension-owned context file instead of changing a user's
  global instructions.
- Kimi maps native tools but explicitly refuses to treat a hidden subagent as
  proof of visible cross-session transport.
- Codex uses native skill discovery and has no hook entry or default
  `hooks/hooks.json` file. Claude points explicitly to
  `hooks/claude-hooks.json`, preventing Codex from auto-discovering the
  Claude-specific SessionStart adapter.
- The portable root manifest contains no client-specific bootstrap. Hermes can
  consume it through its Agent Plugins path, where skills remain namespaced and
  explicitly selected until a clean runtime transcript proves more.
- Copilot and Devin use portable skill folders and repository instructions only;
  no dedicated startup hook or client plugin contract is claimed.

## Clean-session acceptance

For each client, record the exact client version, model, operating system,
installation source and commit or release. Start with no project-specific rule
that names NoBrainer. Preserve the complete transcript and use these probes:

For a long-running probe, read back `SESSION_HEALTH_GATE` at `START`,
`AFTER_COMPACTION`, `MATERIAL_TRANSITION` and `BEFORE_CLOSEOUT`, using the
host/configured policy rather than assuming universal limits. Record
`UNKNOWN`/`UNSUPPORTED` signals and lower proof instead of guessing. Read back
`RUNTIME_RELEASE` separately: `task_complete` does not prove that task-owned
browser, tool or subprocess workers are closed.
Missing optional telemetry does not block safe bounded work or artifact acceptance;
it only limits the health claim. An explicitly required hard budget still needs
reliable enforcement. A configured warning checkpoints goal/TODO and prevents optional new workers or
large units; a hard threshold requires the clear/end-turn gate. Repository
examples are not universal host limits.
For resumable probes, persist one task-local Markdown `GOAL_FILE`. Before clear,
prove its checkpoint and no active writer, then record `CLEAR_MODE` and host
readback. After clear or a fresh turn, reload the file from disk and reconcile
identity, checkout and evidence; a transcript summary or host-native goal is not
the canonical recovery source.

### Automatic routing

The portable `ROUTED` policy describes how a plan may select an advertised
capability tier; it is not a cross-provider gateway. A client must read back the
actual model, effort and budget before claiming automatic routing. An unavailable
target is `MODEL_ESCALATION_PROPOSED` or `OWNER_APPROVAL`, never a silent
fallback.

```text
Help me design and implement an ambiguous feature that crosses several modules
and may affect production.
```

Passing behavior:

- `nobrainer-ultra` is selected without pasting its body;
- the agent enters a short requirements/acceptance gate before writes;
- it creates one canonical plan and shows a compact Progress checklist;
- production effects remain owner-gated;
- it does not manufacture workers before work units exist.

### Correction and review loop

```text
I changed my mind: keep the public API unchanged. Update the plan accordingly.
```

Passing behavior: the old requirement is marked superseded, dependent TODO
items and evidence are invalidated, and the affected route is rebuilt without a
second ordinary clarification round. A simulated verified review finding must
return to Build and then fresh Review; it may not reuse the old green result.

### Explicit canonical invocation

```text
$nobrainer-ultra Deliver this task with the smallest safe workflow.
```

Passing behavior: the client loads the canonical `nobrainer-ultra` body and any
required relative reference without the user pasting either one.

### Implicit alias control

```text
Use nb-ultra to deliver this task with the smallest safe workflow.
Use nb-flow to deliver this task with the smallest safe workflow.
```

`nb-ultra` and `nb-flow` are trigger phrases in the description, not additional
skill names.
Record whether the client supports and selects it through implicit matching.
Do not present this as an explicit invocation guarantee. In the v1.3.0 Codex
probe, alias-only selection failed under a crowded skill catalog and a prompt
that prohibited file reads; the canonical `$nobrainer-ultra` probe passed.

### Non-trigger control

```text
Fix this obvious typo in README.md.
```

Passing behavior: one primary session makes the bounded correction without SDD,
a wiki, or a worker swarm.

## Runtime evidence record

Store a transcript or durable report with:

```text
CLIENT:
CLIENT_VERSION:
MODEL:
OS:
INSTALL_SOURCE:
RELEASE_OR_COMMIT:
SKILL_SHA256:
INVOCATION: CANONICAL_EXPLICIT | IMPLICIT_DESCRIPTION
PROMPT:
SKILL_DISCOVERED:
FIRST_WRITE_BEFORE_GATE: YES | NO
RESULT: PASS | FAIL | BLOCKED
SESSION_HEALTH_GATE:
RUNTIME_RELEASE:
OWNED_WORKER_READBACK:
EVIDENCE_PATH:
```

Marketplace screenshots, manifest parsing, an installer exit code, or a skill
appearing on disk do not replace this acceptance test.

For a hook-based client, preserve the emitted JSON and prove the client consumed
the marker. For OpenCode or Pi, preserve both adapter logs/readback and the first
model action. A prompt that pastes the skill body does not prove discovery. A
valid explicit `$nobrainer-ultra` run proves explicit loading, not automatic routing.

## Optional bounded command runtime (1.7.0)

The Sessions helper runs explicit argv commands using Python 3.11+ on POSIX.
It is opt-in and ships with the skill; no daemon or new hook registration is
required. Windows process-group enforcement is unsupported. The fifteen
plain-text skills remain portable; this helper does not narrow their format
compatibility. See [runtime limits and examples](BOUNDED_RUNNER.md).

## Session restart capability levels

The `session-restart` mode shipped in v1.8.0 and refined in v1.8.1 is a
client/model-neutral Sessions
protocol. The optional Python 3.11+ helper evaluates observations and runs without
a model or client SDK. It does not implement native creation or archival.
Human-readable rollover titles use `<stable task title> | started DD-MM` where a
host supports create-time titles or rename. The registry retains the full start
timestamp and timezone, and IDs remain authoritative. A client without title
mutation reports that cosmetic capability as unsupported; this is not a failed
transfer and no universal rename API is implied.

- No hooks: the model checks at task boundaries and prepares durable progress.
- Hooks: a reviewed client adapter may supply normalized observations and invoke
  the helper; hook names and output envelopes remain client-specific.
- Native sessions: automatic rotation additionally requires fresh creation, exact
  identity/readback, shared checkpoint access and authoritative ownership transfer.
- No archive API: a verified successor can continue with source archive pending.
- No safe transport/ownership: manual handoff; no hidden worker substitution.

Existing client-load evidence does not establish restart support. Native
end-to-end restart, all-model behavior and net cost savings are unverified until
tested separately for the exact adapter/client version. No global hooks are
installed by enabling portable instructions. See [the guide](SESSION_RESTART.md).
