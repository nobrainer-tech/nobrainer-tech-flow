"""Totals report for a CSV of orders."""
import csv

from shop import pricing


def load_orders(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return [(row["order_id"], float(row["total"])) for row in csv.DictReader(handle)]


def load_totals(path):
    return [total for _, total in load_orders(path)]


def top_orders(orders, count):
    """The `count` largest orders, largest first; ties keep file order."""
    return sorted(orders, key=lambda item: -item[1])[:count]


def summarize(totals):
    gross = round(sum(totals), 2)
    disc = round(sum(pricing.discount(t) for t in totals), 2)
    return {"orders": len(totals), "gross": gross, "discount": disc, "net": round(gross - disc, 2)}


def render_text(summary):
    return "\n".join([
        f"orders: {summary['orders']}",
        f"gross: {summary['gross']:.2f}",
        f"discount: {summary['discount']:.2f}",
        f"net: {summary['net']:.2f}",
    ])


def render_top(orders):
    return "\n".join(f"{order_id} {total:.2f}" for order_id, total in orders)
