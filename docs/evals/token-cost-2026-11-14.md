# Token cost of Flow against plain Claude Code — 2026-11-14

The question: does installing Flow change what a Claude Code user spends to reach a verified
fix? Tools such as Caveman publish token savings; Flow had never been measured against the
same client without it. The answer decides whether any public sentence about cost is true.

## Method

The tasks, the measures and the decision rule were committed before any run, in `3c3b554`:
[tasks](artifacts/token-cost/tasks.md), [scoring](artifacts/token-cost/scoring.md),
[fixture generator](artifacts/token-cost/make_fixture.py),
[hidden checks](artifacts/token-cost/hidden/), [runner](artifacts/token-cost/run.py),
[counter](artifacts/token-cost/score.py).

- Six coding tasks on a small Python package with planted defects: paging, a failed import
  with a 2470-line log, a new CLI option, an order that is both cancelled and shipped, a
  report that disagrees with the pricing module, and a red test suite. The visible suite
  prints about 98 KB per run. Each task has a hidden acceptance test the agent never sees.
- **PLAIN**: the fixture alone. **FLOW**: the same fixture with the 18 skills of `6330c3b`
  under `.claude/skills/` and `adapters/bootstrap.md` as `CLAUDE.md`, as a project install
  places them.
- Claude Code CLI 2.1.325 in print mode, `claude-opus-5-5` at effort `medium`, no user
  settings, skills, hooks or MCP servers, web tools disallowed. A fresh copy per run; two runs
  per task and arm. A failed hidden check would get one resumed retry turn, counted in the cost.
- Cost is the client's `total_cost_usd`, a list-price estimate. Subscription users pay a plan;
  this measures how much of it a task uses, not a bill.
- Manipulation check: every FLOW run listed `nobrainer-tech-flow` among its skills, and no PLAIN
  run did.

## Results

All 24 runs passed their hidden check on the first turn, so no retry turn ran.

| Task | PLAIN mean cost | FLOW mean cost | FLOW / PLAIN |
|---|---|---|---|
| T1 paging | 0.140 | 0.182 | 1.30 |
| T2 import log | 0.226 | 0.250 | 1.11 |
| T3 CLI option | 0.147 | 0.183 | 1.25 |
| T4 cancelled and shipped | 0.158 | 0.259 | 1.64 |
| T5 report vs pricing | 0.171 | 0.250 | 1.46 |
| T6 red suite | 0.177 | 0.210 | 1.19 |

| Arm | Verified fixes | Cost | Cost per fix | Cache write | Cache read | Output |
|---|---|---|---|---|---|---|
| PLAIN | 12 of 12 | 2.037 | 0.170 | 131,303 | 2,501,689 | 24,304 |
| FLOW | 12 of 12 | 2.668 | 0.222 | 200,003 | 2,922,549 | 24,137 |

RESULT: `FLOW_COSTS_MORE` (cost per verified fix 1.31 times PLAIN; every task costs more).

As frozen, the result read `EVEN` (ratio 0.934): four PLAIN runs (T2 to T5, second repeat)
waited 15 minutes for the client to start, and those four wrote about 36,000 cache tokens each
instead of about 10,000, which doubled their cost. The stall was in the client or service, not
in the work: each of those runs took 22 to 45 seconds once started, and four parallel trivial
runs started in 5 to 7 seconds afterwards. The four runs were rerun cleanly; the table above uses
the reruns. Both tables are kept: [as frozen](artifacts/token-cost/results-as-frozen.tsv),
[with the reruns](artifacts/token-cost/results-clean-rerun.tsv).

Where the extra cost comes from:

- **Always-loaded text.** The FLOW prompt was 36,182 tokens at the first call against 33,310
  (median), from the bootstrap and the 18 skill descriptions. It is written to the cache once
  per session and read on every turn: cache writes rose 52% and cache reads 17%.
- **Not the workflow.** The entry skill was invoked in one FLOW run of twelve; output tokens
  were equal; median turns were 8 against 7.5. On T4 one FLOW run took 13 turns against 5 to 7.
- **No rework to save.** Both arms fixed every task on the first turn. Flow's done gate has
  nothing to prevent on tasks this small, so this sample cannot show its benefit.

## Limits

- Small sample: six short tasks (20 to 50 seconds each), two runs per cell, one model and one
  effort. The fixed overhead weighs more on short tasks than in a long session.
- Print mode only; the desktop client and other clients were not run.
- Harness changes after the first wave, before the reported runs: two runs at a time instead
  of four (scoring said four), and the skills copied from a tarball of `6330c3b` (sha256
  `8bcc5763…`) because `git archive` on the live checkout failed with exit 128 in eight runs.
  The measures and the decision rule did not change.
- Not measured: Caveman or another compressor, and long tasks where the agent first claims a
  fix that fails.

## LEAN: five lines in `CLAUDE.md`, no Flow install

Frozen in `1a24178` before its runs: [scoring](artifacts/token-cost/scoring-lean.md),
[the five lines](artifacts/token-cost/lean-claude-md.md) (noisy commands show failures only,
locate before reading, hand broad reading to a cheaper subagent, run the check once before
done, reply with result, proof and next step). Twelve runs, same harness, against the twelve
clean PLAIN runs above. [Per-run table](artifacts/token-cost/results-lean.tsv).

| Task | PLAIN | LEAN | LEAN / PLAIN |
|---|---|---|---|
| T1 | 0.140 | 0.147 | 1.05 |
| T2 | 0.226 | 0.176 | 0.78 |
| T3 | 0.147 | 0.147 | 1.00 |
| T4 | 0.158 | 0.149 | 0.94 |
| T5 | 0.171 | 0.174 | 1.02 |
| T6 | 0.177 | 0.168 | 0.95 |

RESULT: `EVEN` (cost per verified fix 0.160 against 0.170, ratio 0.944; 12 of 12 fixed).

- The only clear gain is T2, the 2470-line log (22% less). Elsewhere the lines change little:
  PLAIN already piped noisy output through `tail` (23 calls against 24) and read the whole
  log in 2 runs against 1. No LEAN run used a subagent, so that line was never exercised.
- The baseline PLAIN runs were recorded about an hour earlier, not interleaved with LEAN.

## Consequence

No public sentence may say that Flow, or the five lines, save tokens: Flow costs 1.31 times
plain on these tasks, and the lines are even within the frozen band. What the numbers do
show is where Flow's cost sits: the always-loaded text. Cutting it (a shorter bootstrap and
shorter skill descriptions) is the lever to measure next, in the same harness.
