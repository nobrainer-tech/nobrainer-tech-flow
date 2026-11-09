"""Order fulfilment service (sample under review)."""
import time

MAX_PAYMENT_ATTEMPTS = 3


class Order:
    def __init__(self, order_id, amount):
        self.id = order_id
        self.amount = amount
        self.status = "new"  # "new" | "paid" | "shipped" | "cancelled"
        self.paid = False
        self.refunded = False
        self.shipped_at = None
        self.cancelled_at = None
        self.attempts = 0
        self.locked_at = None


def pay(order, gateway):
    if order.paid:
        return
    order.attempts += 1
    order.locked_at = time.time()
    result = gateway.charge(order.id, order.amount)  # may raise TimeoutError
    order.locked_at = None
    if result.ok:
        order.paid = True
        order.status = "paid"


def can_retry_payment(order):
    return order.status == "new" and order.attempts < MAX_PAYMENT_ATTEMPTS and order.locked_at is None


def ship(order, carrier):
    if not order.paid:
        raise ValueError("unpaid")
    carrier.dispatch(order.id)
    order.shipped_at = time.time()
    order.status = "shipped"


def cancel(order):
    if order.status == "shipped":
        raise ValueError("already shipped")
    order.cancelled_at = time.time()
    order.status = "cancelled"


def refund(order, gateway):
    if not order.paid or order.refunded:
        return
    gateway.refund(order.id, order.amount)
    order.refunded = True


def is_open(order):
    return order.status in ("new", "paid") and order.cancelled_at is None


def total_due(orders):
    return sum(o.amount for o in orders if is_open(o) and not o.paid)


def summary(order):
    if order.refunded:
        return "refunded"
    if order.shipped_at:
        return "shipped"
    return order.status
