"""Plain-text invoice for one order."""
from shop import pricing


def render_invoice(order):
    discount = pricing.discount(order.gross)
    return "\n".join([
        f"invoice {order.order_id}",
        f"total: {order.gross:.2f}",
        f"discount: {discount:.2f}",
        f"to pay: {order.gross - discount:.2f}",
    ])
