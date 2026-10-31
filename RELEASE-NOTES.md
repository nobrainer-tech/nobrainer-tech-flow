# nobrainer-tech-flow release notes

## v2.9.1 - 2026-10-31

A failed test re-run without output could leave an earlier pass marked done. The
MCP done gate now reopens the item until a later test passes.

## v2.9.0 - 2026-10-31

The entry skill gains a `Work to done` section and a finish check, so "from task to
done" no longer depends on the agent's default temperament. Intent is read from the whole
conversation: a request to act is executed, while a question, review or brainstorm gets an
answer without unrequested changes. The full scope stays in force, including requirements
added mid-task; the easier part is never delivered as the whole. Known, authorized next
steps are taken without check-ins, routine reversible details are decided in scope, and
earlier permission is reused. Ambiguity is separated from a blocker: a safe assumption is
named and work continues, only dependent work pauses, and silence is never consent. Before
an unavoidable approval the agent prepares everything already allowed. After a failure it
finds the cause and never repeats an identical attempt. The finish check makes the agent
do any requested, possible and allowed action its reply would only promise, and stop only
on acceptance, an explicit stop or a real blocker with the done part, missing item and
unblock condition. The entry-skill size budget rises to 280 lines and 2150 words. See the
[2.9.0 record](docs/releases/v2.9.0.md).

## v2.8.0 - 2026-10-28

Every finished task now ends with one fixed handoff block: `Delivered`, `Checked` (each
command or check with its observed result) and `Not checked` (each gap with its reason).
A listed gap means done with gaps, not done, the same meaning as the MCP server's
`DONE_WITH_GAPS` verdict. `scripts/validate_skills.py --suite` now fails when the entry
skill loses that block. The verify gate also asks the agent to list each place the task
touched where docs and code disagree.

Seventeen module descriptions now start with the situation they handle instead of a
command alias; the `nb-*` aliases move to the end and still trigger. The entry skill and
the README top section use plain language: "the user" instead of "owner", "main agent"
instead of MAIN in prose, and shorter sentences. Stage tokens such as
`OWNER_DECISION_REQUIRED` do not change. Maintainer-only planning files (`tasks/` and
`docs/reports/paid-run-plan.md`) are no longer tracked, the README chart no longer shows
the optional Jev and Laya profiles, and `docs/COMPATIBILITY.md` now states the real
distribution state. See the [2.8.0 record](docs/releases/v2.8.0.md).

## v2.7.3 - 2026-10-25

Clears the automatic-check warnings that the Claude plugin directory showed. The optional
Jev classifier helper (`typed_decisions.py`) no longer reads a credential from the
machine: the TypeSafe key is piped on stdin with `--key-stdin`, and the old `--key-env`
flag now stops with `KEY_ENV_REMOVED_USE_KEY_STDIN` without reading any variable. The
helper's worker gets only an allowlist of non-secret environment variables. The writing
skill describes the API proof as a `curl` command in a fenced code block instead of a
`bash` block, which the directory read as a download-and-run command. The distribution
repository now ships only `docs/CHAT_PLUGINS.md` and `docs/PRIVACY.md` from `docs/`; its
README links the canonical guides. See the [2.7.3 record](docs/releases/v2.7.3.md).

## v2.7.2 - 2026-10-25

