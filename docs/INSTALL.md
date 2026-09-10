# NoBrainer.Tech Flow installation

All clients consume one canonical `skills/` tree. Prefer an immutable reviewed
release, dry-run every local target and keep installation evidence separate from
clean-session routing evidence.

New public source links use `nobrainer-tech-flow`. Upgrading an existing
installation? Preserve its legacy technical `nobrainer-tech-skills` identity;
see the [Flow migration guide](MIGRATION_TO_FLOW.md).

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
  python3 scripts/install_skills.py --client codex --apply || exit 4
)
```

Set `NB_REVIEWED_COMMIT` to the exact full commit SHA you reviewed. The guarded
subshell rejects unset values, tags, branches and malformed hashes, and stops on
every failed command. The first installer command is a dry-run; inspect every
source, target and conflict before the guarded `--apply` command runs.

The default installs exactly fifteen skills. Install an explicit subset by
repeating `--skill`:

```bash
python3 scripts/install_skills.py \
  --client agents \
  --skill nobrainer-ultra \
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

## Project setup

After client discovery works, invoke `nobrainer-ultra` in the target project in
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

- `nobrainer-ultra` is discoverable without pasting its body;
- the hook emits exactly one bootstrap context;
- a simple task remains direct;
- a non-trivial task starts with NoBrainer.Tech Flow and a compact Progress checklist.

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
Use NoBrainer.Tech Flow for user-facing requests, or `$nobrainer-ultra` for the
technical explicit invocation. Plain `nb-flow`, `nb-ultra` and `nb-workflow` are
compatibility aliases that depend on implicit description matching and must be
recorded separately. Existing
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
    "nobrainer-tech-skills@git+https://github.com/nobrainer-tech/nobrainer-tech-flow.git#NB_REVIEWED_COMMIT_SHA"
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

`.kimi-plugin/plugin.json` exposes `./skills/` and selects `nobrainer-ultra` at session
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

The fifteen curated skills are the stable base. When a concrete work unit still
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
   for Codex the canonical form is `$nobrainer-ultra`;
5. confirm NoBrainer.Tech Flow asks no more than one ordinary requirements round, shows one
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
