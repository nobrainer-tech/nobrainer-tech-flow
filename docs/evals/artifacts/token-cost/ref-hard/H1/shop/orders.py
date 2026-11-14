"""Order lifecycle: pay, cancel, ship, refund."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Order:
    order_id: str
    total: float
    status: str = "new"
    paid: bool = False
    cancelled_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    refunded: float = 0.0


def pay(order):
    if order.paid:
        raise ValueError("order already paid")
    order.paid = True
    order.status = "paid"
    return order


def cancel(order, now):
    order.cancelled_at = now
    order.status = "cancelled"
    return order


def ship(order, now):
    if not order.paid:
        raise ValueError("cannot ship an unpaid order")
    order.shipped_at = now
    order.status = "shipped"
    return order


def refund(order, amount, now):
    if not order.paid:
        raise ValueError("only a paid order can be refunded")
    new_total = round(order.refunded + amount, 2)
    if new_total > round(order.total, 2):
        raise ValueError("refund exceeds the order total")
    order.refunded = new_total
    if new_total == round(order.total, 2):
        order.status = "refunded"
    return order