The plugin ZIP now also declares the remote MCP server in a root `mcp.json`. Its root
`plugin.json` carries OpenAI settings, so the OpenAI plugin directory reads the ZIP as a
portable package, ignores `.codex-plugin/plugin.json` and its `.mcp.json`, and reported it
as skills-only. The new file uses the portable format (Agent Plugins schema, one
`streamable-http` server at https://mcp.nobrainer.tech/mcp) and exists only in the ZIP.
See the [2.7.2 record](docs/releases/v2.7.2.md).

## v2.7.1 - 2026-10-25

The plugin ZIP for plugin directories now declares the optional remote MCP server.
OpenAI's plugin directory stopped accepting skills-only submissions, so the ZIP built by
`scripts/build_plugin.py` adds a `.mcp.json` with one server, `nobrainer-tech-flow` at
`https://mcp.nobrainer.tech/mcp`, and its OpenAI manifest points to it with
`"mcpServers": "./.mcp.json"`. Only the ZIP carries it: the Git marketplace and npm installs
stay skills-only and do not connect to the server.

The plugin manifests now link the server's full privacy policy
(https://nobrainer.tech/flow/privacy/) and terms (https://nobrainer.tech/flow/terms/),
and `docs/PRIVACY.md` and `docs/CHAT_PLUGINS.md` describe the declared server. The plugin
descriptions now match 2.7.0: one main loop does the work, and native workers are used only
for parallel work, context isolation, independent review or specialization. Skills and
workflow guidance do not change.

## v2.7.0 - 2026-10-25

From task to done, visibly: before substantial work the agent shows what done means and
sets it as the host's native goal where the host offers one, so the owner can see whether
the goal is running, paused or stopped. The TODO stays visible in the host's plan or todo
tool when it has one, otherwise as the Progress checklist.

Flow now delegates only where it pays. One MAIN loop loads skills on demand and does the
work; a unit goes to a native worker only for parallel work, context isolation, independent
verification or specialization, and the plan names which condition applies. Work is split
by context, so the worker that changes a feature also writes and runs its tests. This
replaces the 2.6.0 default of delegating every independent unit: a worker costs several
times the tokens of the same work in one loop, every handoff loses detail, and parallel
workers often finish later than one loop would. An owner or host rule that asks for more
delegation still controls.

Owner requests no longer live only in the transcript, where compaction can drop them.
When the owner keeps adding requests mid-run, Flow's guidance now has the agent keep a
goal file and record each new request in it as it arrives, before continuing any work,
even when the request is deferred. Each row quotes the owner's words with the date and a
status. While the ledger is active, rows are reconciled at every checkpoint, after
compaction and at closeout, and none may be silently dropped. The default goal file is
`.nobrainer/goal.md`. When the owner changes a decision, the agent updates the goal file
at once, before continuing other work, and keeps instruction files from carrying the old
rule: it edits a contradicting line in `AGENTS.md`, `CLAUDE.md` or a rules file when the
project's learning policy is `AUTO_SCOPED`, prepares the exact diff under `ASK`, and names
the stale line under `OFF`. The goal file also keeps one `CURRENT_MILESTONE`, a short-term
goal derived from the outcome and the open requests: the agent works toward it without
waiting, sets the next one when it is accepted, and re-derives it when the owner changes
what matters most.

The optional Claude Code guards gain a fourth hook: after compaction, resume or clear it
tells the agent to re-read up to three active goal files. It prints only their paths and
status words, never other goal-file text, and prints nothing on any error. If you already
use the guards, update your Git checkout first, preview the change with
`python3 scripts/install.py --client claude --guards`, apply it with `--apply` and restart
Claude Code; the installer now shows an install from an earlier version as an update.

`nobrainer-team` no longer searches for, installs or runs third-party skills. A remaining
capability gap gets a task-local specialist brief for a native worker, kept in the task
plan and discarded afterwards.

`nobrainer-security` no longer reports a clean result after a single pass: one model pass
samples the scope, so at least one more independent pass, started from a different entry
point, trust boundary or data-flow direction, must add no new verified finding first. When
a fixed defect was public or reachable before the fix, the agent checks the available logs
for exploitation during that window, or lists the window as untested. The review rule now
names authentication, permissions, payments and personal data as security-sensitive paths
that need an independent review however small the diff. Work from an untrusted or unknown
author never takes the low-risk path, and a user-interface change needs a screenshot or
recording, before and after where possible, because unit tests alone do not prove it.

When instruction files or docs describe a coding convention that the existing code does not
follow, `nobrainer-build` no longer picks one silently: it follows the code, unless the
instruction is an explicit owner rule or names a deliberate migration, and lists each
disagreement in its final report. When the code wins, the report includes the exact edit
that fixes the stale instruction file, applied only as the learning policy allows; when an
owner rule or migration wins, it names the code change required.

The README now lists the free remote MCP server as an install channel, the docs say the
npm package is published, and an intermittent bounded-runner test failure is fixed.

The module set stays at eighteen. See the
[release scope and verification record](docs/releases/v2.7.0.md).

## v2.6.0 - 2026-10-23

Flow now delegates aggressively, so substantial work reaches done sooner. Independent
units go to native subagents in parallel while MAIN works its own unit and keeps the
critical path, integration and verification. A unit is delegated when parallel work
shortens the time to done more than a worker's start-up costs; each worker gets a short
task packet instead of the whole conversation and returns a concise report, and narrow,
mechanical work goes to a cheaper model under the host's policy. The workflow names no
model. When part of a batch fails, only the failed units are sent again.

Verification depth now follows the blast radius of a change. A reversible, low-risk change
may proceed on green automated tests, review and security checks; CI configuration,
credentials, security-sensitive paths, data migrations and irreversible effects still need
an independent review and stay owner-gated. An agent's approval never counts as the
owner's.

Flow keeps itself updated by default with one line in the instruction block: once a day on
first use it updates to the latest verified stable release from the canonical source, with
a backup, changing nothing else. `install_personalization.py --no-auto-update` writes a
one-line notify-only rule instead. Existing setups keep their choice: the longer lines
written before 2.6.0 become the matching short line, so an old notify-only setup stays
notify-only.

`nobrainer-build` gains two rules: complexity for a speculative race or security edge case
needs a named failure, its likelihood and its cost first, and in user interfaces taglines,
helper text and secondary labels that explain a screen are treated as slop: fix the layout
instead.

## v2.5.0 - 2026-10-20

One set of project instructions for every coding agent. The module
`nobrainer-codex-context` (`nb-codex-context`) is now `nobrainer-context`
(`nb-context`) and covers Codex, Claude Code, Gemini CLI, Cursor, GitHub Copilot and
OpenCode, not only Codex. Its read-only probe, `context_inventory.py`, lists the
instruction files each client loads in one project, with their size against each
client's documented limits (the Codex byte budget, Claude Code's 200-line guidance,
Cursor's 500-line guidance), byte-identical copies, lines repeated across files and
whether the instructions name the current Flow goal file. The module then proposes one
source of truth, usually `AGENTS.md`, with short pointers such as `@AGENTS.md` in
`CLAUDE.md`, and changes project files only after you see the preview and approve it.
It reads the project again afterwards. Global configuration stays untouched unless you
ask. The client rules come from each client's documentation, checked on 2026-10-20 and
cited in the module; anything the documentation does not state is reported as unknown.

The old name and trigger no longer work. Updating a Git checkout through `install.sh` or
`install.py` links `nobrainer-context` and, as its last change, removes the old link the
setup record lists; a run that fails puts the old link back. Undo of an older setup
removes it too. An npm setup is undone with the earlier
release's command first, as before. A file, folder, copy or link at the old name that is not
this checkout's link is left unchanged. The [migration guide](docs/MIGRATION_TO_FLOW.md)
has the details.

The optional TypeSafe helper (`typed_decisions.py`) no longer reads
`TYPESAFE_API_KEY` by itself: name the variable with `--key-env`, and the key reaches the
worker on standard input, not through its environment.

The module set stays at eighteen. See the
[release scope and verification record](docs/releases/v2.5.0.md).

## v2.4.1 - 2026-10-19

Undo works after a rearranged profile. When a link put in place after the setup makes
two folders the setup created lead to one folder, for example `~/.agents` replaced with a
link to `~/.codex`, `install.sh`, `install.py` and the guided `--rollback` now remove the
skill links instead of refusing the record; the link and your folders stay. A setup whose
folders would resolve, through a link, to a path with a line break now stops with exit 2
before anything is written, instead of saving a record no undo can read. Fixes #82. See
the [verification record](docs/releases/v2.4.1.md).

## v2.4.0 - 2026-10-19

nobrainer-tech-flow can ask before risky commands and shows whether its proof still matches
your files.

Optional Claude Code guards (`scripts/install.py --client claude --guards`, preview first,
undo with `--undo --apply`) add a PreToolUse hook that asks before `rm -r` outside
temporary folders, `git push --force` (also `-f`, `--force-with-lease` or a `+branch`
refspec), `git reset --hard`, `git clean -f`, `vercel --prod`, `npm publish`,
`terraform apply` or `destroy`, `kubectl delete` and `gh release create`, also with
global options before the subcommand. The preview names only the hooks it changes,
never other settings. A Stop hook blocks once when a turn that changed files or ran
commands ends with no `Proof:` or `Checked:` line and no `UNVERIFIED`. The guards are
off by default, exist for Claude Code only and are written to your user settings; the
plugin hooks stay SessionStart only. They read command text, so they are a seatbelt,
not a security boundary.

An optional evidence receipt (`skills/nobrainer-sessions/scripts/evidence_receipt.py`)
records a declared set of input files before and after one command, then reports
`CURRENT`, `STALE`, `CHANGED_DURING_RUN` or `UNAVAILABLE`. The closeout now names the
input snapshot or time the proof is current for, or `UNKNOWN`, and a worker's `RETURN`
line starts with the outcome as the worker understood it, so a misread surfaces first.

The proof contract is stricter. Build reports `TEST_SENSITIVITY` (`PROVEN`,
`PARTLY_PROVEN`, `NOT_PROVEN` or `NOT_APPLICABLE`) for a behavior-preserving rewrite, and
Review keeps a "no behavior change" claim open when it is missing or `NOT_PROVEN`; it
also does not accept `STALE` or `CHANGED_DURING_RUN` evidence as proof of the current
artifact. Model routing gives routine units the lowest effort that meets acceptance, a
shared assignment prefix and a stop at the unit budget. A plaintext credential file an
agent can read counts as secret exposure. A deterministic failure should get a native
check before a prose rule.

Skill doctor gains a report-only instruction-debt audit (`context_candidates.py`) for
stale, repeated or conflicting rules after a model or client upgrade, and the
visible-session rule now lives in one place that other modules link to.

The README first screen leads with the verified Claude Code and Codex plugin installs.
The Codex marketplace is renamed `nobrainer-tech-skills-dev` to `nobrainer-tech`, the
same as the Claude one; the [migration guide](docs/MIGRATION_TO_FLOW.md) has the
commands for the old name. Manifests describe one workflow of 18 modules. The npm package
is still not published on npm; use the Git install or a plugin.

No benchmark was run and no model is imposed. See the
[release scope and verification record](docs/releases/v2.4.0.md).

## v2.3.2 - 2026-10-18

Install, update and undo nobrainer-tech-flow without false alarms or leftovers. A
second undo now says that nothing is recorded to undo and exits cleanly instead of
failing. Undo puts your profile back as it was before the setup, including the empty
folders the installer had to create, such as `~/.agents` for Codex or
`~/.config/opencode` for a client that never ran; the `.bak` copy of an instruction
file you already had stays. Updating through `install.sh` now delivers the current
instruction block, as `install.py` already did, and keeps every byte outside the
managed markers. Applying again when nothing changed says `UP TO DATE` and gives no
restart hint.

The instruction block now tells the model to use the name your client lists for the
module, and the README and the repository instruction files give the same rule. Codex
0.157.1 lists the module as `nobrainer-tech-flow:nobrainer-tech-flow` when it is linked
from a git checkout or the npm package, and it loads the module only for that typed
name; a copy is listed as `nobrainer-tech-flow`. The setup record
(`.nobrainer-flow-onboarding-<client>.json`) and the owner-only mode of the files the
installer writes are now described, and undo deletes the record.

Undo now removes the skill links even after you edited the instruction file; it leaves
the edited file as it is, exits 3 with `PARTLY UNDONE` and says how to take the block
out too. Once the block is deleted by hand, the next undo finishes. The default block no longer tells every user to load the private
`nobrainer-ak` skill; the next apply replaces a 2.3.1 block (through `install.sh` only
when the block holds no option; `install.py` always, keeping its options). The npm command keeps
its release copy in `~/.nobrainer-tech-flow-npm`, so cleaning a Git clone in
`~/.nobrainer-tech-flow` cannot delete it. The Windows hook wrapper no longer runs a
`bash.exe` from the current folder, returns the hook's exit code and says when Git Bash
is missing. Undo also keeps folders that now lie under a link, removes a home made only
for the record, and stops on a dangling older record.

Five instruction fixes from a review of 2.3.1 also ship. The README leads with the
Git install while the npm package is unpublished. Flow owns one corrective-attempt
budget (two attempts per observed failure), and Build and RCA link to it instead of
saying three. Dispatcher accepts the worker ID a host returns for a hidden native
worker as the send receipt, so default delegation can be dispatched; visible sessions
still go through Sessions. Saying "Use NBFlow" turns on session health observation
only: a restart or archive needs separate owner consent, and the quick path skips
startup care. Stale status lines, an undefined "team cap" and two lifecycle names are
corrected, and every approval-gate list includes contacting people.

The module set stays at eighteen. The native plugin 2.3.2 will carry the same
installer; npm registry publication is still pending.

See the [release scope and verification record](docs/releases/v2.3.2.md).

## v2.3.1 - 2026-10-13

Keep your own skill under a name Flow retired and still install or update Flow.
A private `nobrainer-reddit` no longer blocks `install_skills.py`, the `install.py`
and npm setups that call it, or the no-Python `install.sh`. It stays unchanged
through apply, repeat and undo; `install_skills.py` and `install.sh` report it as
`PRESERVED_FOREIGN`, while `install.py` and npm continue without a separate line.
Foreign targets at renamed aliases such as `nb-flow` still stop installation, so
nothing silently shadows a Flow trigger. Exact old links from the same checkout
still require explicit migration.

This is an installer-only fix. The eighteen skill contents are unchanged except
for the entry skill's `VERSION` file. The native plugin 2.3.1 will carry the same
installer; npm registry publication is still pending.

See the [release scope and verification record](docs/releases/v2.3.1.md).

## v2.3.0 - 2026-10-12

Use available native workers for independent work while the main session keeps
the task coordinated and the result checked. The delegation-first default sends
every useful independent ready unit promptly, within verified host capacity and
authorized usage. The main session integrates and verifies artifacts, then
refills free slots without waiting for unrelated slow workers.

Workers receive a compact task packet with scope, inputs, dependencies, method,
model and effort, authority, acceptance, budget, stop conditions and return
requirements. A builder-readiness check resolves implementation gaps before a
large or risky group of writers starts. Existing ownership, identity and
permission safeguards remain in place; the portfolio is still eighteen skills.

This is an instruction contract, with no runtime benchmark or measured speed or
token saving. Native worker availability depends on the client. npm registry
publication remains pending owner publisher access; the registry currently
returns 404. The separate native plugin export follows the GitHub release.

See the [release scope and verification record](docs/releases/v2.3.0.md).

## v2.2.1 — 2026-10-05

Install nobrainer-tech-flow through the npm command and load the same eighteen modules as a portable skills plugin. Preview and undo stay explicit; retained source files keep npx cache cleanup from breaking your setup.

See [distribution scope and proof boundaries](docs/releases/v2.2.1.md). npm and directory publication need their own public readback.

## v2.1.1 - 2026-10-02

- Plain technical English is now the default for operational exchanges between
  agents: assignments, progress, findings, reports and handoffs. Explicit language
  requests, required schemas and exact source text still take precedence.
- User replies are written directly in the requested language, with the same
  facts, conditions, permissions and evidence. No English intermediary or extra
  translation provider is required.
- Writing selects TECHNICAL by default for English technical artifacts when no
  other mode is requested. Ordinary conversation, marketing and creative work
  keep their purpose and requested voice while using clear language.
- The eighteen-skill portfolio, models, benchmark settings and installers stay
  unchanged. This is an instruction default, not a formal ASD-STE100 checker or
  a measured performance claim.

See the [verification record](docs/releases/v2.1.1.md).

## v2.1.0 - 2026-10-02

- Start with an idea. SDD makes the agreed scope and acceptance checks explicit;
  an end-to-end request carries them through implementation, review and evidence.
  A spec-only request stays spec-only. Existing authorization covers routine
  reversible choices, while material product and risk decisions remain visible.
- Autopilot carries supplied or generated plans through ready work, checks and
  confirmed corrections. Blocked requirements stay open while independent work
  advances. This guides the active client; it adds no unattended service.
- Writing adds a `TECHNICAL` mode for plain English procedures and explanations,
  informed by ASD-STE100 and Karpathy's suggestion. It preserves commands,
  permissions, conditions and uncertainty. It is not a full compliance checker
  and does not claim measured token or cost savings.
- Includes the source changes since 2.0.2, including the clarified autopilot
  loop. The portfolio remains eighteen skills. No automatic model benchmark,
  provider activation or model-setting change is included.

See the [verification record](docs/releases/v2.1.0.md).

## v2.0.2 - 2026-09-29

- Install without Python: paste the prompt from the README into your agent, or run
  `sh scripts/install.sh --client claude` (macOS, Linux, WSL, Git Bash on Windows).
  It previews, `--apply` links all skills and adds the instruction block, and
  `--undo --apply` reverses it. `python3 scripts/install.py` does the same with
  Python; both share the setup record, so either one undoes the other.
- Undo now puts the instruction file back as it was before the first setup, even
  after later installs, and keeps edits made outside the managed block since (for
  setups recorded by 2.0.2; see the verification record for older records).
- A Claude file counts as inheriting the Codex instructions only when it holds
  nothing but the import line; every other Claude file gets its own block. The
  earlier check skipped the block for files Claude Code does not import.
- Fixes from an independent review of 2.0.1: an unusable environment variable that
  the selected client never reads no longer stops it (or its undo); a grant can no
  longer be forged from a wiki path or preference through a line-separator
  character; a symlink-loop destination is reported on Python 3.13; a planted
  `.pyc` in a copy install is a conflict again; a home path that is not valid
  UTF-8, holds a line break or is not absolute is refused before anything is
  written.
- Fixes from a review of the new scripts: undo hints keep `--home` and name the
  variable a setup was made with, runs at the same time no longer write into the
  checkout, and `install.sh` handles `CDPATH`, `--home=~/x`, old Mac line breaks and
  the paths the Python scripts refuse.
- Contains everything in 2.0.1; see both verification records.

See the [verification record](docs/releases/v2.0.2.md).

## v2.0.1 - 2026-09-29

- Corrective release: no new skill. Skill text changes only to fix helper paths
  and to say what to do when `nobrainer-sessions` is not installed.
- Codex: the marketplace entry now installs and the default prompts fit the
  client's limit, so they are no longer dropped.
- Windows: copy-mode installs work, hook scripts stay LF, and CI has a Windows job.
- Installers and guided setup follow `CLAUDE_CONFIG_DIR`, `CODEX_HOME` and
  `XDG_CONFIG_HOME`, keep earlier auto-update, session-restart and wiki-root
  settings, and report symlink loops, a file destination and missing input
  instead of crashing or hanging.
- A Claude profile that imports a Codex file without the Flow block now gets the
  block instead of silently getting nothing.
- OpenCode and Pi keep the bootstrap after compaction and survive a missing file.
- README, INSTALL and COMPATIBILITY corrected; the version gate now covers the
  skill `VERSION` file and the lockfile.

See the [verification record](docs/releases/v2.0.1.md).

## v2.0.0 - 2026-09-27

- Canonical product, package and entrypoint name: `nobrainer-tech-flow`.
- Adds standard Auto Fine Tune onboarding to the 18-module workflow.
- Read-only preflight, stable selection IDs, scoped setup, client-specific
  personalization, readback and rollback through the existing installer.
- Preserves MAIN while coordinating useful available workers and task-sized goals.
- Adds daily active-use update checks, browser preferences and guarded worktree cleanup.
- Removes internal working reviews and raw evaluation artifacts from the current tree.

This major version changes package/entry identities. Read the
[migration guide](docs/MIGRATION_TO_FLOW.md) and
[verification record](docs/releases/v2.0.0.md) before upgrading.


## v1.14.1 - 2026-09-22

- Team makes multi-capability coverage and durable source provenance explicit.
- Research distinguishes empty, incomplete, unavailable and unattempted sources.
- Build records known simplification ceilings with observable revisit triggers.
- Keeps one-model execution, existing owners and optional profile settings intact.

See [scope and evidence limits](docs/releases/v1.14.1.md).

## v1.14.0 - 2026-09-22

- Optional core/Jev/Laya preferences with one-time setup and explicit changes.
- Default-off advisory typed decisions with data approval, bounded calls,
  validated answers and core fallback; local Laya loads only cached weights.
- Keeps the seventeen-skill workflow available with one host-selected model.
- Reviews ten popular skill repositories without importing competing workflows.
- Live synthetic Jev/Laya primitive checks and 201-test Linux/macOS CI evidence.

See [scope and proof limits](docs/releases/v1.14.0.md).

## v1.13.0 - 2026-09-14

- Adds `nobrainer-skill-doctor` as the 17th Flow skill for cross-project audits
  of skills, project instructions and task prompts.
- Includes the finalized read-only inventory helper with explicit symlink and
  traversal-error coverage, plus its disposable fixture tests.
- Applies accepted, bounded fixes to session creation reconciliation, SDD state
  vocabulary, Security mode selection, Autoimprove strict caps, Writing scope
  and Browser local-first capability discovery.
- Keeps historical evaluation receipts bound to their original source instead of
  comparing them with later mutable skill bytes.
- Keeps source validation, client loading, runtime behavior and distribution as
  separate evidence layers. This is a release candidate: no tag, publication or
  real-client installation is claimed here.

See [v1.13.0](docs/releases/v1.13.0.md) for scope, checks and limits.

## v1.12.0 - 2026-09-11

- GDD keeps one full-scope goal, explicit milestone TODO and evidence-based continuation.
- BUDDY records missing consequential permissions once; autopilot checks authorized
  UI/API/CLI alternatives and continues independent work before escalating blockers.
- Team builds specialists from inspected skills; Dispatcher fills useful ready slots
  within native capacity and a global maximum of 15 active subagents.
- Codex delegated execution defaults to Luna/max, preserving MAIN and owner overrides.
- Maintained display copy uses `nobrainer-tech-flow`; technical IDs remain compatible.

See [v1.12.0](docs/releases/v1.12.0.md) for verification boundaries.

## v1.11.0 - 2026-09-11

- Adds the original `nobrainer-codex-context` skill for project-local Codex
  instruction discovery, fallback and byte-budget inspection, safe managed-block
  setup and runtime readback.
- Expands the curated source portfolio from fifteen to sixteen skills without
  changing existing skill names, aliases or client adapter contracts.
- Keeps global `~/.codex/config.toml`, credentials, plugin installation and live
  client state outside the default setup scope.

See the [v1.11.0 release record](docs/releases/v1.11.0.md) for scope, checks and
runtime limits.

## v1.10.0 - 2026-09-10

- Explicit NoBrainer.Tech Flow entry now performs bounded session startup care:
  verified title/date formatting, context observation and health assessment at
  accepted milestones, while preserving native host consent and manual fallback.
- Native subagents remain the delegated-work path; visible conversations require
  an owner request or authorized MAIN restart.
- Maintained public copy uses NoBrainer.Tech Flow while technical skill and
  package identifiers remain compatible.

See the [v1.10.0 release record](docs/releases/v1.10.0.md) for scope and limits.

## v1.9.0 - 2026-09-10

- `nobrainer-decide` now has one canonical depth contract: `just decide`/
  `just-decide` for a fast choice, `decide`/`nb-decide`/`nobrainer-decide` for
  standard analysis, and `deep decide`/`deep-decide` for deeper analysis.
- Decision ranking now screens feasibility, deadline, budget and minimum
  reliability before scoring, compares full cost and time to useful output,
  handles growth and reversibility, and does not force panels, models or score
  gaps when evidence does not support them.

See the [v1.9.0 release record](docs/releases/v1.9.0.md) for scope and limits.

## v1.8.1 — 2026-09-06

- Fresh-session transfers now keep a stable task title and append each session's
  own ` | started DD-MM` date where the client supports title creation or rename.
  The full timestamp and timezone remain in the registry, existing suffixes are
  replaced instead of stacked, and titles never replace ID-based verification.

## v1.8.0 — 2026-09-06

- Ships the adaptive session-restart protocol and deterministic decision helper
  inside the existing Sessions skill, with explicit handoff, takeover and
  rollback boundaries.
- Includes portable context, exact-head review, bounded retry and focused-review
  refinements adopted from the source-backed OpenAI Codex review.
- Keeps the fifteen-skill portfolio, package/plugin identities and client-neutral
  adapters intact; this release adds no watcher daemon, scheduler or global hook.

See the [v1.8.0 record](docs/releases/v1.8.0.md) for verification limits and the
`v1.7.1` rollback anchor. Source preparation does not by itself prove a GitHub
release, client loading, marketplace distribution or model-quality improvement.

## v1.7.1 — 2026-09-05

- The product is now **NoBrainer.Tech Flow**: **From task to done.**
- Maintained repository links use `nobrainer-tech/nobrainer-tech-flow`; the product
  website is [nobrainer.tech/flow](https://nobrainer.tech/flow/).
- Package/plugin IDs, marketplace IDs, all fifteen skill names and compatibility
  aliases such as `nb-ultra`
  commands remain unchanged so existing installations retain their identity.
- This is a naming and documentation release. Skill behavior, adapters and the
  bounded command runner are unchanged; historical evidence retains its provenance.

See the [migration guide](docs/MIGRATION_TO_FLOW.md) and
[v1.7.1 record](docs/releases/v1.7.1.md) for verification and publication boundaries.

## v1.7.0 — 2026-09-05

Adds an optional Python/POSIX bounded command runner inside Sessions: explicit
argv, wall-time and combined output limits, owned process-group cleanup and
new-only receipts. No daemon, global hook, model-token or cost-cap claim.

The first-use guide and earlier install section make the existing fifteen skills
easier to try. A 435-discovery Trending screen and pinned source review inform
the release; no cross-product model-quality benchmark is claimed.

See [verification and limits](docs/releases/v1.7.0.md),
[runner usage](docs/BOUNDED_RUNNER.md).

## v1.6.1 — 2026-09-05

- Explicit user instructions take precedence over skill guidelines within the host hierarchy.
- A skill-caused pause identifies the exact source and explains the applicable requirement.
- Verification stops after acceptance and required checks pass, unless new evidence warrants more.
- Setup reconciles stale or conflicting project instructions before adding more.
- Historical runtime evidence now checks its frozen source archive, so later edits cannot inherit old proof.
- The fifteen-skill portfolio and existing prompt-size caps remain unchanged.

See [verification and limits](docs/releases/v1.6.1.md).

## v1.6.0 — 2026-09-04

- Clear coding and everyday tasks take a direct path, including chat-only and non-Git work.
- Optional native goals and telemetry no longer block bounded safe execution;
  explicitly required hard budgets and unknown writer ownership still stop dependent work.
- Empty queues distinguish waiting, auditing, completion and real owner decisions.
- Native subagents use scoped assignments without forced persistent sessions.
- Setup reuses existing TODO/spec/wiki structures; consumer projects do not need
  new SVG/Mermaid diagrams merely to satisfy a workflow rule.
- Existing authorization is preserved; corrective attempts are bounded and stop
  when acceptance passes.
- Current Astra positioning, dated ecosystem research and scoped model evidence
  replace stale availability statements. No universal cost or quality guarantee.

See [verification and runtime limits](docs/releases/v1.6.0.md).

## v1.5.0 — 2026-09-02

This published source release keeps exactly fifteen portable skills and closes
the v1.4.0 public-surface coherence gap.

Highlights:

- `nobrainer-ultra` now freezes a portable `STANDARD`/`EXTENDED`/`ROUTED` model
  policy with explicit model, effort, budget and escalation fields; Dispatcher
  and Sessions carry the policy without silently switching models.
- The README presents v1.5.0 as an Astra Ready Flow for current Codex and
  Claude Fable 5.1 / Mythos 5.1 workflows, with direct runtime compatibility
  kept evidence-scoped.
- `nobrainer-ultra` now requires a `PUBLIC_SURFACE` decision for every change:
  update affected README, docs, templates, assets and flow, or record
  `NOT_NEEDED` with a reason. Public contract, routing and workflow changes use
  the full lifecycle and require fresh SVG and README Mermaid readback.
- `nobrainer-writing` now uses a compact `ENV:` block for bugs and comments;
  bug reports omit speculative workaround and root-cause fields, while feature
  issues keep a one-sentence Description, affected user, desired outcome and evidence.
- The quick path is limited to small reversible edits with no public contract,
  routing, workflow or portfolio impact.
- `CONTRIBUTING.md` and the pull-request template carry the same coherence
  checklist for human review.
- README's Mermaid flow and `assets/nobrainer-workflow.svg` now show the quick
  path and coherence gate.
- The v1.4.0 publication gap is recorded in
  [`docs/releases/v1.4.0-publication-readback.md`](docs/releases/v1.4.0-publication-readback.md).

Source publication is verified in the
[`v1.5.0 publication readback`](docs/releases/v1.5.0-publication-readback.md).
The pre-publication checkpoint remains in [`docs/releases/v1.5.0.md`](docs/releases/v1.5.0.md),
and direct provider runtime support remains separately evidence-scoped.

## v1.4.0 — 2026-09-02

This published source release keeps exactly fifteen portable skills:

- `nobrainer-ultra`
- `nobrainer-team`
- `nobrainer-dispatcher`
- `nobrainer-research`
- `nobrainer-writing`
- `nobrainer-build`
- `nobrainer-security`
- `nobrainer-sessions`
- `nobrainer-spec-driven-development`
- `nobrainer-wiki`
- `nobrainer-browser`
- `nobrainer-autoimprove`
- `nobrainer-decide`
- `nobrainer-rca`
- `nobrainer-review`

Highlights:

- `nobrainer-ultra` now has an explicit quick path for one coherent,
  reversible small change, with a local check and diff/status readback before
  reporting; risk, scope or owner-gate expansion escalates to the full flow.
- `nobrainer-writing` uses one environment block for bugs and comments, containing
  the environment name, exact URL and user used; bug reports keep only an
  explicit `Description` and use `Evidence` for UI screenshots or MP4 recordings.
- API request/response and database query/result proof remain separate and
  copyable, while the public bug template follows the same contract.

The source release is merged in PR #35 at commit
`215c0bb0d6dbfe9b45ecf3202ec198a2c219b3b2`, tagged as `v1.4.0` and published on
GitHub. The archive and installation readback are recorded in
[`docs/releases/v1.4.0-publication-readback.md`](docs/releases/v1.4.0-publication-readback.md),
which also records the post-release coherence gap that v1.5.0 closes.

## v1.3.1 — 2026-09-02

This published source release keeps exactly fifteen portable skills:

- `nobrainer-ultra`
- `nobrainer-team`
- `nobrainer-dispatcher`
- `nobrainer-research`
- `nobrainer-writing`
- `nobrainer-build`
- `nobrainer-security`
- `nobrainer-sessions`
- `nobrainer-spec-driven-development`
- `nobrainer-wiki`
- `nobrainer-browser`
- `nobrainer-autoimprove`
- `nobrainer-decide`
- `nobrainer-rca`
- `nobrainer-review`

Highlights:

- `nobrainer-writing` adds the English-first `BRIEF` mode and the `nb-brief`
  alias for short comments, bug reports, issues, user stories and requests.
- Bug reports keep `Environment`, `URL`, `Steps to reproduce`, `Current
  behavior`, `Expected behavior` and `Evidence` as separate fields.
- API evidence requires request and response, database evidence requires a
  read-only query and result, and UI evidence requires a screenshot or MP4.
  Missing required proof returns `INPUT_REQUIRED` instead of a weaker substitute.
- The repository's public bug template follows the same diagnostic contract;
  no sixteenth skill or client-specific fork was introduced.

The source release is merged in PR #33 at commit
`d1e0ea761d4bf439973727668ee871e2b367797e`, tagged as `v1.3.1` and published on
GitHub. The exact publication evidence is recorded in
[`docs/releases/v1.3.1-publication-readback.md`](docs/releases/v1.3.1-publication-readback.md);
the candidate checkpoint and BRIEF evaluation remain available in
[`docs/releases/v1.3.1.md`](docs/releases/v1.3.1.md) and
[`the BRIEF evaluation`](docs/evals/v1.3.1-writing-brief-2026-09-02.md).

## v1.3.0 — 2026-09-01

This published source release keeps exactly fifteen portable skills:

- `nobrainer-ultra`
- `nobrainer-team`
- `nobrainer-dispatcher`
- `nobrainer-research`
- `nobrainer-writing`
- `nobrainer-build`
- `nobrainer-security`
- `nobrainer-sessions`
- `nobrainer-spec-driven-development`
- `nobrainer-wiki`
- `nobrainer-browser`
- `nobrainer-autoimprove`
- `nobrainer-decide`
- `nobrainer-rca`
- `nobrainer-review`

Highlights:

- Ultra uses a short natural-language scope and Progress checklist for ordinary
  work; a durable ledger appears only for dependencies, handoff, recovery,
  multiple writers or consequential external effects.
- The scope guard now names expected files, proof, untouched work, the minimum
  solution and clean completion before a non-trivial write.
- Stable local errors start from local evidence. Current, uncertain or
  high-stakes remedies still route to bounded primary-source research.
- Codex installation follows the shared `.agents/skills` convention and
  documents `$nobrainer-ultra` as the canonical explicit invocation. The short
  alias remains an implicit-routing hint, not a second skill name.
- Public automation may fetch remote refs but cannot commit, push, open a PR or
  merge. Versioned guards reject backup paths and automated commit identities.
- Every current public head and release tag was checked for the exact retired
  backup identity and trailer. Affected refs were rewritten with exact leases
  while preserving every source tree; unrelated historical authors and
  committers were intentionally preserved. GitHub-managed historical
  pull-request refs remain outside repository write control.
- Root instructions and Ultra are smaller while preserving owner gates,
  correction, recovery, review and receive-audit boundaries.
- Autoimprove now separates candidate and evaluator ownership, calibrates the
  scoring path, binds per-trial receipts, handles noise and continues Pareto-
  sized fresh experiments after a rejected candidate. A bundled counter makes
  serialized-newline word limits reproducible.
- The final5 candidate passed three paired repetitions and a sealed holdout;
  the full evidence is in the [Autoimprove receipt](docs/evals/artifacts/v1.3.0-autoimprove-integrity-final5-receipt.md).

The source release is merged in PR #31 at commit
`8ae4a26548ce908fc5f98b22663f52e163541f56`, tagged as `v1.3.0` and published on
GitHub. Client compatibility remains separate: alias discovery and marketplace
distribution require their own clean-session readback. Exact release and
behavioral evidence are recorded in [the v1.3.0 post-release readback](docs/releases/v1.3.0-publication-readback.md).

## v1.2.1 — 2026-08-28

This patch release contains exactly fifteen portable skills:

- `nobrainer-ultra`
- `nobrainer-team`
- `nobrainer-dispatcher`
- `nobrainer-research`
- `nobrainer-writing`
- `nobrainer-build`
- `nobrainer-security`
- `nobrainer-sessions`
- `nobrainer-spec-driven-development`
- `nobrainer-wiki`
- `nobrainer-browser`
- `nobrainer-autoimprove`
- `nobrainer-decide`
- `nobrainer-rca`
- `nobrainer-review`

The patch makes the frozen-payload attributes test portable. It now verifies
real `git check-attr` behavior in an isolated temporary repository, so a source
archive without the repository's `.git` directory receives the same strict
check instead of failing before validation.

This version is published as a tagged GitHub source release at commit
`0010140d19a7ff847dff776569772ef04d82c314`. Current tag identity,
tree-equivalent historical CI, downloaded archive parity and checksum, 88/88
archive-native tests, secret scan and an
isolated fifteen-skill copy-install readback are recorded in
[the v1.2.1 evidence](docs/releases/v1.2.1.md). This is not a claim of client
marketplace publication, native loading or clean-session runtime behavior.

## v1.2.0 — 2026-08-28

The release contains exactly fifteen portable skills:

- `nobrainer-ultra`
- `nobrainer-team`
- `nobrainer-dispatcher`
- `nobrainer-research`
- `nobrainer-writing`
- `nobrainer-build`
- `nobrainer-security`
- `nobrainer-sessions`
- `nobrainer-spec-driven-development`
- `nobrainer-wiki`
- `nobrainer-browser`
- `nobrainer-autoimprove`
- `nobrainer-decide`
- `nobrainer-rca`
- `nobrainer-review`

Highlights:

- Dispatcher owns dependency readiness, bounded batch selection, backpressure
  and audited result routing without duplicating Team or Sessions.
- Ultra routes multiple delegated work units through Team, Dispatcher and
  Sessions, while one coherent task stays in MAIN.
- Raw worker reports and `NEXT_ACTION` never release dependent work before an
  independent receive-audit.
- Writing compresses messages, comments and documents without dropping facts,
  caveats, voice or action, and retires detector-oriented humanizer behavior.
- The problem gate checks targeted wiki context and current internet evidence
  before choosing a remedy for an error, ambiguity or complication.
- Installer mappings retire generic dispatcher aliases into one canonical
  skill, and all adapters share the same fifteen-skill source tree.
- Copy installs are verified in private staging and published with atomic
  no-replace semantics, so a concurrent foreign target is preserved.

This version was published as a tagged GitHub source release at commit
`46feb1e95567db6967ea718cb75051c507ada02f`. Its tree-equivalent historical CI,
source parity, secret scan, skill validation and isolated installer readback passed, but the
downloaded archive exposed one environment-dependent test that assumed the
presence of `.git`. It is therefore published but not fully accepted and is
superseded by the accepted `v1.2.1` release. The complete boundary is recorded
in [the v1.2.0 evidence](docs/releases/v1.2.0.md).

## v1.1.0 — 2026-08-28

The release contains exactly thirteen portable skills:

- `nobrainer-ultra`
- `nobrainer-team`
- `nobrainer-research`
- `nobrainer-build`
- `nobrainer-security`
- `nobrainer-sessions`
- `nobrainer-spec-driven-development`
- `nobrainer-wiki`
- `nobrainer-browser`
- `nobrainer-autoimprove`
- `nobrainer-decide`
- `nobrainer-rca`
- `nobrainer-review`

Highlights:

- Ultra now creates a complete skill-routed execution map after one focused
  requirements round, then continues through routine approved work.
- Team separates capability/role design from Sessions transport and can inspect
  local skills or safely evaluate one temporary external specialist.
- Research, Build and Security own current evidence, implementation quality and
  trust-boundary risk instead of leaving those concerns implicit.
- Correction hooks update superseded decisions, project lessons and durable
  wiki knowledge without duplicating mutable truth or secrets.
- Failed Review routes back to Build and requires fresh verification/review.
- The workflow graphic, adapters, installer, aliases and behavior tests are
  aligned with the thirteen-skill inventory.
- Installer migration and failed-copy rollback never delete a quarantined
  pathname after fingerprinting; exact recovery claims are preserved and
  reported for post-readback manual cleanup.

This version is published as a tagged GitHub source release at commit
`711be31d654835a04ef8c70674c3e493aeb2da8a`. Current tag identity, archive
SHA-256, file parity, tree-equivalent historical CI, tests, secret scan and
isolated installer readback are recorded in
[the v1.1.0 evidence](docs/releases/v1.1.0.md). This is not a claim of
publication in npm or any client marketplace, nor of native client loading or
runtime behavior.

## v1.0.0 — 2026-08-28

The first stable source release contains exactly nine portable, lightweight
skills:

- `nobrainer-ultra`
- `nobrainer-sessions`
- `nobrainer-spec-driven-development`
- `nobrainer-wiki`
- `nobrainer-browser`
- `nobrainer-autoimprove`
- `nobrainer-decide`
- `nobrainer-rca`
- `nobrainer-review`

The same canonical skill tree is packaged with thin repository-checked adapters
for Claude Code, Codex, Cursor, OpenCode, Gemini CLI, Kimi Code, Pi and generic
Agent Plugins consumers. External capability portfolios are not copied into this
package.

This version is published as a tagged GitHub source release. Exact release,
tag-to-commit, CI and downloaded-archive readback are recorded in
[the v1.0.0 evidence](docs/releases/v1.0.0.md). This is not a claim of publication
in npm or any client marketplace, and adapter checks are not clean-session
runtime proof. Current evidence and limits are recorded in
[the compatibility matrix](docs/COMPATIBILITY.md) and
[the testing guide](docs/TESTING.md).

Install the exact reviewed commit behind `v1.0.0`:

```bash
git clone https://github.com/nobrainer-tech/nobrainer-tech-skills.git
cd nobrainer-tech-skills
git checkout --detach 55c49f40d7dc4ebe900f139711cd46617c706233
test "$(git rev-parse HEAD)" = "55c49f40d7dc4ebe900f139711cd46617c706233"
python3 scripts/validate_skills.py --suite
python3 scripts/install_skills.py --client codex
```

Review the dry-run before adding `--apply`. To roll back a local install, remove
only links created from this checkout or restore the exact previously reviewed
Git ref recorded by the project; do not delete a shared skills directory.

## Release history and rollback sources

Moved from the README. Each entry links to its verification record.

At source version **2.7.3**, check the
[latest published GitHub release](https://github.com/nobrainer-tech/nobrainer-tech-flow/releases/latest)
for distribution and the [2.7.3](docs/releases/v2.7.3.md), [2.7.2](docs/releases/v2.7.2.md), [2.7.1](docs/releases/v2.7.1.md) and
[2.7.0 verification records](docs/releases/v2.7.0.md) for
the current scope, reproducible checks and client-runtime limits. The unchanged command runner keeps its
[v1.7.0 verification scope](docs/releases/v1.7.0.md). Source publication does not
imply client marketplace discovery or improved model reasoning. The earlier
[v1.6.1 publication readback](docs/releases/v1.6.1-publication-readback.md)
remains historical evidence.

Version [`v1.5.0`](docs/releases/v1.5.0-publication-readback.md) remains an
accepted rollback source release. Its historical pre-publication checkpoint is
[`docs/releases/v1.5.0.md`](docs/releases/v1.5.0.md).

Version [`v1.4.0`](docs/releases/v1.4.0-publication-readback.md) remains the
previous accepted source release and rollback option. Client-specific runtime
rows remain evidence-scoped; source publication does not imply marketplace
discovery.

The [`v1.3.1` release](docs/releases/v1.3.1-publication-readback.md) remains the
previous accepted source release and a rollback option. It adds the English
`BRIEF` writing mode, concise issue/story templates and surface-specific bug
evidence.

The [`v1.3.0` release](docs/releases/v1.3.0-publication-readback.md) remains an
older accepted source release and rollback option.

Version [`v1.2.1`](docs/releases/v1.2.1.md) remains the rollback source release
at full commit `0010140d19a7ff847dff776569772ef04d82c314`, with its own exact
tag, archive and isolated-install evidence. To reproduce the reviewed v1.3.0
source:

```bash
git checkout --detach 8ae4a26548ce908fc5f98b22663f52e163541f56
test "$(git rev-parse HEAD)" = "8ae4a26548ce908fc5f98b22663f52e163541f56"
python3 scripts/validate_skills.py --suite
python3 -m unittest discover -s tests -q
```

`v1.2.0` remains published but failed archive acceptance; its exact boundary is
[recorded separately](docs/releases/v1.2.0.md). GitHub reports the `v1.2.1`
release object as non-immutable and tag protection was not independently
verified, so security-sensitive consumers should pin the full commit SHA. The
current tag archive was re-read after the metadata-only history rewrite and
passed 88/88 tests; historical CI binds the same tree, not the current commit
identity.
[`v1.1.0`](docs/releases/v1.1.0.md) remains the accepted rollback anchor at full
commit `711be31d654835a04ef8c70674c3e493aeb2da8a`.
