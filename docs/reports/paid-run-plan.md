# Plan for the paid measurement runs

Status: **proposed, not approved, nothing run.** The [report](flow-quality-report.md) covers Flow as software. This plan covers the part it cannot: does an agent that uses Flow finish tasks better, more reliably, faster or cheaper than the same agent without it? Nothing here is a result.

## Question and design

For a frozen set of tasks, run the same agent, model, effort and budget in two arms and compare.

| | Arm A (baseline) | Arm B (Flow) |
|---|---|---|
| Instructions | Project instructions only | Same, plus Flow installed |
| Model, effort, tool budget | Identical | Identical |
| Task set and fixtures | Frozen, identical | Frozen, identical |

Rules taken from [TESTING.md](../TESTING.md): develop on one set of tasks and keep a sealed holdout; self-test the judge with known-good, known-bad and deceptive controls before scoring; keep the rubric and score path outside anything the agent can write; at least three paired repetitions per task; record failed trials; no tuning against a failed holdout.

**Task set (12):** four small bug fixes with hidden tests, four multi-file changes with written acceptance criteria, four traps (ambiguous scope, a misleading green test, a request that should be refused or paused). Three of the twelve are sealed as the holdout. Fixtures are synthetic and public-clean.

## Metrics

| Metric | How it is computed from a run |
|---|---|
| Quality | Hidden tests passed, independent rubric score, and false-completion rate (claimed done while a required proof was missing or failing) |
| Reliability | Share of tasks passed in all three repetitions, plus the spread across repetitions |
| Speed | Wall time to the accepted result, and turn count |
| Cost | Input, cached input and output tokens from the host's usage receipt, converted at the price list on the day of the run |

## Volume and token envelope

72 agent runs (12 tasks, 2 arms, 3 repetitions), 72 judge calls and about 12 calibration calls.

The only measured anchor in the repository is one small tool-using run: 64,216 cumulative input tokens, 75% of them cached ([v1.6.1 record](../releases/v1.6.1.md)). The medium and large sizes below are **assumptions** that the pilot replaces with measurements.

| Item | Runs | Input tokens per run (assumed unless noted) | Output tokens per run (assumed) |
|---|---|---|---|
| Small task | 24 | 65,000 (measured scale) | 6,000 |
| Medium task | 24 | 400,000 | 30,000 |
| Large task | 24 | 1,200,000 | 80,000 |
| Judge and calibration calls | 84 | 30,000 | 2,000 |

Totals: about **42.5 million input tokens** and **2.9 million output tokens**, of which roughly three quarters of the input may be cached if the host behaves as in the one receipt. The dollar figure is those totals times the current price of the chosen model, so it is **not stated here**: it needs the model choice and a live price list, and a made-up price would be worse than none. On a flat-rate coding plan the cost is quota, not dollars; the token totals still apply.

## Phases and stop rules

1. **Pilot, about 3% of the volume:** 3 tasks, both arms, 1 repetition, plus the judge controls. Replace the assumed token sizes with measured ones and re-state the envelope. Stop if the judge fails its known-bad or deceptive control.
2. **Full run:** only after the owner approves the re-stated envelope. Hard cap at 1.25 times the approved tokens; stop and report rather than continue past it.
3. **Report:** per-metric result with the spread, failed trials kept, holdout result separate. A null or negative result is published as such.

## Decisions needed from the owner

- Approve the budget, expressed in tokens or in currency after the pilot.
- Pick the model and effort the two arms use.
- Say whether the sealed holdout may be run once, after the development set is final.
