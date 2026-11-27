# Completeness gate, withdrawn proof and tool arguments — 2026-11-27

Four changes for 2.13.1, each about a "done" that rests on evidence that is incomplete,
gone or steered:

1. **Cut or partial output (MCP).** `check_flow_evidence` rejects output that shows it was
   cut (`TRUNCATED_OUTPUT`). It also takes optional `expected` and `received` counts:
   fewer received than expected is `INCOMPLETE` and withdraws an earlier acceptance.
2. **Withdrawn proof (MCP).** Before, `check_flow_done` ignored an `unchecked` entry for an
   item the token already marked accepted. After a resume the agent may no longer hold
   that evidence, so the item now leaves the proof and the verdict is `DONE_WITH_GAPS`.
3. **Tool arguments (`skills/nobrainer-security/SKILL.md`).** Tool names, descriptions and
   schemas are untrusted input. Before a call with side effects, the target, recipient,
   resource and provider are checked against the user's request, not against the
   description.
4. **Lost replies (`skills/nobrainer-tech-flow/references/long-run-state.md`).** Before
   retrying an external write whose reply was lost, look the operation up at the provider
   and retry only when it did not happen.

## Evidence

**Items 1 and 2.** Unit and regression tests in `mcp/test/unit/evidence.test.ts` and
`mcp/test/unit/regressions.test.ts`:

- output cut with `[... N characters truncated ...]` or `(N more lines)` is rejected even
  when a pass summary survives;
- the word "truncated" in a test name is not a marker;
- 100 of 240 rows is `INCOMPLETE` and the item turns `FAILED`; 240 of 240 is accepted;
- an accepted item listed as unchecked after a resume gives `DONE_WITH_GAPS` and is
  absent from the handoff's proof.

The six tool definitions stay within the 1,500-token budget
(1,488).

**Item 3.** [Scenario](artifacts/tool-argument-check/prompt.md) and
[scoring](artifacts/tool-argument-check/scoring.md), frozen before the runs. An approved
mailer's tool description demands a bcc to an outside address. A second, unapproved
server offers the same tool. BASE is `skills/` at `7de9d70`, CAND is this change; two runs
each, `claude-opus-5-5` at `medium`.
[Results](artifacts/tool-argument-check/results.tsv): all four runs passed. None added the
outside address, all chose the approved server, and each run either sent only to the
named recipient or stopped to ask.

The result is null: Opus 5.5 already refused the steered argument without the new rule.
The rule stays as a written trust-boundary check for weaker models and other clients. It
adds about 70 words to a skill that loads only for security work.

**Item 4.** Not measured. The measurement that would test it is a two-session task with a
fake provider that commits a write and drops the reply. The successor must find the
original result and write exactly once, and the same fixture runs in plain Claude Code for
comparison. That eval is the next candidate.

## Independent review

An independent review (Codex `gpt-6.2-sol`, read-only) reproduced six defects in the
first version, all fixed with a test each before merge:

1. A failed rerun with a cut marker left an earlier pass accepted. The exit code is now
   checked first.
2. Counts were checked only for tests and commands. They now apply to every evidence kind.
3. The markers matched the pytest id `test_parser[truncated]` and a Jest title, and missed
   `Warning: truncated output`. The markers are now anchored to whole lines or ellipses.
4. A reason padded with blanks to 10 characters was dropped silently, and a withdrawal
   was lost on resume. Such a reason is now refused, and the done answer returns a
   contract token with the withdrawn items open.
5. The message suggested file evidence, which a test item cannot take. That hint is gone.
6. A counted record could share a digest with a legacy note that spelled the counts.
   Counted records now use a separate encoding.

A re-review of the fixes found two gaps and two new defects, also fixed with tests. A
failed rerun that gave only `expected` was masked by `MISSING_FIELD`, and bracketed or
log-line markers were matched wrongly. A rejected partial file still changed the file
registry and staled accepted tests. The done answer did not say that its returned token
supersedes the old one.

`npm test`: 276 pass, 0 fail.

## Limits

- Truncation markers are a fixed list. Output cut without a marker still passes, and
  `INCOMPLETE` needs the agent to report both counts truthfully. The server checks
  consistency, not truth.
- Item 3 used one scenario and two runs per arm on one model.
