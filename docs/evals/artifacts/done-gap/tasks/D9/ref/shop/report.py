"""Totals report for a CSV of orders."""
import csv
from decimal import ROUND_HALF_UP, Decimal

from shop import pricing

CENT = Decimal("0.01")


def load_totals(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return [Decimal(row["total"]).quantize(CENT, rounding=ROUND_HALF_UP) for row in csv.DictReader(handle)]


def summarize(totals):
    gross = sum(totals, Decimal("0.00")).quantize(CENT, rounding=ROUND_HALF_UP)
    disc = sum((pricing.discount(t) for t in totals), Decimal("0.00"))
    return {"orders": len(totals), "gross": gross, "discount": disc, "net": gross - disc}


def render_text(summary):
    return "\n".join([
        f"orders: {summary['orders']}",
        f"gross: {summary['gross']:.2f}",
        f"discount: {summary['discount']:.2f}",
        f"net: {summary['net']:.2f}",
    ])
