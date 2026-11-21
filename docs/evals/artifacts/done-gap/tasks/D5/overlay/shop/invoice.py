"""Text invoice for a single order."""
import csv

from shop import pricing

ORDERS_PATH = "data/orders.csv"


def load_order(order_id, path=ORDERS_PATH):
    """The row of `order_id` in the orders CSV, as a dict."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["order_id"] == order_id:
                return row
    raise KeyError(order_id)


def render_invoice(order_id, total):
    disc = pricing.discount(total)
    return "\n".join([
        f"invoice: {order_id}",
        f"total: {total:.2f}",
        f"discount: {disc:.2f}",
        f"to pay: {total - disc:.2f}",
    ])
