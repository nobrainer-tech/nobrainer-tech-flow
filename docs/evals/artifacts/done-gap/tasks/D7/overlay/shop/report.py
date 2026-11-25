"""Totals report for a CSV of orders."""
import csv

from shop import pricing


def load_totals(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return [float(row["total"]) for row in csv.DictReader(handle)]


def summarize(totals):
    gross = round(sum(totals), 2)
    disc = round(sum(pricing.discount(t) for t in totals), 2)
    return {"orders": len(totals), "gross": gross, "discount": disc, "net": round(gross - disc, 2)}


def summarize_rows(rows):
    """Summarize order rows: dicts with at least `total` and `status`."""
    return summarize([float(row["total"]) for row in rows])


def render_text(summary):
    return "\n".join([
        f"orders: {summary['orders']}",
        f"gross: {summary['gross']:.2f}",
        f"discount: {summary['discount']:.2f}",
        f"net: {summary['net']:.2f}",
    ])
