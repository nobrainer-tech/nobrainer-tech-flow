"""Totals report for a CSV of orders."""
import csv

from shop import pricing


def load_rows(path):
    """(total, returned) for each row; `returned` is True when the status column says so."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return [(float(row["total"]), row.get("status") == "returned") for row in csv.DictReader(handle)]


def load_totals(path):
    return [total for total, _ in load_rows(path)]


def summarize(totals, returned=()):
    gross = round(sum(totals), 2)
    disc = round(sum(pricing.discount(t) for t in totals), 2)
    return {
        "orders": len(totals),
        "gross": gross,
        "discount": disc,
        "net": round(gross - disc, 2),
        "returned": len(returned),
        "returned_total": round(sum(returned), 2),
    }


def summarize_rows(rows):
    kept = [total for total, returned in rows if not returned]
    sent_back = [total for total, returned in rows if returned]
    return summarize(kept, sent_back)


def render_text(summary):
    return "\n".join([
        f"orders: {summary['orders']}",
        f"gross: {summary['gross']:.2f}",
        f"discount: {summary['discount']:.2f}",
        f"net: {summary['net']:.2f}",
        f"returned: {summary['returned']}",
        f"returned_total: {summary['returned_total']:.2f}",
    ])
