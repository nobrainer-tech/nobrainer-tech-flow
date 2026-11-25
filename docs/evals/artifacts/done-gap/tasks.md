# Done gap: tasks (frozen before the first agent run)

The earlier evals ([token cost](../../token-cost-2026-11-14.md)) used eleven well-specified
tasks; plain Claude Code passed all of them, so they could not show whether Flow catches a
false "done". These ten tasks are built around the ways an agent says "done" too early, as
Anthropic describes them (verification, second callers, project rules, long specs,
backward compatibility, flaky tests). Each hidden check follows from a sentence of the prompt
or of a file in the repository the agent works in.

Base: `make_base.py` writes the `shop` fixture of the token-cost eval with its six planted
defects already fixed and its visible suite green. Each task adds `tasks/<ID>/overlay/` on top.
The prompt in `tasks/<ID>/prompt.txt` is the user's whole message, the same for every arm
(FLOW_ASK prefixes one sentence, see `scoring.md`).

| ID | Failure class | Prompt (short form; exact text in `prompt.txt`) | What the hidden check holds the agent to |
|---|---|---|---|
| D1 | Second caller | Raise the mid-tier discount (500 up to 1000) from 5% to 6%. Update the shop. | `pricing`, the report and the text invoice all give 6%; the boundaries 499.99, 500, 999.99 and 1000 are unchanged otherwise. |
| D2 | Project rule | Add `--top N` to `shop report`. | Behaviour, plus the rules in `CONTRIBUTING.md`: README `## CLI` section, a `## Unreleased` line in `CHANGELOG.md`, a subprocess test in `tests/test_cli.py`. |
| D3 | Data variety | Report per currency; files without the column are PLN; codes in any case; empty cell is PLN; every file in `data/` and `data/archive/` must still report. | Per-currency totals on every data file, ordering PLN first, mixed-case and empty codes. |
| D4 | Long spec | Implement `docs/specs/returns.md`. | Every acceptance criterion AC01-AC08 of the spec. |
| D5 | Rendered output and untrusted input | `shop invoice ID --html` with name, total, discount, amount to pay; same amounts as the text invoice; names can contain any characters. | HTML escapes `<`, `&`, quotes; keeps Polish letters; amounts equal the text invoice. |
| D6 | Idempotency and partial failure | `shop migrate data/store` to schema v2 (`docs/schema.md`); safe to rerun; a broken file is reported and left untouched while the rest migrate. | Two runs give the same files; v2 fields per the schema; the broken file is byte-identical and named on stderr. |
| D7 | Real entry point | Cancelled orders must not count in the totals report. | `report.summarize` and `python3 -m shop report` (which streams through another module) both exclude them. |
| D8 | Flaky test | `tests/test_couriers.py` fails about one run in five on CI. Fix the cause, not the test. | The assignment is correct under 50 hash seeds; the test file is unchanged. |
| D9 | Sweeping constraint | All money is `Decimal`, half-up to 0.01, in every public function and the CLI; no float for money in `shop/`. | Types from each public function, half-up cases, no `float` in `shop/`. |
| D10 | Rename with compatibility | Rename `Order.total` to `Order.gross`, keep `total` as a deprecated alias (read, write, constructor keyword) with a `DeprecationWarning`. | The alias works and warns; internal code raises no warning under `-W error`. |

Every hidden check also requires the visible suite to pass, so a fix that breaks other tests fails.

## Calibration (before any agent run)

`calibrate.py` must show, for every task: the hidden check fails on base + overlay, and the
visible suite plus the hidden check pass on base + overlay + `tasks/<ID>/ref/`. A task that
fails calibration is fixed or dropped before any run; it is never tuned on agent results.

## Retry turn

If the check fails after the first turn, the same session is resumed once with the retry
message of the token-cost eval (last 30 lines of the check output, then "Fix it."). Its cost
counts toward the run.
