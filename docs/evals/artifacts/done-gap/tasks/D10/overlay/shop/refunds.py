"""Refunds for paid orders."""
from shop import pricing


def refund_amount(order, fraction=1.0):
    """Part `fraction` of what the customer paid, rounded to cents."""
    if not order.paid:
        raise ValueError("order was not paid")
    return round(order.total * fraction, 2)


def net_refund(order):
    """Full refund minus the discount the customer got."""
    return round(order.total - pricing.discount(order.total), 2)
