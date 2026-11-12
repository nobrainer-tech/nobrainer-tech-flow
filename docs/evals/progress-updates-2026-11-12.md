# Progress updates during a run — 2026-11-12

The question: the communication rule told agents to "run tools without announcing them" and
to speak mid-run only at a transition, a blocker, a safety gate or new evidence. In Claude Code
that gave long stretches of tool calls with no word to the user; in one long coordinator session
the client injected its "The user hasn't heard from you in a while" reminder dozens of times.
Anthropic's prompting guide for Claude Fable 5.2 recommends the opposite: one line before the
first tool call, short updates while working, and a recap that stands on its own. Does that
wording close the gap without making answers to short questions longer?

Changed text:

- `CLAUDE.md` and `AGENTS.md` (still byte-identical): "Before the first tool call, say in one
  line what you will do; on longer runs, update in one line every few calls. Never repeat the
  plan or unchanged state. Close with a self-contained recap: outcome, decisive proof, remaining
  risk and next action." It replaces the "run tools without announcing them" and "Speak mid-run
  only for ..." sentences and keeps the file within its 205-line and 1620-word test limits.
- `skills/nobrainer-tech-flow/SKILL.md`: "Before the first tool call, say in one line what you
  are about to do; on longer runs give a one-line update every few tool calls." It replaces "Run
  tools without announcing the next command when the host permits; otherwise emit its shortest
  useful scope or evidence sentence." The entry skill grows from 2202 to 2208 words.

## Method

The tasks, the measures and the pass rules were written before any run:
[tasks](artifacts/progress-updates/tasks.md), [scoring](artifacts/progress-updates/scoring.md),
[counter](artifacts/progress-updates/score.py).

- Real client runs, not source reading: Claude Code CLI 2.1.322 in print mode with the
  `stream-json` transcript, model `claude-opus-5-5` at effort `medium`, project settings only
  (no user settings or hooks), read-only tools. Each run used a fresh copy of the checkout.
- The baseline copy was `origin/main` at `b48f15c`; the candidate copy was the same commit with
  this change. The client loaded the copy's `CLAUDE.md`, and every prompt told the reader to
  read and follow the entry skill.
- **Pressure:** two multi-step audits (broken relative links in skill files; skill names in
  `README.md` and `docs/COMPATIBILITY.md` against `skills/`), two runs each per side.
- **Holdout:** two short questions (the portfolio size in one line; what `--suite` checks in two
  sentences), one run each per side.
- MAIN checked each answer against the repository. All twelve answers were correct.

## Results

| Run | M1 opening | M2 longest silence | M3 output tokens | Tool calls |
|---|---|---|---|---|
| Baseline P1 #1 | 0 | 6 | 5144 | 7 |
| Baseline P1 #2 | 0 | 5 | 3589 | 5 |
| Baseline P2 #1 | 0 | 7 | 3129 | 7 |
| Baseline P2 #2 | 0 | 3 | 1895 | 3 |
| Candidate P1 #1 | 1 | 2 | 7423 | 10 |
| Candidate P1 #2 | 1 | 2 | 4878 | 7 |
| Candidate P2 #1 | 1 | 3 | 3154 | 7 |
| Candidate P2 #2 | 1 | 5 | 3714 | 8 |

| Holdout | Baseline words | Candidate words | Limit |
|---|---|---|---|
| H1 portfolio size | 17 | 31 | 45 |
| H2 `--suite` | 124 | 130 | 206 |

PRESSURE_RESULT: PASS (opening line 4 of 4 against 0 of 4; median longest silence 2.5 against
5.5; mean output tokens 4792 against 3439, 1.39 times, limit 1.4)
HOLDOUT_RESULT: PASS 2/2 (answers correct; words within the limit)

- **Baseline.** No run said anything before its first tool call. In three of four runs the first
  visible text came after five or more tool calls.
- **Candidate.** Every run opened with one line of intent. Updates named what changed the plan
  (a refused shell command, a switch from a script to Grep) rather than restating it. The
  longest silence was five tool calls, in one run.
- **Cost.** Output tokens rose 39%, close to the limit. Part of that is more work, not more
  words: the candidate made 8 tool calls per run on average against 5.5. Anthropic's guide gives
  about +20% for the same wording. The final answers kept the evidence-first shape.

## Limits

- **Small sample.** One model, one effort level, two pressure tasks, two runs per cell. The
  numbers show direction, not a rate.
- **Print mode.** The runs used the CLI without the desktop client's own reminder, which is what
  this change replaces in the first place. Interactive behaviour in the desktop client:
  CLIENT_RUNTIME: NOT_VERIFIED.
- **Other clients.** Codex, Cursor and Gemini read the same `AGENTS.md`; they were not run.
- **Token cost.** The +39% is measured on read-only audits. Long implementation runs were not
  measured.
- **Wording measured.** The runs used a longer `CLAUDE.md` sentence with the same instructions
  (it also listed transitions, blockers, safety gates and new evidence as update points). It was
  shortened afterwards to fit the always-loaded size limit; the entry skill sentence is the one
  that was measured. The shortened file text was not re-run.
