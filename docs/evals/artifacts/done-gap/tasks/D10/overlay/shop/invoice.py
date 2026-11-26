"""Plain-text invoice for one order."""
from shop import pricing


def render_invoice(order):
    discount = pricing.discount(order.total)
    return "\n".join([
        f"invoice {order.order_id}",
        f"total: {order.total:.2f}",
        f"discount: {discount:.2f}",
        f"to pay: {order.total - discount:.2f}",
    ])
