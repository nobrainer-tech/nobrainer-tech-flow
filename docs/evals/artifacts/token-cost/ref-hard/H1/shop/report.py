"""Totals report for a CSV of orders."""
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


def summarize(totals, refunds=None):
    gross = round(sum(totals), 2)
    disc = round(sum(order_discount(t) for t in totals), 2)
    back = round(sum(refunds or []), 2)
    return {"orders": len(totals), "gross": gross, "discount": disc, "refunds": back,
            "net": round(gross - disc - back, 2)}


def render_text(summary):
    return "\n".join([
        f"orders: {summary['orders']}",
        f"gross: {summary['gross']:.2f}",
        f"discount: {summary['discount']:.2f}",
        f"refunds: {summary.get('refunds', 0.0):.2f}",
        f"net: {summary['net']:.2f}",
    ])
