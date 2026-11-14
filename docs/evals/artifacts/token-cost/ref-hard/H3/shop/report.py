"""Totals report for a CSV of orders."""
import csv
from datetime import datetime

from shop import pricing


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_totals(path):
    return [float(row["total"]) for row in load_rows(path)]


def order_discount(row):
    total = float(row["total"])
    if row.get("placed_at"):
        return pricing.discount_at(total, datetime.fromisoformat(row["placed_at"].replace("Z", "+00:00")))
    return pricing.discount(total)


def summarize(totals, discounts=None):
    gross = round(sum(totals), 2)
    disc = round(sum(discounts) if discounts is not None else sum(pricing.discount(t) for t in totals), 2)
    return {"orders": len(totals), "gross": gross, "discount": disc, "net": round(gross - disc, 2)}


def summarize_file(path):
    rows = load_rows(path)
    return summarize([float(r["total"]) for r in rows], [order_discount(r) for r in rows])


def render_text(summary):
    return "\n".join([
        f"orders: {summary['orders']}",
        f"gross: {summary['gross']:.2f}",
        f"discount: {summary['discount']:.2f}",
        f"net: {summary['net']:.2f}",
    ])
