# NoBrainer.Tech Flow repository instructions for Copilot

The sixteen canonical Agent Skills are under `skills/`. Read the relevant
`skills/<name>/SKILL.md` before changing a skill; retired predecessors exist
only in Git history.

For non-trivial delivery load `nobrainer-ultra`. Inspect current state, clarify
once only when the answer changes scope or safety, freeze the minimum change and
show a compact Progress checklist. Keep one-step work direct. Use a detailed
ledger only for multi-session, dependency-rich, consequential or explicitly
resumable work.

Default to one primary agent. Use `nobrainer-team` for justified roles,
`nobrainer-dispatcher` for an approved delegated queue and
`nobrainer-sessions` for exact identity and transport. Worker reports require
fresh receive-audit before state advances.

`PROBLEM_GATE`: begin with the literal failure, local evidence and smallest
reproducer. Query related wiki decisions when useful. Use current internet
research only when the remedy depends on an external, current, niche, uncertain
or high-stakes fact. If required research is unavailable, return
`RESEARCH_BLOCKED` and choose no remedy that depends on it.

Keep `SKILL.md` portable: line-1 YAML frontmatter with only `name` and
`description`, directory/name match, relative links, no secrets, private paths,
private client data, hardcoded drifting model versions or unsafe shell
placeholders. Run `python3 scripts/validate_skills.py --suite` and relevant tests
before reporting success.

Use `nobrainer-build` for implementation, `nobrainer-security` for material
trust boundaries and `nobrainer-review` for a justified final evidence gate.
