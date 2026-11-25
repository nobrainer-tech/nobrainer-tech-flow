"""Invoices for a single order: text and HTML."""
import csv
import html
import os

from shop import pricing

ORDERS_PATH = "data/orders.csv"
CUSTOMERS_PATH = "data/customers.csv"
INVOICE_DIR = "invoices"


def load_order(order_id, path=ORDERS_PATH):
    """The row of `order_id` in the orders CSV, as a dict."""
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["order_id"] == order_id:
                return row
    raise KeyError(order_id)


def load_customer_name(customer_id, path=CUSTOMERS_PATH):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["customer_id"] == customer_id:
                return row["name"]
    return customer_id


def amounts(total):
    disc = pricing.discount(total)
    return f"{total:.2f}", f"{disc:.2f}", f"{total - disc:.2f}"


def render_invoice(order_id, total):
    total_text, disc_text, pay_text = amounts(total)
    return "\n".join([
        f"invoice: {order_id}",
        f"total: {total_text}",
        f"discount: {disc_text}",
        f"to pay: {pay_text}",
    ])


def render_html(order_id, customer_name, total):
    total_text, disc_text, pay_text = amounts(total)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Invoice {html.escape(order_id)}</title>
</head>
<body>
<h1>Invoice {html.escape(order_id)}</h1>
<p>Customer: {html.escape(customer_name)}</p>
<table>
<tr><th>Total</th><td>{total_text}</td></tr>
<tr><th>Discount</th><td>{disc_text}</td></tr>
<tr><th>To pay</th><td>{pay_text}</td></tr>
</table>
</body>
</html>
"""


def write_html(order_id, directory=INVOICE_DIR):
    order = load_order(order_id)
    name = load_customer_name(order["customer"])
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{order_id}.html")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_html(order_id, name, float(order["total"])))
    return path
