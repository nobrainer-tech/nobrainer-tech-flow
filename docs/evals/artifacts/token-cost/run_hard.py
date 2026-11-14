"""Hard-task token-cost eval: PLAIN vs FLOW, five tasks, three repeats, up to two retry turns.

Usage: python3 run_hard.py EVAL_DIR FLOW_CHECKOUT [--only H1-plain-1,...] [--workers 2]
EVAL_DIR holds run.py, make_fixture.py, skills.tar and hidden/hidden_h1.py ... hidden_h5.py.
Writes EVAL_DIR/runs/<task>-<arm>-<rep>/{turnN.jsonl,checkN.txt,result.json}.
"""
import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run  # noqa: E402  (shared prepare, claude and check helpers)

MAX_RETRIES = 2
PROMPTS = {
    "H1": (
        "Add refunds. Add `refund(order, amount, now)` to shop/orders.py. Only a paid order can be refunded. "
        "It can be refunded any number of times, partially or fully, but the total refunded must never exceed "
        "`order.total`; a refund that would exceed it raises ValueError and changes nothing. Keep the running total "
        "in `order.refunded` (starts at 0). When the refunded total reaches `order.total`, the status becomes "
        "\"refunded\". In shop/report.py, `summarize(totals, refunds=None)` takes an optional list of refund amounts: "
        "the summary gets a \"refunds\" key, net becomes gross minus discount minus refunds, and `render_text` "
        "prints a `refunds: X.XX` line."
    ),
    "H2": (
        "Supplier C sends European exports: `;` as the column delimiter and prices like `1.234,50`. Make "
        "`import_file` handle both comma- and semicolon-delimited files automatically, detecting the delimiter from "
        "the header line. Price rules: if a price contains both '.' and ',', the right-most of them is the decimal "
        "separator and the other is a thousands separator; if it contains only ',', that comma is the decimal "
        "separator. A sample file is data/supplier-c.csv. Every supplier file in data/ must import."
    ),
    "H3": (
        "Weekend orders get extra discount. An order placed on a Saturday or Sunday in Europe/Warsaw local time "
        "gets 2 percentage points more than its normal rate (0.10 becomes 0.12, 0.05 becomes 0.07, 0 becomes 0.02). "
        "Add `pricing.discount_at(total, placed_at)`, where `placed_at` is a timezone-aware datetime, returning the "
        "rounded discount amount like `pricing.discount`. data/orders-dated.csv adds a `placed_at` column in UTC "
        "ISO-8601 (for example 2026-03-28T23:30:00Z); when that column is present, `python3 -m shop report` must "
        "compute discounts with `discount_at`. The report and the invoices (the pricing module) must always agree."
    ),
    "H4": (
        "Orders can now ship line by line. Add `lines` to Order: a dict from sku to quantity, empty by default. "
        "Add `ship_line(order, sku, now)` to shop/orders.py. Shipping a line requires a paid order that is not "
        "cancelled, and a sku that is in the order and not shipped yet; otherwise raise ValueError and change "
        "nothing. While some but not all lines are shipped the status is \"partially_shipped\"; when the last line "
        "ships the status becomes \"shipped\" and `shipped_at` is set. `cancel` must raise ValueError once any line "
        "has shipped. `ship()` keeps working for orders without lines."
    ),
    "H5": (
        "The payment provider retries its callbacks. Change `pay` to `pay(order, payment_id=None)` and store the id "
        "in `order.payment_id`. Paying again with the same payment_id must return the order unchanged; a different "
        "payment_id on an already paid order must raise ValueError and change nothing; paying a cancelled order must "
        "raise ValueError. Calls without payment_id keep today's behaviour."
    ),
}
SUPPLIER_C = [
    "sku;name;qty;price",
    *[f"C-{i:04d};clip {i};{i % 9 + 1};{i},{i % 100:02d}" for i in range(1, 7)],
    'C-0007;"bolt; zinc";3;1.234,50',
    "C-0008;hinge 8;2;12,5",
    "C-0009;cap 9;5;7",
    *[f"C-{i:04d};rail {i};{i % 7 + 1};{i * 3}.{i % 1000:03d},{i % 100:02d}" for i in range(10, 41)],
]
ORDERS_DATED = [
    "order_id,customer,total,placed_at",
    "D-001,C-01,100.00,2026-03-27T23:30:00Z",
    "D-002,C-02,100.00,2026-03-29T22:30:00Z",
    "D-003,C-03,1000.00,2026-01-25T22:30:00Z",
    "D-004,C-04,600.00,2026-03-25T10:00:00Z",
    "D-005,C-05,1000.00,2026-03-25T10:00:00Z",
    "D-006,C-06,499.99,2026-07-25T21:59:00Z",
    "D-007,C-07,750.00,2026-07-26T22:30:00Z",
    "D-008,C-08,1500.00,2026-10-25T00:30:00Z",
    "D-009,C-09,250.00,2026-10-24T21:30:00Z",
    "D-010,C-10,999.99,2026-11-14T08:00:00Z",
]


