# Implicit state machines in review — 2026-11-09

The question: does a reader with `nobrainer-review` find and report implicit state
machines (one state spread over flags, status strings, counters and locks) when asked,
without adding ceremony to reviews that have none?

Changed skills under test: `nobrainer-review` (`SKILL.md`: one defect class in Pass 2, the
description and the alias `nb-auto-fix`; new `references/implicit-state.md`). One routing
row, read for coherence and not behavior-tested here: `nobrainer-tech-flow`
(`references/routing.md`).

## Method

The scenario files and the scoring rules were written before any run:
[pressure sample](artifacts/implicit-state-review/pressure/),
[holdout sample](artifacts/implicit-state-review/holdout/) and
[scoring](artifacts/implicit-state-review/scoring.md). Each run was one fresh reader on a
mid-tier model that read only the skill and the sample files and ran nothing. The baseline
read `nobrainer-review` from `origin/main`; the candidate read the working tree. MAIN
scored the answers against the frozen list and edited none of them.

- **Pressure 1**, `BUG_HUNT` on two files with nine planted defects, each a state nobody
  designed. An item counts only with the triggering sequence and the wrong result.
- **Pressure 2**, the request "Find the implicit state machines in these two files and
  tell me what to fix first", four checks: names the machines with their fields; gives an
  invalid reachable state per machine as a sequence with field values; ranks by
  consequence; keeps review and fix apart, with a failing test first and one explicit
  state with a single transition function. It was added after the baseline run of
  Pressure 1 showed a one-item gap, and frozen before any other run.
- **Holdout**, three cases that must stay as they were: a pure function with one real
  off-by-one, a module that already has one explicit enum and one transition table, and a
  one-word README typo in `CLOSEOUT`.

## Results

| Scenario | Baseline | Candidate v1 | Candidate v2 |
|---|---|---|---|
| Pressure 1 (9 planted) | 8 | 8 | not rerun |
| Pressure 2 (4 checks) | 3 | 4 | 4 |
| Holdout (3 cases) | not run | 3 | 3 |

PRESSURE_RESULT: PASS (Pressure 1: 8 of 9, equal to the baseline; Pressure 2: 4 of 4 against 3 of 4)
HOLDOUT_RESULT: PASS 3/3 (v1 and v2; the reference was opened in none of the three cases)

- Pressure 1 shows no detection gain. Baseline and candidate found the same eight items
  and missed the same one: an order whose payment attempts are used up stays "new" for
  ever. The candidate reader did not open `implicit-state.md` in a plain `BUG_HUNT`.
- Pressure 2 is where the change shows. The baseline also named both machines, gave
  sequences and ranked them. It listed a regression test per finding, but did not say the
  fix starts with that test or goes to `nobrainer-build`. The candidate did both, and said
  that a change to user-visible behaviour needs the owner's approval. This is a close
  call on one check, from one run per side.
- Candidate v2 changes one thing after that diagnosis. v1 said "Load this in `BUG_HUNT`",
  which the Pressure 1 run did not do. v2 names the two conditions that hold: the request
  names state machines, or several findings share that cause.

## Limits

- One run per cell, one model, one sample. The numbers show direction, not a rate.
- The second load condition (several findings share that cause) was not exercised by a
  run. NOT_VERIFIED.
- The alias `nb-auto-fix` and the routing row were not behavior-tested: every run was
  pointed at the skill directly. ROUTING: NOT_VERIFIED.
- The fix half belongs to `nobrainer-build` and was not run here. The same method was
  applied by hand to this repository's MCP server in the same release (item state read through
  one function; two reachable invalid states fixed with tests written first).
- CLIENT_RUNTIME: NOT_VERIFIED. This is a source-reading check, not proof of behaviour in
  an installed client.
