# One source of truth with pointers

Use this after an inventory, in `consolidate` or `repair` mode. Everything here
is project-local and needs a preview and explicit approval before any write.

## Choose the source of truth

1. Prefer the root `AGENTS.md`: Codex, Cursor, GitHub Copilot's agent surfaces,
   OpenCode and Claude Code (directly or through an import) can read it.
2. If the project has no `AGENTS.md`, propose moving the shared content of the
   largest current file into one, unless the team uses a single client and
   says it does not want another file.
3. Keep nested `AGENTS.md` files that hold real directory-specific rules; Codex
   and Cursor combine them with the root file, and closer files win.

## Reduce the other files

| File | Keep | Pointer |
|---|---|---|
| `CLAUDE.md` / `.claude/CLAUDE.md` | Claude-only lines | `@AGENTS.md` on its own line |
| `CLAUDE.local.md` | personal, uncommitted lines | none; it stops Claude reading `AGENTS.md` directly, so keep the `@AGENTS.md` import in `CLAUDE.md` |
| `GEMINI.md` | Gemini-only lines | `@AGENTS.md`, or `context.fileName` in project `.gemini/settings.json` listing `AGENTS.md` |
| `.cursor/rules/*.mdc` | path- or task-scoped rules | none needed; Cursor reads `AGENTS.md` |
| `.github/copilot-instructions.md` | lines for surfaces that ignore `AGENTS.md` (Copilot Chat on GitHub.com, code review in IDEs) | no import syntax; keep it short and non-contradictory |
| `.github/instructions/*.instructions.md` | path-scoped rules with `applyTo` | none |
| `opencode.json` `instructions` | extra files OpenCode should add | entries only |

Rules:

- Keep each fact in one file. Delete a duplicate only after the source of truth
  holds the same meaning; when the copies disagree, report the conflict and ask
  which wording wins instead of picking one.
- An import is not free: Claude Code and Gemini CLI load imported files at
  start, so the import moves bytes, it does not remove them.
- A sentence that only tells an agent to read another file is unreliable; use
  the client's import or file-name setting when it has one.
- A byte-identical copy (for example `CLAUDE.md` copied from `AGENTS.md`) is
  drifts, and GitHub Copilot's agent surfaces read both copies. Replace it with the pointer unless the
  project requires the copy; a test that enforces the copy is such a reason.
- Preserve client-managed blocks (for example `NOBRAINER-TECH-FLOW` markers),
  `AGENTS.override.md` precedence and every byte outside the lines you change.
  A `NOBRAINER-CODEX-CONTEXT` block left by an earlier release is ordinary
  project content: keep it, or fold its facts into the source of truth and
  remove the markers in the same approved preview.
- Never create a file a client does not read and call it loaded. A Codex
  fallback name works only when `project_doc_fallback_filenames` lists it;
  changing that global setting is a separate owner action.
- Keep credentials, private machine paths, mutable runtime state, guessed
  commands and model names out of instruction files.

## Preview

Show, for every file: the current bytes, the proposed bytes or a unified diff,
and what each client in use will load afterwards with byte counts. Name the
rollback: the exact preimage of each changed file (or a recoverable copy) and
the files to delete if new. Wait for an explicit yes.

## Apply and read back

Write only the approved files, then run the inventory again. The change is
`UPDATED` when the new inventory matches the preview: the same files per client,
no new truncation, fewer or equal repeated lines and the goal pointer as
proposed. Otherwise restore the preimages and report `BLOCKED` with the
difference.