def add_data(repo: Path) -> None:
    (repo / "data" / "supplier-c.csv").write_text("\n".join(SUPPLIER_C) + "\n", encoding="utf-8")
    (repo / "data" / "orders-dated.csv").write_text("\n".join(ORDERS_DATED) + "\n", encoding="utf-8")
    subprocess.run(run.GIT + ["add", "-A"], cwd=repo, check=True)
    subprocess.run(run.GIT + ["commit", "-q", "-m", "data"], cwd=repo, check=True)


def run_one(eval_dir: Path, flow: Path, name: str) -> dict:
    task, arm, rep = name.split("-")
    run_dir = eval_dir / "runs" / name
    run_dir.mkdir(parents=True, exist_ok=True)
    repo = run_dir / "repo"
    run.prepare(eval_dir, flow, task, arm, repo)
    add_data(repo)
    turns = [run.claude(["-p", PROMPTS[task]], repo, run_dir / "turn1.jsonl")]
    passes = [run.check(eval_dir, task, repo, run_dir / "check1.txt")]
    while not passes[-1] and len(turns) <= MAX_RETRIES and turns[0]["session"]:
        number = len(turns)
        tail = "\n".join((run_dir / f"check{number}.txt").read_text(encoding="utf-8").splitlines()[-30:])
        turns.append(run.claude(["-p", run.RETRY.format(tail=tail), "--resume", turns[0]["session"]], repo,
                                run_dir / f"turn{number + 1}.jsonl"))
        passes.append(run.check(eval_dir, task, repo, run_dir / f"check{number + 1}.txt"))
    diff = subprocess.run(["git", "diff", "--stat", "HEAD"], cwd=repo, capture_output=True, text=True).stdout
    result = {"name": name, "task": task, "arm": arm, "rep": int(rep), "passes": passes,
              "p1": passes[0], "p2": passes[-1], "turns": turns, "turn1": turns[0], "diffstat": diff}
    (run_dir / "result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    costs = [(t["result"] or {}).get("total_cost_usd") for t in turns]
    print(f"{name}\tpasses={passes}\tcosts={costs}", flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_dir", type=Path)
    parser.add_argument("flow", type=Path)
    parser.add_argument("--only")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    names = []
    for rep in (1, 2, 3):
        for i, task in enumerate(PROMPTS):
            arms = ("plain", "flow") if (i + rep) % 2 else ("flow", "plain")
            names += [f"{task}-{arm}-{rep}" for arm in arms]
    if args.only:
        names = [n for n in names if n in args.only.split(",")]

    def safe(name):
        try:
            return run_one(args.eval_dir.resolve(), args.flow.resolve(), name)
        except Exception as error:  # keep the other runs going; the failure is reported
            print(f"{name}\tHARNESS_ERROR\t{error!r}", flush=True)
            return None

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(safe, names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
