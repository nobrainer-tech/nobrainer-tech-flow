# What each client loads

Checked against official documentation on 2026-10-20. Client behaviour changes;
re-check the cited page before relying on a number, and report anything newer as
fresh evidence. `UNVERIFIED` means the official pages read did not document it:
treat it as unknown, never as a limit. `context_inventory.py` implements the
project-local rules below.

## Codex

- Per directory from the project root (usually the Git root) down to the
  working directory, at most one file: `AGENTS.override.md`, else `AGENTS.md`,
  else the first name in `project_doc_fallback_filenames`. Files are joined
  root first, so closer files appear later and win.
- Global: `AGENTS.override.md` or `AGENTS.md` in `CODEX_HOME` (default
  `~/.codex`).
- Limit: `project_doc_max_bytes`, default 32 KiB; files past the limit are not
  added. `project_root_markers` changes root detection; its default is
  `UNVERIFIED` (the probe assumes `.git`).
- Imports: none documented.
- Readback: no command that prints the loaded instructions is documented
  (`UNVERIFIED`); a model asked to list its sources is not a deterministic
  readback. Use `codex_context.py` for the file chain.
- Sources: <https://developers.openai.com/codex/guides/agents-md>,
  <https://developers.openai.com/codex/config-reference>.

## Claude Code

- Project: `CLAUDE.md` or `.claude/CLAUDE.md`, and `CLAUDE.local.md` (personal,
  gitignored), in the working directory and every directory above it, joined
  root first; subdirectory files load when Claude works there.
- Rules: `.claude/rules/**/*.md`. A rule without `paths:` frontmatter loads at
  start; with `paths:` it loads only for matching files.
- `AGENTS.md`: read directly (v2.1.277 or later) only when no `CLAUDE.md`,
  `.claude/CLAUDE.md` or `CLAUDE.local.md` exists in the working directory or
  above. Adding any of them stops that unless the user-level setting
  `claude-md-and-agents-md` is chosen. A `CLAUDE.md` with `@AGENTS.md` works on
  every version and never reads `AGENTS.md` twice.
- Imports: `@path`, relative to the importing file, up to four hops; imported
  files inherit the importing file's start-up or on-demand scope. With
  `--include-global`, the probe also expands imports from the user-level
  `~/.claude/CLAUDE.md`. Not expanded inside code spans or blocks.
- Limits: guidance of under 200 lines per `CLAUDE.md`; the probe applies it to
  directly discovered `CLAUDE.md` files, not imported files, `AGENTS.md` fallbacks
  or `.claude/rules/*.md` rules. A file over 4 MiB is skipped.
- Readback: `/context` (Memory files) and `/memory` in a fresh interactive
  session; the `InstructionsLoaded` hook logs loads (not for `AGENTS.md` read
  through the setting). `/doctor prompt-audit` (v2.1.283 or later) is a native
  report of stale or conflicting instructions. No non-interactive command is
  documented.
- Source: <https://code.claude.com/docs/en/memory>.

## Gemini CLI

- `~/.gemini/GEMINI.md`, then `GEMINI.md` in the workspace directories and
  their parents, then files found when a tool reads a directory. All are joined.
- `context.fileName` in `settings.json` sets one name or a list, for example
  `["AGENTS.md", "GEMINI.md"]`. The probe reads only project
  `.gemini/settings.json`.
- Imports: `@path`, default depth 5, circular imports blocked. With
  `--include-global`, the probe also expands imports from the user-level
  `~/.gemini/GEMINI.md`, using the same size, duplicate and goal-pointer checks.
- Limit: none documented.
- Readback: `/memory show` prints the combined memory.
- Sources: <https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/gemini-md.md>,
  <https://github.com/google-gemini/gemini-cli/blob/main/docs/reference/memport.md>.

## Cursor

- Project rules: `.cursor/rules`, `.mdc` files only (a plain `.md` there is
  ignored), with `description`, `globs` and `alwaysApply` frontmatter.
  `alwaysApply: true` applies to every request; the others attach by file
  match, agent choice or manual mention.
- `AGENTS.md` in the root and subdirectories; nested files combine with their
  parents and the more specific one wins.
- `.cursorrules`: not mentioned in the current docs (`UNVERIFIED`); the probe
  reports it as legacy.
- Limit: guidance to keep each rule under 500 lines.
- Readback: none documented.
- Sources: <https://cursor.com/docs/context/rules>,
  <https://cursor.com/docs/cli/using>.

## GitHub Copilot

- `.github/copilot-instructions.md` (repository-wide) and
  `.github/instructions/**/*.instructions.md` (path-specific, `applyTo`).
- Agent files: `AGENTS.md` (nearest wins) and a root `CLAUDE.md` or `GEMINI.md`.
- Support differs by surface: the cloud agent, the CLI and code review on
  GitHub.com read all three kinds; VS Code chat reads `AGENTS.md` but not
  `CLAUDE.md` or `GEMINI.md`; Copilot Chat on GitHub.com and code review in VS
  Code and Visual Studio read only `copilot-instructions.md`.
- Limit: none documented; a character limit for code review is `UNVERIFIED`.
- Readback: none documented.
- Sources: <https://docs.github.com/en/copilot/reference/custom-instructions-support>,
  <https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions>,
  <https://code.visualstudio.com/docs/copilot/customization/custom-instructions>.

## OpenCode

- Project: the first `AGENTS.md` found walking up from the working directory;
  a `CLAUDE.md` only when no `AGENTS.md` exists. Global:
  `~/.config/opencode/AGENTS.md`, else `~/.claude/CLAUDE.md`.
- `instructions` in the project `opencode.json`: extra paths, globs or URLs, all
  added. Config files may be JSON or JSONC (JSON with comments). The docs name
  `opencode.jsonc` for managed settings; a project `opencode.jsonc` is
  `UNVERIFIED`, and the probe reads it too. The probe resolves local paths and
  globs and never fetches URLs. Source: <https://opencode.ai/docs/config/>.
- Limit: none documented. Readback: none documented.
- Source: <https://opencode.ai/docs/rules>.

## Other clients

The `AGENTS.md` format page lists further clients that read `AGENTS.md`
(<https://agents.md>). Treat any client not covered above as `UNVERIFIED` until
its own documentation is checked.
