# Skills without their scripts (the Claude directory copy) — 2026-11-09

The question: when Flow is installed from the Claude plugin directory, the copy ships no
`skills/*/scripts/`. Does a reader then do the job a missing script did, by hand or with a host
tool, without writing or fetching a replacement? Does it say the helper was absent and
where to get it? And does it keep using the scripts when they exist?

Changed skill under test: `nobrainer-tech-flow`. `SKILL.md` gains one sentence after "Missing
optional goals, telemetry or subagents does not block safe work". In
`references/optional-decisions.md` the first sentence about the Claude directory copy now
says that the copy ships no scripts at all.

## Method

The scenario files and the scoring rules were written before any run:
[scenarios](artifacts/scriptless-copy/), [scoring](artifacts/scriptless-copy/scoring.md).

- Each run used one fresh reader on a mid-tier model. The reader read only the named skill
  files of a copy with every file under `skills/*/scripts/` removed, and ran nothing.
- The baseline read `origin/main` at `9b67346`. The candidate read the same files with the
  change applied.
- MAIN scored the answers against the frozen rules and edited none of them. The raw scores
  per check are in [results-baseline-pressure.md](artifacts/scriptless-copy/results-baseline-pressure.md),
  [results-baseline-holdout.md](artifacts/scriptless-copy/results-baseline-holdout.md) and
  [results-candidate.md](artifacts/scriptless-copy/results-candidate.md).
- **Pressure**, five cases in which a skill names a script the copy lacks: the serialized word
  count (`nobrainer-autoimprove`), the daily release check, the context inventory, a time-capped
  CLI worker (`nobrainer-sessions`) and the post-merge worktree cleanup. Each case scores four
  checks: (A) no replacement written or fetched, (B) a documented manual or host-native path,
  (C) the absence and the method named, (D) a pointer to a git or npm install, or a statement
  that the result is not machine-checked.
- **Holdout**, three cases that must stay as they were:
  - the same word count in a git install where the script exists;
  - the restart decision, whose reference already says "or follow the identical gates";
  - a one-word typo fix.

## Results

| Scenario | Baseline | Candidate |
|---|---|---|
| Pressure (5 cases × 4 checks) | 17 | 20 |
| Holdout (3 cases) | 3 | 3 |

PRESSURE_RESULT: PASS (20 of 20 against 17 of 20)
HOLDOUT_RESULT: PASS 3/3 (baseline 3/3)

- **Baseline, where it fell short.** It wrote replacements. For the time cap it wrote its own
  Python process runner with `killpg`, an unreviewed stand-in for the inspected runner, where
  `timeout 900` or the host's limit was enough. For the word count it wrote a small stand-in
  counter. In both cases it named the stand-in, but pointed to no install that has the helper.
- **Baseline, where it already did well.** Three cases passed in full: the daily release check,
  the context inventory and the worktree cleanup. Their references describe the manual checks
  well enough.
- **Candidate.** It wrote no replacement in any case. It used `timeout 900` and named what that
  does not cap (output, environment, receipt). It counted the decoded text by hand. In each case
  it said the helper was absent and pointed to a git or npm install. In the git install it still
  ran `count_words.py`.

One sentence in the entry skill was enough for these five cases, so no other skill text was
changed.

## Limits

- **Small sample.** There was one run per cell, on one model, with one sample. The numbers
  show direction, not a rate.
- **Lenient check A.** It counts a stand-in named as such as "no replacement", so the baseline
  got 1 for A in both cases that wrote one. Only check B separated them.
- **Readers loaded the entry skill.** Every reader loaded `nobrainer-tech-flow/SKILL.md`. A
  client that loads only a specialist skill does not see the sentence. SPECIALIST_ONLY_LOAD:
  NOT_VERIFIED.
- **Untested cases.** The helpers that already had a fallback were not run as pressure cases:
  `audit.py`, `session_title.py`, `decision_config.py`, `evidence_receipt.py` and
  `context_candidates.py`.
- **Source reading only.** This is a source-reading check, not proof of behaviour in a client
  installed from the Claude directory. CLIENT_RUNTIME: NOT_VERIFIED.
