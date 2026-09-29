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
  --skill nobrainer-auto-fine-tune \
  --skill nobrainer-sessions \
  --skill nobrainer-build \
  --skill nobrainer-review
```

The core skill links to `nobrainer-auto-fine-tune` and `nobrainer-sessions`, so a
subset should keep both (the guided setup below always adds the audit skill).
The installer prints a `NOTE:` for every selected skill that links to a skill
which is neither selected nor already installed; the guided setup prints the same
note once for its whole install set, with the selection ID to add.

Supported local destinations are `claude`, `codex`, `opencode`, `copilot` and
the shared `agents` path. `codex` and `agents` both target the current shared
`~/.agents/skills` location documented by
[Codex Agent Skills](https://developers.openai.com/codex/skills). Claude Code
follows `CLAUDE_CONFIG_DIR` and OpenCode follows `XDG_CONFIG_HOME`; the installer
honours both. An empty value counts as unset, and a value that is not an
absolute path is an error (Claude Code does not accept relative or `~` values
either). Override a destination only when you have inspected it:

```bash
python3 scripts/install_skills.py \
  --client agents \
  --dest /path/to/controlled/skills \
  --mode copy
```

`symlink` is the default and keeps one source of truth. `copy` is useful for an
isolated release/archive test, or where the operating system does not allow
symlinks (for example Windows without developer mode). Repeating a `copy`
install over an identical copy reports it as current, whatever bytecode
(`__pycache__`) or file-manager litter (`.DS_Store`) has appeared in it since; a
copy that differs is a conflict and must be replaced by hand after review.

Use one channel per client. Gemini CLI, Pi, OpenCode and Kimi Code also read
`~/.agents/skills`, so installing there (`--client agents` or `codex`) on top of
their own adapter can list every skill twice. Pick either the adapter or the
shared folder.

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

```bash
python3 scripts/install_personalization.py --client codex
python3 scripts/install_personalization.py --client codex --apply
```

Repeat with `--client claude`, `opencode` or `copilot` as supported. Without
`--home` the installer follows the variables the clients read:
`CLAUDE_CONFIG_DIR` for Claude Code, `CODEX_HOME` for Codex and
`XDG_CONFIG_HOME` for OpenCode; an explicit `--home` selects the documented
default locations under it and ignores them. Codex reads
`AGENTS.override.md` instead of `AGENTS.md` whenever the override is not
empty, so the installer refuses to write `AGENTS.md` next to one; remove or
empty the override, or pass `--path` to target it on purpose.

Claude Code may already import the Codex global file with `@~/.codex/AGENTS.md`.
The installer skips the duplicate block only when that import is real (a word of
its own in prose, not inside a code span, fence, indented block or comment) and
the imported file already carries the managed block; otherwise it writes the
block to the Claude file and says why. A second copy of the block is harmless;
a missing one would leave Claude without the instructions, so the check errs
that way. `agents` needs an explicit verified `--path`. For a resolved global wiki,
pass `--wiki-root PATH` pointing at a directory containing `WIKI.md`; this
records the actual location in the personalization block. `--auto-update`
opts into safe checked `nobrainer-tech-flow`-only upgrades where standing owner
authorization exists, and `--auto-session-restart` opts into evidence-gated
session rotation. A later run without those flags writes the default block
again; add `--keep-options` to keep the update, session-restart and wiki-root
settings already in the block (the guided setup always does). A grant counts
only as the exact line the installer writes for it, so wording quoted in a
`--preferences` value never becomes one. Without the
update opt-in, the first active `nobrainer-tech-flow` use each day checks and
notifies. Use a scheduler separately if updates must be checked on inactive days.

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

Answer the questions in a terminal, or pass them so nothing is asked
(`--work-profile`, `--goal`, `--tools` and `--existing-setup`). Without a
terminal and with an answer missing, the command stops with `INPUT_REQUIRED`
and the flags it needs instead of waiting for input:

```bash
python3 scripts/recommend_flow_setup.py \
  --repo-url https://github.com/owner/project \
  --client codex \
  --work-profile software-development \
  --goal "ship and test a web application" \
  --tools "Codex, Python, GitHub" \
  --existing-setup "pytest and git"
