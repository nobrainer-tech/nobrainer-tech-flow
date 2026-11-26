"""Order lifecycle: pay, cancel, ship, return."""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

RETURN_WINDOW = timedelta(days=30)
RETURN_REASONS = ("damaged", "wrong_item", "not_as_described", "changed_mind")


@dataclass
class Order:
    order_id: str
    total: float
    status: str = "new"
    paid: bool = False
    cancelled_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    returned_at: Optional[datetime] = None
    return_reason: Optional[str] = None


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
    if order.status == "returned":
        raise ValueError("cannot cancel a returned order")
    order.cancelled_at = now
    order.status = "cancelled"
    return order


def ship(order: Order, now: datetime) -> Order:
    if order.status == "returned":
        raise ValueError("cannot ship a returned order")
    if not order.paid:
        raise ValueError("cannot ship an unpaid order")
    if order.cancelled_at is not None:
        raise ValueError("cannot ship a cancelled order")
    order.shipped_at = now
    order.status = "shipped"
    return order


def return_order(order: Order, now: datetime, reason: Optional[str]) -> Order:
    if order.status == "returned":
        raise ValueError("order already returned")
    if order.status != "shipped" or order.shipped_at is None:
        raise ValueError("only a shipped order can be returned")
    if now - order.shipped_at > RETURN_WINDOW:
        raise ValueError("return window of 30 days has passed")
    if reason not in RETURN_REASONS:
        raise ValueError(f"unknown return reason: {reason!r}")
    order.status = "returned"
    order.returned_at = now
    order.return_reason = reason
    return order
