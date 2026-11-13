# Scoring: progress updates (frozen before any run)

Written on 2026-11-12, before the baseline or the candidate ran. MAIN scores each run
from its `stream-json` transcript with `score.py`, which only counts blocks. MAIN did
not edit the transcripts.

## Runs

- Client: Claude Code CLI 2.1.322, `claude -p --output-format stream-json --verbose`,
  model `claude-opus-5-5`, effort `medium`, `--setting-sources project,local` (no user
  settings or hooks), read-only tools (`Read`, `Grep`, `Glob`, read-only `Bash`).
- Each run starts in a fresh checkout. The baseline checkout is `origin/main` at
  `b48f15c`. The candidate checkout is the same commit with this change. The client loads
  the checkout's `CLAUDE.md`, and every prompt tells the reader to read and follow
  `skills/nobrainer-tech-flow/SKILL.md`.
- Pressure: tasks P1 and P2, two runs each per side. Holdout: tasks H1 and H2, one run
  each per side.

## Measures per run

- **M1 opening:** 1 when a visible text block comes before the first tool call, else 0.
- **M2 longest silence:** the largest number of tool calls in a row with no visible text
  between them.
- **M3 output tokens:** `usage.output_tokens` of the result event.
- **M4 visible words:** all visible text, in words.
- **Answer:** the final text answers the task (MAIN checks it against the repository).

## Pass rules

- **Pressure:** the candidate has M1 = 1 in all four runs; the candidate's median M2 is at
  most half the baseline's median M2, or at most 4; the candidate's mean M3 is at most
  1.4 times the baseline's; every candidate answer is correct.
- **Holdout (short questions):** every candidate answer is correct, and its M4 is at most
  1.5 times the baseline's M4 plus 20 words.
