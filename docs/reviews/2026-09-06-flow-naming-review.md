# NoBrainer.Tech Flow naming review

## Decision

Maintained user-facing language uses **NoBrainer.Tech Flow**. Public repository
links and new checkout or package channel references use `nobrainer-tech-flow`.
The technical skill remains `nobrainer-ultra`; `$nobrainer-ultra` is shown only
when a technical entrypoint or path is relevant. `nb-ultra`, `nb-flow` and
`nb-workflow` remain compatibility aliases. The private `nb-workflow` skill is a
separate older skill and was not merged.

The existing package/plugin ID `nobrainer-tech-skills`, its directory names,
frontmatter, installer targets and client module paths remain unchanged. A
separate compatibility migration is required before changing those identities.

## Scope and proof

The source checkout was dirty before this task. A complete backup was created at
`/Volumes/1TB/MacMini/Backups/nobrainer-tech-skills/naming-before-20260906`.
The backup includes the original status, HEAD and binary diff. The earlier
session-care and RCA edits were preserved.

Changed maintained surfaces: `AGENTS.md`, `CLAUDE.md`, `README.md`,
`RELEASE-NOTES.md`, `package.json`, plugin and marketplace descriptions/default
prompt, `adapters/bootstrap.md`, the workflow SVG, `.opencode/INSTALL.md`,
Copilot instructions, `docs/COMPATIBILITY.md`, `docs/INSTALL.md`,
`docs/MIGRATION_TO_FLOW.md`, `docs/SESSION_RESTART.md`, `docs/NAMING.md`,
the technical routing headings, current task lessons/status and the naming
contract tests.

The 22-file maintained public set measured 112,924 characters / 2,296 lines
before the naming patch and 116,164 characters / 2,339 lines after it:
`+3,240` characters and `+43` lines. The new naming map accounts for 2,168
characters; the remainder is wording, test coverage and the existing dirty
session-care overlap. Within that set, old product-brand matches fell from 30 to
0, exact `NoBrainer.Tech Flow` matches rose from 0 to 49, and public
`nobrainer-tech-flow` channel matches rose from 20 to 24.

Checks completed:

- `python3 scripts/validate_skills.py --suite` passed.
- `test_adapters.py` passed 6 tests.
- `test_suite.py` passed 71 tests.
- Full `python3 -m unittest discover -s tests -q` passed 163 tests.
- JSON manifests and workflow SVG parsed successfully.
- `git diff --check` passed.
- Changed-source secret scan found no leaks.
- `AGENTS.md` and `CLAUDE.md` are byte-identical.

No commit, push, publish, deploy, installer run or derived-index edit was made.

## Remaining occurrences and classification

The post-change inventory scanned all text files while excluding `.git`, Python
bytecode, test caches and review-report files. It found 78 exact public-brand
matches, 36 public channel matches, 111 compatibility-alias matches, 281
technical `nobrainer-ultra` matches and 82 legacy `nobrainer-tech-skills` matches.

The remaining old-form matches are intentional:

- `plugin.json:7` is the legal author field `NoBrainer Tech`, not the product
  name.
- `docs/specs/v1.3.0-harness-clarity.spec.md:6,7,16,156-159` is a frozen
  owner and audience specification.
- `docs/releases/v1.7.1.md:1,7` and
  `docs/releases/v1.7.1-publication-readback.md:3,10,49` preserve published
  v1.7.1 provenance.
- `docs/releases/v1.0.0.md`, `v1.1.0.md`, `v1.2.0.md` and `v1.2.1.md` preserve
  the former `NoBrainer Tech Skills` release identity.
- `docs/evals/artifacts/**` contains frozen prompts, policies, cases and
  receipts whose old `NoBrainer Ultra` or `NoBrainer Tech Skills` text is part
  of the evaluated input and must not be rewritten.
- `tests/test_suite.py:3448-3449` retains the old strings as negative assertions
  that maintained public copy does not regress.

Technical aliases remain only in the compatibility contract, tests, installer
maps, validator maps, technical skill descriptions, session protocol and the
explicit alias-control examples in `README.md`, `docs/COMPATIBILITY.md`,
`docs/INSTALL.md`, `docs/MIGRATION_TO_FLOW.md`, `docs/NAMING.md` and
`adapters/bootstrap.md`. They are not used as the product name.

Technical `nobrainer-ultra` remains in its frontmatter, directory, relative
links, installer and validator maps, adapter tests, runtime compatibility
examples, routing references and other skill-to-skill references. Legacy
`nobrainer-tech-skills` remains in package/plugin names, lockfile, module paths,
installer/readback tests and historical evidence. The public repository URL is
`https://github.com/nobrainer-tech/nobrainer-tech-flow`.

## Consumer propagation plan

After this source is approved, use the reviewed sync workflow to inventory the
83 repository `AGENTS.md` files and 3 `CLAUDE.md` files. Classify each match,
preview only maintained public-text changes, preserve local rules and managed
blocks, read back dirty state per repository, then apply through canonical sync.
Run each consumer's nearest validator and stop on a conflict or owner gate.
Do not hand-edit `~/.codex/skills`, `~/.agents/skills`, `~/.claude/skills` or
plugin cache. This task intentionally did not propagate to those locations.

Rollback is the backup directory above or a scoped revert of this task's files;
unrelated dirty work and the preserved technical identities remain untouched.
