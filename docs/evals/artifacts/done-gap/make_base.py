"""Write the done-gap base fixture: the token-cost `shop` fixture with its planted defects fixed.

Usage: python3 make_base.py OUT_DIR
Deterministic. The visible suite (python3 -m unittest discover -s tests) passes on the output.
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXED = {}

FIXED["shop/listing.py"] = '''"""Paging for order listings."""


def paginate(items, page, size):
    """Return page `page` (1-based) of `items`, `size` items per page."""
    if page < 1 or size < 1:
        raise ValueError("page and size must be positive")
    start = (page - 1) * size
    return list(items[start:start + size])
'''

FIXED["shop/report.py"] = '''"""Totals report for a CSV of orders."""
import csv

from shop import pricing


def load_totals(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return [float(row["total"]) for row in csv.DictReader(handle)]


def summarize(totals):
    gross = round(sum(totals), 2)
    disc = round(sum(pricing.discount(t) for t in totals), 2)
    return {"orders": len(totals), "gross": gross, "discount": disc, "net": round(gross - disc, 2)}


def render_text(summary):
    return "\\n".join([
        f"orders: {summary['orders']}",
        f"gross: {summary['gross']:.2f}",
        f"discount: {summary['discount']:.2f}",
        f"net: {summary['net']:.2f}",
    ])
'''

FIXED["shop/importer.py"] = '''"""Import supplier price lists (CSV: sku,name,qty,price)."""
import csv


def parse_price(value):
    return float(value.strip().replace(",", "."))


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

FIXED["shop/schedule.py"] = '''"""Due dates for unpaid orders."""
from datetime import datetime, timezone


def is_overdue(due, now=None):
    if now is None:
        now = datetime.now(timezone.utc) if due.tzinfo else datetime.now()
    return due < now
'''

FIXED["shop/orders.py"] = '''"""Order lifecycle: pay, cancel, ship."""
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
    if order.cancelled_at is not None:
        raise ValueError("cannot pay a cancelled order")
    order.paid = True
    order.status = "paid"
    return order


def cancel(order: Order, now: datetime) -> Order:
    if order.shipped_at is not None:
        raise ValueError("cannot cancel a shipped order")
    order.cancelled_at = now
    order.status = "cancelled"
    return order


def ship(order: Order, now: datetime) -> Order:
    if not order.paid:
        raise ValueError("cannot ship an unpaid order")
    if order.cancelled_at is not None:
        raise ValueError("cannot ship a cancelled order")
    order.shipped_at = now
    order.status = "shipped"
    return order
'''


def main() -> int:
    out = Path(sys.argv[1])
    subprocess.run([sys.executable, "-I", str(HERE.parent / "token-cost" / "make_fixture.py"), str(out)], check=True)
    (out / "_extra_t6_test_schedule.py").unlink()
    for rel, text in FIXED.items():
        (out / rel).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
