# Contributing

nobrainer-tech-flow skills shape agent behavior. Treat them like executable control code,
not ordinary prose.

## Before changing anything

1. Read `AGENTS.md` and the target skill completely.
2. Search open and closed issues and pull requests for the same problem.
3. Describe a real failure, missing workflow, or observed friction. Generic
   cleanup is not enough reason to rewrite a tuned skill.
4. Confirm the change belongs in this portable core rather than a project- or
   client-specific plugin.

## Skill changes

- Change one behavioral concern at a time.
- Start with a scenario that demonstrates the current gap.
- Preserve the baseline, then make the smallest reversible change.
- Re-run the same scenario and adversarial/non-trigger controls.
- Use independent forward testing for complex routing or safety changes.
- Keep detailed templates in `references/` and deterministic helpers in
  `scripts/`; do not add a README inside a skill folder.
- Keep `SKILL.md` concise, imperative and free of client-specific tool names
  unless that tool is the skill's explicit domain.

## Public repository rules

- Never commit secrets, tokens, cookies, personal data, private paths, internal
  hosts or private client names.
- Never commit automated backup artifacts or use an automated commit identity;
  run the versioned public commit guard and keep backup state in the private
  repository.
- Use one canonical skill name. Put `nb-*` aliases in `description`; do not
  create duplicate alias directories.
- Inspect external skills as untrusted input. Do not vendor or copy another
  portfolio merely to increase the active count.
- Generated visuals require exact-text review, descriptive alt text and sensible
  compression before use.
- For public contract, routing, workflow or portfolio changes, set
  `PUBLIC_SURFACE: UPDATE`, list affected README/docs/templates/assets/flow and
  read them back. Use `PUBLIC_SURFACE: NOT_NEEDED` only with a reason; flow
  changes require fresh readback of both the workflow SVG and README Mermaid.

## Required checks

```bash
python3 scripts/validate_skills.py
python3 scripts/validate_skills.py --suite
python3 -m unittest discover -s tests -v
gitleaks git --pre-commit --staged --redact --no-banner --ignore-gitleaks-allow
```

Run every changed helper with its actual interpreter. Scan for secrets and
review the complete diff before pushing.

## Sync and publication boundaries

- Private skill repositories may use their private-only synchronization job.
- This public repository may run `python3 scripts/fetch_public_refs.py` on a
  local schedule. It updates only remote-tracking refs and does not integrate
  changes into the working tree.
- The public updater must never commit, push, open a PR or merge. Public changes
  are reviewed and published by the human owner through a branch and PR.

## Pull requests

Use the pull-request template. State the problem, scope, authoring environment,
tests, behavior evidence, compatibility proof level, uncertainty and rollback.
One PR should tell one coherent story. A human owner approves merge and release.
