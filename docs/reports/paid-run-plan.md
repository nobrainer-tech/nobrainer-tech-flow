# Plan for the paid measurement runs

Status: **proposed, not approved, nothing run.** The [report](flow-quality-report.md) covers Flow as software. This plan covers the part it cannot: does an agent that uses Flow finish tasks better, more reliably, faster or cheaper than the same agent without it? Nothing here is a result.

## Question and design

For a frozen set of tasks, run the same agent, model, effort and budget in two arms and compare.

| | Arm A (baseline) | Arm B (Flow) |
|---|---|---|
| Instructions | Project instructions only | Same, plus Flow installed |
| Model, effort, tool budget | Identical | Identical |
| Task set and fixtures | Frozen, identical | Frozen, identical |

Rules taken from [TESTING.md](../TESTING.md): keep development cases separate from final holdout cases; self-test the judge with known-good and known-bad controls, plus a deceptive control when the metric can be gamed, before scoring; keep the rubric and score path outside anything the agent can write; at least three paired runs for a borderline promotion claim; record null results; no tuning against a failed holdout. This plan adds one rule of its own: failed trials are kept in the report.

**Task set (12):** four small bug fixes with hidden tests, four multi-file changes with written acceptance criteria, four traps (ambiguous scope, a misleading green test, a request that should be refused or paused). Three of the twelve are sealed as the holdout. Fixtures are synthetic and public-clean.

## Metrics

| Metric | How it is computed from a run |
|---|---|
| Quality | Hidden tests passed, independent rubric score, and false-completion rate (claimed done while a required proof was missing or failing) |
| Reliability | Share of tasks passed in all three repetitions, plus the spread across repetitions |
| Speed | Wall time to the accepted result, and turn count |
| Cost | Input, cached input and output tokens from the host's usage receipt, converted at the price list on the day of the run |

## Volume and token envelope

72 agent runs (12 tasks x 2 arms x 3 repetitions), 72 judge calls and about 12 calibration calls (84 judge-side calls).

The token receipts the report cites under [Cost](flow-quality-report.md#cost) are all single small runs: one local repair with tools reported 64,216 input tokens (48,128 cached, 75%) and 1,133 output tokens ([v1.6.1 receipt](../evals/artifacts/v1.6.1/runtime/receipt.json)), and four smoke trials reported 70,987 to 111,655 input and 441 to 902 output tokens ([v1.6.0 receipts](../evals/artifacts/v1.6.0/smoke-receipts.json)). They do not establish usage for the medium and large tasks proposed here. Every size below is an **assumption** for budgeting, except that the small input figure is rounded from the 64,216 receipt. The pilot replaces the assumptions with measurements.

Size classes are assigned to the 12 tasks when the task set is frozen: four small, four medium, four large.

| Item | Runs | Input tokens per run (assumed unless noted) | Output tokens per run (assumed) |
|---|---|---|---|
| Small task | 24 | 65,000 (rounded from one receipt) | 6,000 |
| Medium task | 24 | 400,000 | 30,000 |
| Large task | 24 | 1,200,000 | 80,000 |
| Judge and calibration calls | 84 | 30,000 | 2,000 |

Totals: about **42.5 million input tokens** and **2.95 million output tokens** (24 x 65,000 + 24 x 400,000 + 24 x 1,200,000 + 84 x 30,000 input; 24 x 6,000 + 24 x 30,000 + 24 x 80,000 + 84 x 2,000 output). Roughly three quarters of the input may be cached if the host behaves as in the v1.6.1 receipt; the four v1.6.0 smoke receipts show 73 to 81 percent and the v1.6.0 holdout verdict ([verdict](../evals/artifacts/v1.6.0/holdout/verdict.json)) shows none cached for its single run, so the cached share varies between runs and is unmeasured at this scale. The dollar figure is those totals times the current price of the chosen model, so it is **not stated here**: it needs the model choice and a live price list, and a made-up price would be worse than none. On a flat-rate plan the limit is quota rather than a per-token bill; the token totals still apply.

## Phases and stop rules

1. **Pilot, 6 of the 72 agent runs (about 8% by count; the token share depends on which tasks):** 3 tasks, both arms, 1 repetition, plus the judge controls. Replace the assumed token sizes with measured ones and re-state the envelope. Stop if the judge fails its known-bad or deceptive control.
2. **Full run:** only after the owner approves the re-stated envelope. Hard cap at 1.25 times the approved tokens; stop and report rather than continue past it.
3. **Report:** per-metric result with the spread, failed trials kept, holdout result separate. A null or negative result is published as such.

## Decisions needed from the owner

- Approve the budget, expressed in tokens or in currency after the pilot.
- Pick the model and effort the two arms use.
- Say whether the sealed holdout may be run once, after the development set is final.
