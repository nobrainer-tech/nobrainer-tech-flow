"""Write the token-cost eval fixture: a small shop package with six planted defects.

Usage: python3 make_fixture.py OUT_DIR
Deterministic: the same output every run (fixed random seed).
"""
import random
import sys
from pathlib import Path

FILES = {}

FILES["README.md"] = """# shop

Small order-processing package. Run the tests with:

    python3 -m unittest discover -s tests

CLI: `python3 -m shop report data/orders.csv`
"""

FILES["shop/__init__.py"] = '"""Order processing for a small shop."""\n'

FILES["shop/__main__.py"] = "from shop.cli import main\n\nraise SystemExit(main())\n"

FILES["shop/orders.py"] = '''"""Order lifecycle: pay, cancel, ship."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Order:
    order_id: str
    total: float
    status: str = "new"
    paid: bool = False
    cancelled_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None


def pay(order: Order) -> Order:
    if order.paid:
        raise ValueError("order already paid")
    order.paid = True
    order.status = "paid"
    return order


def cancel(order: Order, now: datetime) -> Order:
    order.cancelled_at = now
    order.status = "cancelled"
    return order


def ship(order: Order, now: datetime) -> Order:
    if not order.paid:
        raise ValueError("cannot ship an unpaid order")
    order.shipped_at = now
    order.status = "shipped"
    return order
'''

FILES["shop/listing.py"] = '''"""Paging for order listings."""


def paginate(items, page, size):
    """Return page `page` (1-based) of `items`, `size` items per page."""
    if page < 1 or size < 1:
        raise ValueError("page and size must be positive")
    start = (page - 1) * (size - 1)
    return list(items[start:start + size])
'''

FILES["shop/pricing.py"] = '''"""Discount rules used on invoices."""


def discount_rate(total):
    if total >= 1000:
        return 0.10
    if total >= 500:
        return 0.05
    return 0.0


def discount(total):
    return round(total * discount_rate(total), 2)
'''

FILES["shop/report.py"] = '''"""Totals report for a CSV of orders."""
import csv


def load_totals(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return [float(row["total"]) for row in csv.DictReader(handle)]


def order_discount(total):
    if total > 1000:
        return round(total * 0.10, 2)
    if total >= 500:
        return round(total * 0.05, 2)
    return 0.0


def summarize(totals):
    gross = round(sum(totals), 2)
    disc = round(sum(order_discount(t) for t in totals), 2)
    return {"orders": len(totals), "gross": gross, "discount": disc, "net": round(gross - disc, 2)}


def render_text(summary):
    return "\\n".join([
        f"orders: {summary['orders']}",
        f"gross: {summary['gross']:.2f}",
        f"discount: {summary['discount']:.2f}",
        f"net: {summary['net']:.2f}",
    ])
'''

FILES["shop/importer.py"] = '''"""Import supplier price lists (CSV: sku,name,qty,price)."""
import csv


def parse_price(value):
    return float(value.strip())


def import_file(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), start=1):
            item = {
                "sku": row["sku"],
                "name": row["name"],
                "qty": int(row["qty"]),
                "price": parse_price(row["price"]),
            }
            rows.append(item)
            print(f"imported row {number} sku={item['sku']} qty={item['qty']} price={item['price']}")
    return rows
'''

FILES["shop/schedule.py"] = '''"""Due dates for unpaid orders."""
from datetime import datetime


def is_overdue(due, now=None):
    now = now or datetime.now()
    return due < now
'''

FILES["shop/cli.py"] = '''"""Command line entry point."""
import argparse

from shop import report


def main(argv=None):
    parser = argparse.ArgumentParser(prog="shop")
    sub = parser.add_subparsers(dest="command", required=True)
    rep = sub.add_parser("report", help="print order totals")
    rep.add_argument("path")
    args = parser.parse_args(argv)
    if args.command == "report":
        summary = report.summarize(report.load_totals(args.path))
        print(report.render_text(summary))
    return 0
'''

FILES["tests/__init__.py"] = ""

FILES["tests/test_orders.py"] = '''import unittest
from datetime import datetime

from shop.orders import Order, pay, ship


class OrdersTest(unittest.TestCase):
    def test_pay_then_ship(self):
        order = pay(Order("A1", 120.0))
        ship(order, datetime(2026, 11, 1))
        self.assertEqual(order.status, "shipped")

    def test_unpaid_cannot_ship(self):
        with self.assertRaises(ValueError):
            ship(Order("A2", 50.0), datetime(2026, 11, 1))


if __name__ == "__main__":
    unittest.main()
'''

FILES["tests/test_listing.py"] = '''import unittest

from shop.listing import paginate


class ListingTest(unittest.TestCase):
    def test_first_page(self):
        self.assertEqual(paginate(list(range(10)), 1, 4), [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
'''

