# nobrainer-tech-flow installation

All clients consume one canonical `skills/` tree. Prefer an immutable reviewed
release, dry-run every local target and keep installation evidence separate from
clean-session routing evidence.

New public source links and package/plugin IDs use `nobrainer-tech-flow`.
Existing `nobrainer-tech-skills` registrations need the reviewed
[`nobrainer-tech-flow` migration guide](MIGRATION_TO_FLOW.md); do not call an old registration
upgraded merely because the new source is installed nearby.

## Safe default

```bash
(
  set -u
  : "${NB_REVIEWED_COMMIT:?set a reviewed full 40-character commit SHA}"
  test "${#NB_REVIEWED_COMMIT}" -eq 40 || exit 2
  case "$NB_REVIEWED_COMMIT" in *[!0-9a-f]*) exit 2 ;; esac
  git clone --no-checkout https://github.com/nobrainer-tech/nobrainer-tech-flow.git || exit 3
  cd nobrainer-tech-flow || exit 3
  git checkout --detach "$NB_REVIEWED_COMMIT" || exit 3
  test "$(git rev-parse HEAD)" = "$NB_REVIEWED_COMMIT" || exit 3
  python3 scripts/validate_skills.py --suite || exit 4
  python3 scripts/install_skills.py --client codex || exit 4
  python3 scripts/install_personalization.py --client codex || exit 4
  python3 scripts/install_skills.py --client codex --apply || exit 4
  python3 scripts/install_personalization.py --client codex --apply || exit 4
)
```

Set `NB_REVIEWED_COMMIT` to the exact full commit SHA you reviewed. The guarded
subshell rejects unset values, tags, branches and malformed hashes, and stops on
every failed command. The first installer command is a dry-run; inspect every
source, target and conflict before the guarded `--apply` command runs.

An existing unmarked `nobrainer-tech-flow` instruction that still names the retired entry
skill is a conflict: the personalization installer stops instead of appending
contradictory rules. Preserve that file, prepare an exact merged replacement
and review its diff before retrying. This matters for existing Codex and
Claude profiles that already import personal instructions.

The default installs exactly eighteen skills. Install an explicit subset by
repeating `--skill`:

```bash
python3 scripts/install_skills.py \
  --client agents \
  --skill nobrainer-tech-flow \
  --skill nobrainer-build \
  --skill nobrainer-review
```