```

To inspect an already available checkout instead of contacting GitHub, add
`--repo-path /path/to/checkout`. To keep the whole preflight offline, add
`--offline`; it will base recommendations on the answers and local client
configuration only and report that repository content was unavailable.

After reviewing the dry-run, repeat the command with your selected IDs
(`--selection 01,03,04`) and `--apply`. Only those items are added, together with required IDs `01`
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

Use the repository as a plugin or install the canonical skill directories
through the client-supported Agent Skills path. The checked adapter includes a
`SessionStart` hook that injects only `adapters/bootstrap.md`.

```bash
claude plugin marketplace add /path/to/reviewed/nobrainer-tech-flow
claude plugin install nobrainer-tech-flow@nobrainer-tech
```

The path is the checkout pinned to a reviewed commit in "Safe default" above.
`claude plugin marketplace add nobrainer-tech/nobrainer-tech-flow` tracks the
default branch instead, so prefer it only where that is acceptable. The same
commands work inside a session as `/plugin marketplace add ...` and
`/plugin install ...`. A plugin namespaces its skills, so the entry point is
`/nobrainer-tech-flow:nobrainer-tech-flow`; skills installed with
`--client claude` keep the plain `/nobrainer-tech-flow`. Either way the model
can also load the skill by name. The `$nobrainer-tech-flow` form is Codex syntax.

Claude Code lists every skill name but drops the descriptions of the least-used
skills once the listing passes its budget (1% of the context window by default).
In a session that already carries many skills the Flow descriptions may reach
the model as names only. The bootstrap and the personalization block name the
entry skill, so it can still be loaded by name; what is lost is routing to the
specialists by their descriptions. The companion
[`nobrainer-claude`](https://github.com/nobrainer-tech/nobrainer-claude)
installer can raise the budget on request (`--raise-skill-budget`).

After restart, verify:

- `nobrainer-tech-flow` is discoverable without pasting its body;
- the hook emits exactly one bootstrap context;
- a simple task remains direct;
- a non-trivial task starts with nobrainer-tech-flow and a compact Progress checklist.

### Codex

The `.codex-plugin/plugin.json` manifest exposes `./skills/` and declares no
plugin hook; bootstrap comes from the personalization block or the skill's own
trigger. Install through the native plugin channel or use the installer. The
plugin channel needs a reviewed checkout:

```bash
codex plugin marketplace add /path/to/reviewed/nobrainer-tech-flow
codex plugin add nobrainer-tech-flow@nobrainer-tech-skills-dev
```

The installer's `codex` destination is the shared `~/.agents/skills` path:

```bash
python3 scripts/install_skills.py --client codex
python3 scripts/install_skills.py --client codex --apply
```

Restart Codex and test discovery in a fresh task. Repository instructions or the
native skill trigger provide bootstrap; a file on disk is not routing proof.
Use nobrainer-tech-flow for user-facing requests, or `$nobrainer-tech-flow` for the
technical explicit invocation; when the skills come from the plugin, use the
name the client's skill list shows. Plain `NBFlow`, `NBF` and `nobrainer-tech-flow`
are natural-language triggers whose recognition depends on the client. Existing
legacy entries under `~/.codex/skills` are not deleted or rewritten automatically.

### Cursor

Use `.cursor-plugin/plugin.json`. Its session hook runs the shared bootstrap
through `hooks/run-hook.cmd`, which uses Git Bash on Windows. Repository tests
cover the manifest and the hook script; Cursor itself has not been read back, so
confirm one injection and native skill discovery after restart.

### OpenCode

Pin the Git package to an immutable full commit in `opencode.json`:

```json
{
  "plugin": [
    "nobrainer-tech-flow@git+https://github.com/nobrainer-tech/nobrainer-tech-flow.git#NB_REVIEWED_COMMIT_SHA"
  ]
}
```

Replace the placeholder before use. The adapter registers `skills/` and puts
the bootstrap in front of the first user message of each request, once; when
that message has no text part (after a compaction) it adds a synthetic text part
instead. Local checkout installation is also available with `--client opencode`.

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

The package extension registers `skills/` during resource discovery and adds the
bootstrap to every model request that does not carry it yet. The host rebuilds
the message list for each request, so the bootstrap also survives compaction, and
a marker keeps one request from receiving it twice. Repository tests cover the
extension contract; a real client readback is still required.

### Windows

Run the Python scripts with `py -3` or `python`. The hook adapters need Git Bash,
not the `bash.exe` launcher that Windows ships for WSL (Windows finds that one
first when a command says just `bash`). The repository pins the hook scripts and
the bootstrap to LF endings so a Git checkout with `core.autocrlf=true` still
runs them. Creating symlinks needs developer mode or an elevated shell; without
either, install with `--mode copy`. CI runs the structure validators, the
adapter tests and a Windows smoke module on a Windows runner; it does not run the
whole suite there, and no client was read back on Windows.

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
   for Codex the canonical form is `$nobrainer-tech-flow` (a plugin install lists
   the skills under the plugin's name, so use the name the client shows);
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