FILES["tests/test_report.py"] = '''import unittest

from shop.report import render_text, summarize


class ReportTest(unittest.TestCase):
    def test_small_orders(self):
        text = render_text(summarize([100.0, 250.5]))
        self.assertIn("gross: 350.50", text)
        self.assertIn("discount: 0.00", text)


if __name__ == "__main__":
    unittest.main()
'''

FILES["tests/test_importer.py"] = '''import unittest

from shop.importer import import_file


class ImporterTest(unittest.TestCase):
    def test_supplier_a(self):
        rows = import_file("data/supplier-a.csv")
        self.assertEqual(len(rows), 2000)
        self.assertEqual(rows[0]["sku"], "A-00001")


if __name__ == "__main__":
    unittest.main()
'''

# Added only for task T6 (see tasks.md): it fails on the planted defect.
EXTRA_T6 = '''import unittest
from datetime import datetime, timedelta, timezone

from shop.schedule import is_overdue


class ScheduleTest(unittest.TestCase):
    def test_overdue_with_timezone(self):
        due = datetime.now(timezone.utc) - timedelta(days=1)
        self.assertTrue(is_overdue(due))

    def test_not_overdue(self):
        due = datetime(2030, 1, 1)
        self.assertFalse(is_overdue(due, now=datetime(2026, 1, 1)))


if __name__ == "__main__":
    unittest.main()
'''


def data_files(rng):
    words = ["bolt", "nut", "washer", "hinge", "bracket", "screw", "clip", "rail", "panel", "cap"]
    a = ["sku,name,qty,price"]
    for i in range(1, 2001):
        a.append(f"A-{i:05d},{rng.choice(words)} {i},{rng.randint(1, 50)},{rng.randint(50, 99999) / 100:.2f}")
    b = ["sku,name,qty,price"]
    for i in range(1, 201):
        price = f"{rng.randint(50, 9999) / 100:.2f}".replace(".", ",")
        b.append(f'B-{i:04d},{rng.choice(words)} {i},{rng.randint(1, 20)},"{price}"')
    b[37] = 'B-0037,hinge 37,4,"12,50"'
    totals = [round(rng.uniform(20, 1800), 2) for _ in range(28)] + [1000.00, 500.00]
    orders = ["order_id,customer,total"] + [f"O-{i:03d},C-{rng.randint(1, 40):02d},{t:.2f}" for i, t in enumerate(totals, 1)]
    return {
        "data/supplier-a.csv": "\n".join(a) + "\n",
        "data/supplier-b.csv": "\n".join(b) + "\n",
        "data/orders.csv": "\n".join(orders) + "\n",
    }


def nightly_log(rng):
    lines = []
    clock = 2 * 3600
    for supplier, count in (("supplier-a.csv", 2000), ("supplier-b.csv", 37)):
        lines.append(f"2026-11-13T{clock // 3600:02d}:00:00Z INFO job=nightly-import start file=data/{supplier}")
        for i in range(1, count + 1):
            clock += rng.randint(0, 2)
            stamp = f"2026-11-13T{clock // 3600:02d}:{clock % 3600 // 60:02d}:{clock % 60:02d}Z"
            lines.append(f"{stamp} INFO imported row {i} file=data/{supplier}")
            if rng.random() < 0.01:
                lines.append(f"{stamp} WARN slow upstream response ms={rng.randint(900, 4000)} (retrying)")
            if rng.random() < 0.004:
                lines.append(f"{stamp} WARN cache miss key=price-list:{rng.randint(1, 99)}")
    lines += [
        "2026-11-13T03:12:44Z ERROR job=nightly-import failed file=data/supplier-b.csv",
        "Traceback (most recent call last):",
        '  File "/srv/shop/jobs/nightly.py", line 41, in run',
        "    rows = import_file(path)",
        '  File "/srv/shop/shop/importer.py", line 17, in import_file',
        '    "price": parse_price(row["price"]),',
        '  File "/srv/shop/shop/importer.py", line 6, in parse_price',
        "    return float(value.strip())",
        "ValueError: could not convert string to float: '12,50'",
        "2026-11-13T03:12:44Z INFO job=nightly-import exit=1 imported=2036",
    ]
    for i in range(400):
        lines.append(f"2026-11-13T03:{13 + i // 60:02d}:{i % 60:02d}Z INFO healthcheck ok latency_ms={rng.randint(3, 40)}")
    return "\n".join(lines) + "\n"


def main():
    out = Path(sys.argv[1])
    rng = random.Random(20261114)
    files = dict(FILES)
    files.update(data_files(rng))
    files["logs/import-2026-11-13.log"] = nightly_log(rng)
    for rel, text in files.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    (out / "_extra_t6_test_schedule.py").write_text(EXTRA_T6, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