Supported local destinations are `claude`, `codex`, `opencode`, `copilot` and
the shared `agents` path. `codex` and `agents` both target the current shared
`~/.agents/skills` location documented by
[Codex Agent Skills](https://developers.openai.com/codex/skills). Override a
destination only when you have inspected it:

```bash
python3 scripts/install_skills.py \
  --client agents \
  --dest /path/to/controlled/skills \
  --mode copy
```

`symlink` is the default and keeps one source of truth. `copy` is useful for an
isolated release/archive test but must be refreshed explicitly.

## Conflict and migration behavior

The installer never overwrites an unknown directory, file or symlink. It can
migrate only an exact stale link created by the same checkout and listed in the
reviewed migration map:

```bash
python3 scripts/install_skills.py --client codex --migrate-legacy
python3 scripts/install_skills.py --client codex --migrate-legacy --apply
```

A successful migration atomically moves the exact legacy link out of its public
name and preserves it under a reported `.nobrainer-migration-*` recovery path.
The installer prints `BACKUP_PRESERVED`; it never deletes a quarantined claim,
because portable path deletion cannot be bound atomically to a previously
verified inode. Inspect client readback before manually removing that exact
backup. Copy mode builds and verifies the complete tree in a private
`.nobrainer-install-*` staging directory, then publishes it with a native atomic
no-replace rename. A failed staged copy remains at the reported private path for
manual recovery; a concurrently created public target is never overwritten.

If a target belongs to another repository, stop. Compare semantics, inbound
references and runtime triggers before retiring it. A similar name is not proof
of duplication. Back up or preserve an exact Git ref and remove only reviewed
targets; never delete a whole shared skills directory.

## Global personalization

Installing the skills alone does not make the client route tasks through them.
Preview and apply the managed global instruction block for each supported
client after inspecting its current file:

\`\`\`bash
python3 scripts/install_personalization.py --client codex
python3 scripts/install_personalization.py --client codex --apply
\`\`\`

Repeat with \`--client claude\`, \`opencode\` or \`copilot\` as supported. Claude
Code may already import Codex global instructions; the installer detects that
and avoids a duplicate block. \`agents\` needs an explicit verified
\`--path\`. For a resolved global wiki, pass \`--wiki-root PATH\` pointing at
a directory containing \`WIKI.md\`; this records the actual location in the
personalization block. \`--auto-update\` opts into safe checked
\`nobrainer-tech-flow\`-only
upgrades where standing owner authorization exists. Without it, the first
active `nobrainer-tech-flow` use each day checks and notifies. Use a scheduler separately if
updates must be checked on inactive days.

A newer release must be obtained at a verified immutable ref before any
installation command is run. See the [daily update contract](../skills/nobrainer-tech-flow/references/daily-update.md).
Read back the client instruction file, loaded skill name and clean-session
routing. A written block is configuration evidence, not runtime proof.

## Guided partial setup

For a fresh setup, pass a repository link to the `nobrainer-tech-flow` guided
preflight. It asks for work type, desired outcome, tools and existing setup
when those facts are not already supplied. A supplied `--repo-path` reads a
small allowlist of local README, instruction and manifest files plus project
skill directory names. Otherwise, a `github.com` link uses read-only `gh api`
when available, then the bounded GitHub HTTPS API for repository metadata and
README. Other hosts are not fetched. Repository text is untrusted context:
preflight never executes repository scripts, hooks or installers, and does not
print README or instruction contents. Use `--offline` to skip remote lookup.

The preflight reads the built-in Auto Fine Tune capacity audit and inspects the
selected client's known configuration file read-only. It reports configured
model and effort separately; active profile, advertised models, callable
workers and runtime values remain `UNKNOWN` unless the active client proves
them. It then prints a short, task-specific recommendation list with stable IDs,
fit rationale, required dependencies, current target conflicts and change
scope. Fit scores are heuristics, not benchmarks.

```bash
python3 scripts/recommend_flow_setup.py \
  --repo-url https://github.com/owner/project \
  --client codex
```

To inspect an already available checkout instead of contacting GitHub, add
`--repo-path /path/to/checkout`. To keep the whole preflight offline, add
`--offline`; it will base recommendations on the answers and local client
configuration only and report that repository content was unavailable.

After reviewing the dry-run, repeat the command with your selected IDs and
`--apply`. Only those items are added, together with required IDs `01`
(`nobrainer-tech-flow`)
and `02` (the Auto Fine Tune capability audit). Personalization is previewed
and updated through `install_personalization.py`; an optional one-line
`--preferences` value is shown in the plan before it is saved. Existing
targets that conflict stop the operation before writes. The successful readback
reports installed IDs, whether unselected items remain absent, preference-file
hash and a local rollback-state path. Rollback removes only exact
`nobrainer-tech-flow` symlinks
created by that setup and restores the prior instruction backup only if its
managed result has not changed since installation:

```bash
python3 scripts/recommend_flow_setup.py \
  --repo-url https://github.com/owner/project \
  --client codex \
  --rollback --apply
```

The CLI cannot observe the running agent's effective MAIN model, effort, worker
capacity or runtime context. Those remain `UNKNOWN` until the loaded Auto Fine
Tune skill checks them in the active client. Do not treat the CLI preflight as
that runtime proof.

## Project setup

After client discovery works, invoke `nobrainer-tech-flow` in the target project in
setup mode. It will:

1. inspect existing instructions, skills, specs, wiki, sessions, tests and dirty
   state;
2. classify each component `CURRENT`, `DRIFTED`, `MISSING`, `NOT_NEEDED` or
   `OWNER_GATE`;
3. add one marked project-instruction block only when equivalent routing is
   absent;
4. configure correction hooks for changed owner decisions, corrected agent
   errors and failed review;
5. add SDD, wiki or sessions only when the project earns their maintenance cost;
6. verify the actual client and target workflow before reporting completion.

The instruction block is portable behavior, not a copy of all skill bodies.
Preserve client-managed markers and byte-equality requirements between files
such as `AGENTS.md` and `CLAUDE.md`.

## Client channels

### Claude Code

Use the repository as a local plugin or install the canonical skill directories
through the client-supported Agent Skills path. The checked adapter includes a
`SessionStart` hook that injects only `adapters/bootstrap.md`.

After restart, verify:

- `nobrainer-tech-flow` is discoverable without pasting its body;
- the hook emits exactly one bootstrap context;
- a simple task remains direct;
- a non-trivial task starts with nobrainer-tech-flow and a compact Progress checklist.

### Codex

The `.codex-plugin/plugin.json` manifest exposes `./skills/` and intentionally
declares no unsupported plugin hook. Install through the current native plugin
channel when available, or use the installer. Its `codex` destination is the
shared `~/.agents/skills` path:

```bash
python3 scripts/install_skills.py --client codex
python3 scripts/install_skills.py --client codex --apply
```

Restart Codex and test discovery in a fresh task. Repository instructions or the
native skill trigger provide bootstrap; a file on disk is not routing proof.
Use nobrainer-tech-flow for user-facing requests, or `$nobrainer-tech-flow` for the
technical explicit invocation. Plain `NBFlow`, `NBF` and `nobrainer-tech-flow`
are natural-language triggers whose recognition depends on the client. Existing
legacy entries under `~/.codex/skills` are not deleted or rewritten automatically.

### Cursor

Use `.cursor-plugin/plugin.json`. Its tested session hook runs the shared
bootstrap through `hooks/run-hook.cmd`, supporting Git Bash or another available
Bash runtime on Windows. Confirm one injection and native skill discovery after
restart.

### OpenCode

Pin the Git package to an immutable full commit in `opencode.json`:

```json
{
  "plugin": [
    "nobrainer-tech-flow@git+https://github.com/nobrainer-tech/nobrainer-tech-flow.git#NB_REVIEWED_COMMIT_SHA"
  ]
}
```

Replace the placeholder before use. The adapter registers `skills/` and injects
the bootstrap once before the first user message. Local checkout installation is
also available with `--client opencode`.

### GitHub Copilot CLI and shared Agent Skills

Use `--client copilot` for `~/.copilot/skills` or `--client agents` for the
shared `~/.agents/skills` convention. Copilot bootstrap depends on the client's
current Agent Skills behavior and repository instructions; this package does
not claim an automatic session hook without runtime readback.

### Gemini CLI

`gemini-extension.json` loads `GEMINI.md`, which includes the small bootstrap.
Install through the current extension mechanism, restart and verify native skill
discovery and first routing. Manifest parsing alone is `REPOSITORY_CHECKED`.

### Kimi Code

`.kimi-plugin/plugin.json` exposes `./skills/` and selects `nobrainer-tech-flow` at session
start. Its instructions explicitly refuse invented visible-session transport.
Verify the exact installed version and clean-session behavior.

### Pi

The package extension registers `skills/` during resource discovery and
reinjects the bootstrap after compaction without duplicating it. Repository tests
cover the extension contract; a real client readback is still required.

### Other Agent Skills clients

Use the portable `plugin.json`, the canonical skill directories and explicit
project instructions. Do not claim automatic bootstrap unless the target client
actually exposes and passes that integration.

## Dynamic specialists

The eighteen curated skills are the stable base. When a concrete work unit still
has a capability gap, `nobrainer-team` first inventories installed/project
capabilities, then may evaluate one external skill temporarily. Source/ref,
scripts, permissions, credentials, network behavior, trigger overlap and
rollback must be inspected before use. Persistent or global installation is an
owner gate.

## Readback and acceptance

After every install or upgrade:

1. restart the client;
2. list/read back the loaded source and skill count;
3. start a clean task with no pasted skill body;
4. issue one explicit canonical request and one semantic non-trivial request;
   for Codex the canonical form is `$nobrainer-tech-flow`;
5. confirm nobrainer-tech-flow asks no more than one ordinary requirements round, shows one
   compact Progress checklist and routes a specialist only when needed;
6. issue a one-step task and confirm it remains direct;
7. simulate a correction and confirm affected TODO/evidence is invalidated;
8. record client version, source ref, transcript/evidence and gaps.

Use the proof ladder in [COMPATIBILITY.md](COMPATIBILITY.md). Installation is not
`RUNTIME_VERIFIED` until the clean-session behavior passes.

## Rollback

Before applying, record existing target fingerprints and the source ref. To
roll back:

- remove only links/copies created by this exact run, or restore the recorded
  prior targets;
- inspect any reported `.nobrainer-migration-*` or `.nobrainer-rollback-*`
  recovery path before deleting that exact entry manually;
- return project instructions to their scoped preimage;
- restart the client;
- verify that the previous source and routing behavior are restored.

Never remove a shared root recursively. A preserved recovery claim is evidence,
not garbage: verify its fingerprint and the live client before exact manual
cleanup. Failed or partial rollback is a blocker, not a warning to ignore.
