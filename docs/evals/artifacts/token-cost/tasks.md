# Token cost: tasks

Six coding tasks on the `shop` fixture (`make_fixture.py`). Each task has one planted
defect or missing feature and a hidden acceptance test (`hidden/hidden_tN.py`) that the agent
never sees. The visible suite (`python3 -m unittest discover -s tests`) is green on the base
fixture, except in T6, where `tests/test_schedule.py` is added and fails. It prints 2000 import
lines (about 98 KB), as noisy legacy suites do.

The prompt is the user's whole message. Both arms get exactly the same text.

| ID | Prompt | Hidden check |
|---|---|---|
| T1 | Customers say page 2 of the order list repeats the last order from page 1. Fix the paging in this repo. | Every page size covers each item exactly once. |
| T2 | Last night's supplier import failed. The log is logs/import-2026-11-13.log (about 2500 lines). Find the cause and fix it so the import works. | supplier-b (decimal comma) imports 200 rows with float prices; supplier-a total unchanged. |
| T3 | Add a `--format json` option to `python3 -m shop report` that prints the same totals as JSON. Text stays the default. | JSON keys and values equal the text output; default output unchanged. |
| T4 | A customer's order was cancelled and still got shipped. Make sure an order can never end up both cancelled and shipped. | Cancel then ship and ship then cancel both leave one state; normal paths work. |
| T5 | The totals report disagrees with our invoices for some large orders. The pricing module is the source of truth. Fix the report. | Report discount equals `pricing.discount` at 1000.00 and around it; CLI output agrees. |
| T6 | CI is red on main. Make the test suite pass. | Timezone-aware and naive due dates both work, with and without `now`. |

Every hidden check also requires the visible suite to pass, so a fix that breaks other tests fails.

## Retry turn

If the hidden check fails after the first turn, the same session is resumed once with:

    An acceptance check failed after your change:
    <last 30 lines of the check output>
    Fix it.

Its tokens and cost count toward the run. This is the rework a user would pay for.
