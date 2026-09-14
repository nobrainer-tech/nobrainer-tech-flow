---
name: nobrainer-codex-context
description: "Use when setting up, auditing or repairing one project's Codex context; use nb-codex-context to inspect AGENTS files, configured fallbacks and byte limits, then make one evidence-backed project-local context change without changing global Codex configuration by default."
---

# NoBrainer Codex Context

Prepare the smallest useful project context for Codex. This skill owns the
project-instruction boundary that Codex reads before a turn; it does not own
model selection, subagent topology, session transfer, or the whole delivery
workflow.

## Select a mode

- `inspect` - read the current project root, instruction candidates, configured
  fallbacks, byte cap and effective document set. Do not write.
- `setup` - inspect first, reconcile the existing instruction files, and add or
  update one marked project-local context block only when it improves the
  actual repository. Run the inspection again after the edit.
- `repair` - fix a known context defect such as duplicate managed markers,
  stale generated content or a truncation-risk block. Do not rewrite unrelated
  instructions.

Use `inspect` for a question. Use `setup` only when the owner asks to prepare
the project or the project has a demonstrated context gap. A clean result is
`CURRENT`; absence, truncation or an unknown runtime is evidence to report, not
permission to invent a fix.

## Codex context contract

Codex's effective project instructions are assembled from the nearest project
root through the current directory. The normal candidates are
`AGENTS.override.md` and `AGENTS.md`; configured fallback names are considered
after them. The configured project-document byte budget applies to the loaded
instruction set and defaults to the host's documented value when no override is
read.

Run the bundled read-only probe with Python 3.11+ before deciding what to change:

```bash
python3 skills/nobrainer-codex-context/scripts/codex_context.py --check --json
```

If the skill is installed outside the repository, run the same script from the
installed skill directory. The probe is an inventory and truncation check; its
exit status does not prove that a live Codex client followed the instructions.

When a project needs a durable NoBrainer context block, preserve all existing
bytes and use exactly these markers in the applicable `AGENTS.md`:

```markdown
<!-- NOBRAINER-CODEX-CONTEXT:START -->
## Project context

- Source of truth: `<verified project files>`.
- First checks: `<verified commands or tests>`.
- Keep this block compact; link to deeper project docs instead of copying them.
<!-- NOBRAINER-CODEX-CONTEXT:END -->
```

Replace the placeholders only with facts read from the current project. Do not
put credentials, private machine paths, mutable runtime state, guessed commands
or model names in the block. If an existing managed block is present, update it
in place; do not create a second one. If an `AGENTS.md` is absent, create it
only when setup is explicitly requested and the project has enough inspected
source facts to make the block useful.

Do not create a `CODEX_CONTEXT.md` file and call it automatically loaded. Codex
will only use an alternate filename when the host's `project_doc_fallback_filenames`
configuration actually includes it; changing that global configuration is an
owner-gated action outside this skill's default setup.

## Safe setup boundaries

- Keep `AGENTS.override.md` precedence and client-managed blocks intact.
- Never replace a whole `AGENTS.md` because it is long, old or from another
  client. Reduce duplication only when the exact duplicate and its owner are
  clear.
- Do not edit `~/.codex/config.toml`, credentials, plugin installation or
  client settings unless the owner explicitly requests that separate action.
- Do not claim `RUNTIME_VERIFIED` from a file read, probe exit code or installed
  skill. If `codex debug prompt-input` or `codex debug agents-md` is available,
  use it for a fresh readback; otherwise report `RUNTIME_READBACK: UNKNOWN`.
- Keep the context block below the project's own required instructions when the
  file's structure makes that safer. Follow the nearest `AGENTS.md` rules.

## Closeout

Return a compact readback:

```text
CODEX_CONTEXT: CURRENT | UPDATED | BLOCKED
PROJECT_ROOT: <path or UNKNOWN>
DOCUMENTS: <ordered discovered files>
FALLBACKS: <configured names or NONE>
BYTE_BUDGET: <observed value or UNKNOWN>
LOADED_BYTES: <observed value or UNKNOWN>
TRUNCATED: YES | NO | UNKNOWN
PROJECT_WRITE: NONE | AGENTS_BLOCK_UPDATED | AGENTS_CREATED
RUNTIME_READBACK: VERIFIED | UNKNOWN | UNSUPPORTED
OWNER_ACTION_REQUIRED: <one exact action or NONE>
ROLLBACK: <exact preimage or NOT_APPLICABLE>
```

Route portfolio-wide semantic instruction or skill audits to
`nobrainer-skill-doctor`; keep one-project Codex context setup and repair here.
Route broader setup, installation or delivery work back to `nobrainer-ultra`.
Use `nobrainer-sessions` for context transfer and `nobrainer-review` for a
release or adversarial closeout; do not duplicate their contracts here.
