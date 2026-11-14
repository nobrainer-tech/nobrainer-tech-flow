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
- After review, the counter refuses a verdict unless every task, arm and repeat has a valid
  run with the client's final cost telemetry. Every reported run had both (all tables:
  nonzero cost, manipulation check passed), so no reported result changes.
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

## SLIM: Flow with a short bootstrap and short skill descriptions

Frozen in `7b540f3` before its runs: [scoring](artifacts/token-cost/scoring-slim.md),
[short descriptions](artifacts/token-cost/slim-descriptions.json) (5298 to 2106 characters),
[short bootstrap](artifacts/token-cost/slim-bootstrap.md) (220 to 51 words). Skill bodies
unchanged. Twelve SLIM runs interleaved with twelve fresh PLAIN runs.
[Per-run table](artifacts/token-cost/results-slim.tsv).

| Task | PLAIN (fresh) | SLIM | SLIM / PLAIN |
|---|---|---|---|
| T1 | 0.136 | 0.172 | 1.26 |
| T2 | 0.210 | 0.236 | 1.13 |
| T3 | 0.128 | 0.176 | 1.38 |
| T4 | 0.188 | 0.239 | 1.27 |
| T5 | 0.220 | 0.248 | 1.13 |
| T6 | 0.162 | 0.200 | 1.24 |

RESULT: `SLIM_COSTS_MORE` (cost per verified fix 0.212 against 0.174, ratio 1.22; 12 of 12
fixed in both arms). Against the FLOW table above, SLIM is 0.95 (0.212 against 0.222).

- The short text did shrink the prompt: the first call carried 1,324 tokens more than PLAIN
  (median 34,640 against 33,317), against 2,900 more for FLOW.
- The cost barely moved because most of it is a one-off cache write at the start of each
  session: 8,629 tokens for SLIM against 5,395 for PLAIN at the first call (median), with
  1,900 fewer tokens read from a cache shared across runs. Why the shared prefix gets shorter
  is inferred, not observed: the client places the skill listing in the session-specific part
  of the prompt.
- The extra cost behaves like a fixed amount per session, not a share of the work: SLIM minus
  PLAIN is 0.026 to 0.050 per task (mean 0.038), FLOW minus PLAIN 0.024 to 0.101 (mean 0.053),
  whatever the task's own cost. On tasks of 20 to 50 seconds that is 13 to 38 percent; a long
  session would carry the same amount once.
- Routing with the short descriptions was not tested, so SLIM is not a release candidate.

## Hard tasks with rework

Frozen in `56b34ea` before any run: [scoring](artifacts/token-cost/scoring-hard.md),
[tasks](artifacts/token-cost/tasks-hard.md), [runner](artifacts/token-cost/run_hard.py),
[reference solutions](artifacts/token-cost/ref-hard/). Five tasks whose hidden checks follow
from prompt sentences (float refund totals, two decimal conventions, a weekend discount in
Warsaw time across DST, line-by-line shipping, idempotent payment retries); each check failed
on the base fixture and passed on the reference solution before the runs. Three runs per task
and arm, up to two resumed retry turns, every turn's cost counted.
[Per-run table](artifacts/token-cost/results-hard.tsv).

| Task | PLAIN mean cost | FLOW mean cost | FLOW / PLAIN |
|---|---|---|---|
| H1 refunds | 0.267 | 0.268 | 1.00 |
| H2 supplier formats | 0.277 | 0.274 | 0.99 |
| H3 weekend discount | 0.270 | 0.346 | 1.28 |
| H4 line shipping | 0.203 | 0.256 | 1.26 |
| H5 payment retries | 0.302 | 0.427 | 1.42 |

| Arm | Passed on turn 1 | Passed in the end | Retry turns | Cost per fix |
|---|---|---|---|---|
| PLAIN | 14 of 15 | 15 of 15 | 1 | 0.264 |
| FLOW | 13 of 15 | 15 of 15 | 2 | 0.314 |

RESULT: `FLOW_COSTS_MORE` (ratio 1.192).

- All three first-turn failures were in H5, and all three for the same case: paying a
  cancelled order without a `payment_id`. The prompt is ambiguous there: "paying a cancelled
  order must raise" sits next to "calls without payment_id keep today's behaviour", and today
  that call succeeds. One PLAIN run named it as an open decision. This is a defect of the task,
  not evidence about either arm. Without H5 the ratio is 1.125, still `FLOW_COSTS_MORE`, with
  12 of 12 first-turn passes in both arms.
- No task showed Flow preventing rework: plain Claude Code (Opus 5.5, medium) already tested
  its own changes and passed every unambiguous task on the first turn.
- The extra cost is again close to a fixed amount per run: 0.050 on average (FLOW total 4.712
  against 3.955 over 15 runs), the same order as on the short tasks.

## Consequence

No public sentence may say that Flow, the five lines or the short text save tokens. What the
numbers support: Flow adds a roughly fixed list-price amount per session (about 0.04 to 0.05
here, once per session), and on these tasks it bought no extra verified fixes because plain
Claude Code fixed all of them. On five harder tasks with rework counted, the same held: Flow
cost 1.19 times plain (1.13 without the ambiguous task) and prevented no retry. Flow's case
does not rest on tokens; on single-session, well-specified coding tasks it is a cost of about
0.05 per session at list price.
