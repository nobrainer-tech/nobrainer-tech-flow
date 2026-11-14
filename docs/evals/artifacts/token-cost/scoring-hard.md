# Token cost on hard tasks: scoring (frozen before the first run)

Question: on tasks where an agent can say "done" too early, does Flow lower what a Claude Code
user spends to reach a verified fix, once rework is counted?

## Tasks

Five tasks in `run_hard.py` (H1 refunds with float totals and a report line; H2 comma and
semicolon supplier files with both decimal conventions; H3 a weekend discount in
Europe/Warsaw time across DST, with report and invoices agreeing; H4 line-by-line shipping
with a state rule for cancel; H5 idempotent payment retries). Every hidden check in
`hidden/hidden_h1.py` to `hidden_h5.py` follows from a sentence of the prompt. Before any run,
each hidden check failed on the base fixture and passed on the reference solution in
`ref-hard/` (checked by MAIN, with the visible suite).

## Arms and runs

PLAIN and FLOW exactly as in `scoring.md` (FLOW: the skills of `6330c3b` and
`adapters/bootstrap.md` as `CLAUDE.md`). Three runs per task and arm (30 runs), interleaved, two
at a time. When the hidden check fails, the same session is resumed with the retry message of
`tasks.md`, at most twice. Every turn's cost counts.

## Measures

- **PF**: hidden check passes after the last turn. **P1**: passes after the first turn.
- **Retries**: retry turns used. **C**: `total_cost_usd` summed over all turns.
- Cost per verified fix = sum of C over an arm's runs / its PF passes.
- `score.py RUNS plain,flow --tasks H1,H2,H3,H4,H5 --repeats 3` refuses a verdict until all
  30 runs are valid with cost telemetry; a missing or invalid run is rerun.

## Primary result

RATIO = FLOW cost per verified fix / PLAIN cost per verified fix.

- `FLOW_SAVES`: RATIO <= 0.90 and FLOW PF >= PLAIN PF.
- `EVEN`: 0.90 < RATIO < 1.10.
- `FLOW_COSTS_MORE`: RATIO >= 1.10.
- Reported with it: P1 and PF per arm, retries per arm, cost per task.

A public sentence that Flow saves tokens needs `FLOW_SAVES`, and states the sample's size and
limits next to the number. Any other result is reported as it is.
