"""Totals report for a CSV of orders."""
import csv

from shop import pricing

DEFAULT_CURRENCY = "PLN"


def load_orders(path):
    """(currency, total) per row; a missing or empty currency means PLN."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return [
            (((row.get("currency") or "").strip().upper() or DEFAULT_CURRENCY), float(row["total"]))
            for row in csv.DictReader(handle)
        ]


def load_totals(path):
    return [total for _, total in load_orders(path)]


def summarize(totals):
    gross = round(sum(totals), 2)
    disc = round(sum(pricing.discount(t) for t in totals), 2)
    return {"orders": len(totals), "gross": gross, "discount": disc, "net": round(gross - disc, 2)}


def summarize_by_currency(orders):
    grouped = {}
    for currency, total in orders:
        grouped.setdefault(currency, []).append(total)
    names = sorted(grouped, key=lambda code: (code != DEFAULT_CURRENCY, code))
    return [(name, summarize(grouped[name])) for name in names]


def render_text(summary):
    return "\n".join([
        f"orders: {summary['orders']}",
        f"gross: {summary['gross']:.2f}",
        f"discount: {summary['discount']:.2f}",
        f"net: {summary['net']:.2f}",
    ])


def render_blocks(blocks):
    return "\n\n".join(f"currency: {name}\n{render_text(summary)}" for name, summary in blocks)
