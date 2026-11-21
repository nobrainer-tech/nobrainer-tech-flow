"""Order lifecycle: pay, cancel, ship."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class Order:
    order_id: str
    total: Decimal
    status: str = "new"
    paid: bool = False
    cancelled_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None


def pay(order: Order) -> Order:
    if order.paid:
        raise ValueError("order already paid")
    if order.cancelled_at is not None:
        raise ValueError("cannot pay a cancelled order")
    order.paid = True
    order.status = "paid"
    return order


def cancel(order: Order, now: datetime) -> Order:
    if order.shipped_at is not None:
        raise ValueError("cannot cancel a shipped order")
    order.cancelled_at = now
    order.status = "cancelled"
    return order


def ship(order: Order, now: datetime) -> Order:
    if not order.paid:
        raise ValueError("cannot ship an unpaid order")
    if order.cancelled_at is not None:
        raise ValueError("cannot ship a cancelled order")
    order.shipped_at = now
    order.status = "shipped"
    return order
