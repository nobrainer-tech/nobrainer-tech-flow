"""Order lifecycle: pay, cancel, ship."""
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
    payment_id: Optional[str] = None


def pay(order, payment_id=None):
    if order.cancelled_at is not None:
        raise ValueError("cannot pay a cancelled order")
    if order.paid:
        if payment_id is not None and payment_id == order.payment_id:
            return order
        raise ValueError("order already paid")
    order.paid = True
    order.payment_id = payment_id
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
