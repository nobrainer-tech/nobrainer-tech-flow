# nobrainer-tech-flow installation

All clients consume one canonical `skills/` tree. Prefer an immutable reviewed
release, dry-run every local target and keep installation evidence separate from
clean-session routing evidence.

New public source links and package/plugin IDs use `nobrainer-tech-flow`.
Existing `nobrainer-tech-skills` registrations need the reviewed
[`nobrainer-tech-flow` migration guide](MIGRATION_TO_FLOW.md); do not call an old registration
upgraded merely because the new source is installed nearby.

## npm command

Node 18+ and Python 3.11+ are prerequisites. Preview the setup first:

```sh
npx nobrainer-tech-flow@2.9.0 --client codex
npx nobrainer-tech-flow@2.9.0 --client codex --apply
npx nobrainer-tech-flow@2.9.0 --client codex --undo --apply
```

Use claude for Claude Code, opencode or copilot for those clients. Add --home PATH
for an isolated profile. The package is published on
[npm](https://www.npmjs.com/package/nobrainer-tech-flow); each release lists its
version there.

Application copies the release files into the chosen home directory's
.nobrainer-tech-flow-npm/2.9.0 and verifies the copy. That folder sits beside
~/.nobrainer-tech-flow, where the Git installation suggests a clone, so cleaning
the clone cannot delete the files the skill links point to. Releases before 2.3.2
kept their copy in .nobrainer-tech-flow/npm; undo such a setup with the command of
the release that made it. The existing installer then
links skills to that stable source and writes its managed instructions. This
avoids links into npx's temporary cache. Unknown files and conflicting installs
are preserved. Undo uses the same setup record as the Git installer. Retained
release files remain available for other profiles; they are not disposable test
artifacts. No postinstall script runs on npm installation.

When switching from an existing Git or npm installation, preview first. If it
reports a different source, use that installation's recorded undo command before
applying the new source. The npm command preserves conflicts rather than replacing
another installation automatically.

For ChatGPT and Claude Chat, follow the [native plugin setup](CHAT_PLUGINS.md)
rather than the coding-client command.

### Publishing and trusted updates

The first npm publication requires an authenticated package owner. After the
package exists, configure its Trusted Publisher with GitHub owner
`nobrainer-tech`, repository `nobrainer-tech-flow`, workflow `npm-publish.yml`,
no environment name, and permission to run `npm publish`. A publisher configured
for a different package or repository does not authorize this package.

After the release PR's Validate checks pass and its commit is merged, create the
matching stable tag. Run the manual Publish npm workflow from that tag. It checks
the tag against package.json, verifies the packed installation and publishes
with OIDC provenance. Its bounded registry readback compares the version and
tarball integrity before reporting delivery. Inspect the registry before retrying
a run that fails after publication; npm versions cannot be overwritten.

See [npm's trusted publishing documentation](https://docs.npmjs.com/trusted-publishers/).

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
  python3 scripts/install.py --client codex || exit 4          # preview: changes nothing
  python3 scripts/install.py --client codex --apply || exit 4  # link the skills, add the block
)
```

Set `NB_REVIEWED_COMMIT` to the exact full commit SHA you reviewed. The guarded
subshell rejects unset values, tags, branches and malformed hashes, and stops on
every failed command. The first installer command is a dry-run; stop the block
there to read the plan, then run the `--apply` command.

`scripts/install.sh` is the shortest path for one client (`claude`, `codex`,
`opencode` or `copilot`). It needs no Python and asks nothing; it runs as `sh` on
macOS, Linux and WSL (tested with dash, bash, busybox and zsh emulating sh), and in
Git Bash on Windows. Run it where the agent runs: an install made inside WSL lands in the WSL
home, which a Windows-native client does not read.

```sh
git clone https://github.com/nobrainer-tech/nobrainer-tech-flow ~/.nobrainer-tech-flow
sh ~/.nobrainer-tech-flow/scripts/install.sh --client claude            # preview: changes nothing
sh ~/.nobrainer-tech-flow/scripts/install.sh --client claude --apply    # link all skills, add the block
sh ~/.nobrainer-tech-flow/scripts/install.sh --client claude --undo --apply
```

`scripts/install.py` does the same with Python (`python3 scripts/install.py`, same
flags). The two share the setup record, so either one undoes what the other did.

- The preview names the source commit, how many skills it would link and where,
  and shows the exact text it would write to the client's global instruction file.
- A canonical skill target that is not a link to this checkout is a conflict:
  nothing is written and the command says which one.
- Running `--apply` again when nothing needs to change prints `UP TO DATE` and no
  restart hint. `INSTALLED` and the restart hint appear only when a link or the
  instruction file was written.
- The only standing authorization it writes is the default one-line daily update of
  Flow itself to a verified stable release; session rotation still needs its own
  opt-in. When the block in the instruction file is the text of an earlier version,
  both scripts replace it with this version's text, keep everything outside the two
  markers byte for byte and save the file as it was as a `.bak` copy first. Both keep
  the update choice: an existing block updates itself again only when it holds the
  update line as its own line, and a notify-only, edited or unknown update line is
  replaced by the one-line notify-only rule. `install.py` also keeps session-restart
  and wiki-root settings as `--keep-options` keeps them; `install.sh` leaves a block
  that carries one of those options or a preference, or whose markers do not stand on
  lines of their own, exactly as it is and says so. Change options with
  `install_personalization.py`.
- `--undo` (a preview until `--apply` is added) removes exactly the links the setup
  created and puts the managed block back as it was before the first setup:
  removed, or the block that was there before. The rest of the instruction file
  stays as it is now, so the file comes back byte for byte when nothing else
  changed. It stops with the reason if the file changed since the last run. It is
  the guided setup's rollback, so it also reverses a setup made by the guided setup
  below, and the other way round.
- `--undo` also removes the folders the setup had to create, such as `~/.agents`
  for Codex or `~/.config/opencode` for a client that never ran, but only when they
  are empty. A folder that was there before the setup, or holds anything else, stays.
  A second undo, or an undo where no setup is recorded, prints `NOTHING TO UNDO`
  with the client and the record it looked for, changes nothing and exits 0. A
  damaged record is still an error.
- It needs symbolic links. On Windows turn on Developer Mode or run from an
  elevated shell; the command checks first and says so. Otherwise use
  `install_skills.py --mode copy` (see Windows below).
- `--home` and the client variables behave as described for the individual
  scripts below. When a variable chose the location, the output says so; keep it
  set when you undo.

The setup record is `.nobrainer-flow-onboarding-<client>.json` (for example
`.nobrainer-flow-onboarding-codex.json`) in the chosen home, next to the client's
folders. Only you can read or write it (mode 0600), and it holds paths and hashes,
never a secret: the skills folder, the links the setup created, the instruction file
with its backup and the SHA-256 of what was written, and `created_dirs`, the folders
the setup created. `--undo --apply` deletes it, so keep it until you no longer need
to undo. `.nobrainer-flow-onboarding.json` without a client name is the older
single-client record; `install.py` still reads it, and `install.sh` points you to it.
A new instruction file the setup creates is owner-only (mode 0600) as well. An
existing file keeps its mode, and its `.bak` copy has the same mode.

The individual scripts remain the way to install a subset, use copies, target
the shared `agents` folder or another client, and are documented next.

An existing unmarked `nobrainer-tech-flow` instruction that still names the retired entry
skill is a conflict: the personalization installer stops instead of appending
contradictory rules. Preserve that file, prepare an exact merged replacement
and review its diff before retrying. This matters for existing Codex and
Claude profiles that already import personal instructions.

`install_skills.py` installs exactly eighteen skills by default. Install an
explicit subset by repeating `--skill`:

```bash
python3 scripts/install_skills.py \
  --client agents \
  --skill nobrainer-tech-flow \
  --skill nobrainer-auto-fine-tune \
  --skill nobrainer-sessions \
  --skill nobrainer-spec-driven-development \
  --skill nobrainer-build \
  --skill nobrainer-review
```

The core skill links to `nobrainer-auto-fine-tune`, `nobrainer-sessions` and
`nobrainer-spec-driven-development`, so a subset should keep all three to make
those references available. The guided setup always adds the audit skill;
Sessions and SDD remain explicit selections, not silently added modules.
The installer prints a `NOTE:` for every selected skill that links to a skill
which is neither selected nor already installed; the guided setup prints the same
note once for its whole install set, with the selection ID to add.

Supported local destinations are `claude`, `codex`, `opencode`, `copilot` and
the shared `agents` path. `codex` and `agents` both target the current shared
`~/.agents/skills` location documented by
[Codex Agent Skills](https://developers.openai.com/codex/skills). Claude Code
follows `CLAUDE_CONFIG_DIR` and OpenCode follows `XDG_CONFIG_HOME`; the installer
honours both. An empty `XDG_CONFIG_HOME` (or `CODEX_HOME`) counts as unset, as the
XDG specification (and Codex) say; any other value is used exactly as written. A
value that is not an absolute path is an error for the client that reads it,
spaces-only and an empty `CLAUDE_CONFIG_DIR` included: Claude Code resolves such a
value against its own working directory and does not expand `~`, so the
installer, which runs from the checkout, cannot know where it points. A variable
the selected client does not read is ignored. Override a destination only when you
have inspected it:

```bash
python3 scripts/install_skills.py \
  --client agents \
  --dest /path/to/controlled/skills \
  --mode copy
```

`symlink` is the default and keeps one source of truth. `copy` is useful for an
isolated release/archive test, or where the operating system does not allow
symlinks (for example Windows without developer mode). Repeating a `copy`
install over an identical copy reports it as current, whatever `__pycache__`
directories or `.DS_Store` and `Thumbs.db` files have appeared in it since; any
other difference, including a loose `.pyc` file that would shadow a module, is a
conflict and the copy must be replaced by hand after review.

Use one channel per client. Gemini CLI, Pi, OpenCode and Kimi Code also read
`~/.agents/skills`, so installing there (`--client agents` or `codex`) on top of
their own adapter can list every skill twice. Pick either the adapter or the
shared folder.

## Conflict and migration behavior

`install_skills.py` and `install.sh` never overwrite an unknown directory, file
or symlink. A foreign target at a retired name such as `nobrainer-reddit` is
reported as `PRESERVED_FOREIGN` and left unchanged without blocking installation.
An exact old link into this checkout at a retired name that a setup record lists
is removed by the next `install.sh` or `install.py` apply (see the
[migration guide](MIGRATION_TO_FLOW.md) for the 2.5.0 rename). A foreign
target at a renamed alias such as `nb-flow`, a canonical name or an unresolved
legacy name such as `nobrainer-fast-audit` still stops installation.

Both installers use this conflict rule, including the Python/npm setups that
call `install_skills.py`. An exact stale link from the same checkout still
blocks installation and requires explicit migration through the Python helper:

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

For a blocking target from another repository, compare semantics, inbound
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
The installer skips the duplicate block only when the Claude file holds nothing
but that import line and the imported file already carries the managed block;
otherwise it writes the block to the Claude file. Whether an import inside a
longer file is live depends on how Claude Code parses the whole file, and an
independent review found ordinary files that looked like imports and were not.
A second copy of the block is harmless; a missing one would leave Claude without
the instructions. A guided setup recorded earlier for the Codex file asks for an
undo before it writes the Claude file. `agents` needs an explicit verified
`--path`. For a resolved global wiki,
pass `--wiki-root PATH` pointing at a directory containing `WIKI.md`; this
records the actual location in the personalization block. Since 2.6.0 the
block keeps Flow updated by default with one line: once a day on first use,
update to the latest verified stable release from the canonical source, with a
backup, changing nothing else. `--no-auto-update` writes a one-line notify-only
rule instead; `--auto-update` is still accepted and means the default. With
`--keep-options` an opt-out already in the block stays, and the longer update
lines written before 2.6.0 become the matching short line (an old grant stays a
grant, the old notify-only default stays notify-only). An update line that is
neither recognized grant becomes the notify-only line: updates are never inferred. `--auto-session-restart`
opts into evidence-gated session rotation. A later run without those flags
writes the default block again; add `--keep-options` to keep the update choice,
session-restart and wiki-root settings already in the block (the guided setup
always does). A grant counts
only as the exact line the installer writes for it, so wording quoted in a
`--preferences` value never becomes one, and a preference or wiki path must be
one printable line. A grant line that was edited is not kept, and the run says so
and names the flag that grants it again. With the
notify-only line, the first active `nobrainer-tech-flow` use each day checks and
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
`nobrainer-tech-flow` symlinks created by that setup and, if the instruction file
has not changed since the last run, puts its managed block back as it was before
the first setup, leaving the rest of the file as it is:

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
can also load the skill by name. The `$` forms are Codex syntax; the Codex section
below says which one to type.

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

#### Optional guards

Opt-in hooks in your Claude Code user `settings.json`, never in the plugin:

- before a shell command, Claude Code asks you first (it never denies) for
  `rm -r` (also `/bin/rm`) outside the temporary folders (`$TMPDIR`, `/tmp`,
  `/var/folders`), `git push --force` (also `-f`, `--force-with-lease` or a
  `+branch` refspec), `git reset --hard`, `git clean -f`, `vercel --prod`,
  `npm publish`, `terraform apply` or `destroy`, `kubectl delete` and
  `gh release create`, also with global options before the subcommand
  (`npm -w pkg publish`, `gh -R owner/repo release create`). A relative `rm`
  target counts as temporary only when the working folder is temporary and the
  command does not `cd` or `pushd` first, and a path counts by where its links
  lead. An `rm -r` whose arguments it cannot read, and a command line over 2,000
  characters that names one of these tools, are asked about as well;
- when a turn that edited files or ran commands ends without a line starting
  with `Proof:` or `Checked:` and without `UNVERIFIED`, the stop is blocked once
  so the agent adds one. A read-only turn, a second stop and an unreadable
  transcript are let through;
- after compaction, resume or clear, the agent is told to re-read up to three
  active Flow goal files (a `GOAL_ID:` line and a `STATUS` other than `COMPLETE`,
  in the project root, `tasks/`, `docs/` or `.nobrainer/`). It prints only each
  path and a known `STATUS` word, never other goal-file text; it follows no
  symlink, skips names with characters other than letters, digits, `.`, `-` and
  `_`, stops after 5,000 folder entries or 200 files, and prints nothing on any
  error.

This is a seatbelt, not a security boundary. It reads the command text, so
`sh -c`, a variable or an alias gets past it, and a risky phrase inside a quoted
string (`echo "git reset --hard"`) asks without need.

```bash
python3 scripts/install.py --client claude --guards            # preview the hooks it would add
python3 scripts/install.py --client claude --guards --apply    # add them, with a backup
python3 scripts/install.py --client claude --guards --undo --apply
```

`python3 scripts/install_guards.py` takes the same `--apply`, `--undo` and
`--home` flags. The settings file is `$CLAUDE_CONFIG_DIR/settings.json`, or
`~/.claude/settings.json` when the variable is unset. The preview lists only the
hooks it would add or remove, never other settings; other hooks are kept, each
change writes a new backup, readable only by you, without overwriting an older one, a second `--apply`
changes nothing, an install from an earlier version is shown as an update, and an invalid file is refused
(exit 3) without being touched. The hooks run `flow_guard.py` through the
skill link that `--client claude` created, so install the skills first. A
plugin-only install, other clients, `scripts/install.sh` and Windows are not
supported in this version (`UNSUPPORTED`, exit 3). Removing the skills leaves
the hooks in place, where they do nothing; remove them with `--guards --undo
--apply`. Restart Claude Code after a change.

The hooks follow https://code.claude.com/docs/en/hooks (Claude Code 2.1.302):
PreToolUse reads `tool_name`, `tool_input.command` and `cwd` and answers
`hookSpecificOutput.permissionDecision: "ask"` with `permissionDecisionReason`;
Stop and SubagentStop read `stop_hook_active`, `last_assistant_message`,
`transcript_path` and `agent_transcript_path` and answer
`{"decision": "block", "reason": ...}`; SessionStart (matcher
`compact|resume|clear`) reads `cwd` and answers
`hookSpecificOutput.additionalContext`.

### Codex

The `.codex-plugin/plugin.json` manifest exposes `./skills/` and declares no
plugin hook; bootstrap comes from the personalization block or the skill's own
trigger. Install through the native plugin channel or use the installer. The
plugin channel needs a reviewed checkout:

```bash
codex plugin marketplace add /path/to/reviewed/nobrainer-tech-flow
codex plugin add nobrainer-tech-flow@nobrainer-tech
```

The installer's `codex` destination is the shared `~/.agents/skills` path:

```bash
python3 scripts/install_skills.py --client codex
python3 scripts/install_skills.py --client codex --apply
```

Restart Codex and test discovery in a fresh task. Repository instructions or the
native skill trigger provide bootstrap; a file on disk is not routing proof.
Use nobrainer-tech-flow for user-facing requests. For the technical explicit
invocation, type the exact name Codex lists for the module, because on Codex
0.157.1 (macOS) the other form adds no module text to the model input. Codex
lists the module under the plugin name, so you type
`$nobrainer-tech-flow:nobrainer-tech-flow`, when a plugin manifest sits above the
folder a link resolves to: a plugin install, the npm package, or the links the
installer makes into a git checkout. It lists the plain name, so you type
`$nobrainer-tech-flow`, for a copy made with `install_skills.py --mode copy`.
[COMPATIBILITY.md](COMPATIBILITY.md) records what was checked. Plain `NBFlow`,
`NBF` and `nobrainer-tech-flow` are natural-language triggers whose recognition
depends on the client. Existing legacy entries under `~/.codex/skills` are not
deleted or rewritten automatically.

### Cursor

Use `.cursor-plugin/plugin.json`. Its session hook runs the shared bootstrap
through `hooks/run-hook.cmd`, which uses Git Bash on Windows: from its install
folders or beside the `git.exe` on PATH, never a `bash.exe` in the current folder.
Without Git Bash the hook says so on stderr and exits 1, and the session continues
without the bootstrap. Repository tests
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

Run `scripts/install.sh` in Git Bash (it comes with Git for Windows), or the
Python scripts with `py -3` or `python`. The hook adapters need Git Bash too, not
the `bash.exe` launcher that Windows ships for WSL (Windows finds that one first
when a command says just `bash`). The repository pins the hook scripts, the shell
installer and the bootstrap to LF endings so a Git checkout with
`core.autocrlf=true` still runs them. Creating symlinks needs developer mode or an
elevated shell; without either, install with `install_skills.py --mode copy`. CI
runs the structure validators, the adapter tests, a Windows smoke module and both
one-command installers on a Windows runner; it does not run the whole suite
there, and no client was read back on Windows.

### Other Agent Skills clients

Use the portable `plugin.json`, the canonical skill directories and explicit
project instructions. Do not claim automatic bootstrap unless the target client
actually exposes and passes that integration.

## Dynamic specialists

The eighteen curated skills are the stable base. When a concrete work unit still
has a capability gap, `nobrainer-team` first inventories installed/project
capabilities, then writes a task-local specialist brief (role, method from
project docs or verified primary sources, allowed actions, write scope and
acceptance) for a native worker. Team never searches for, installs or runs
third-party skills; installing anything is the owner's own separate decision.

## Readback and acceptance

After every install or upgrade:

1. restart the client;
2. list/read back the loaded source and skill count;
3. start a clean task with no pasted skill body;
4. issue one explicit canonical request and one semantic non-trivial request;
   for Codex type the name the client lists for the module:
   `$nobrainer-tech-flow:nobrainer-tech-flow` when it lists modules under the
   plugin name, `$nobrainer-tech-flow` when it lists them plainly (the Codex
   section above says which installs do which);
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
