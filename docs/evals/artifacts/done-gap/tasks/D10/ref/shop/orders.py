"""Order lifecycle: pay, cancel, ship."""
import warnings
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

_DEPRECATED = "Order.total is deprecated, use Order.gross"


@dataclass(init=False)
class Order:
    order_id: str
    gross: float
    status: str = "new"
    paid: bool = False
    cancelled_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None

    def __init__(self, order_id, gross=None, status="new", paid=False, cancelled_at=None,
                 shipped_at=None, *, total=None):
        if total is not None:
            if gross is not None:
                raise TypeError("pass gross or total, not both")
            warnings.warn(_DEPRECATED, DeprecationWarning, stacklevel=2)
            gross = total
        if gross is None:
            raise TypeError("missing required argument: gross")
        self.order_id = order_id
        self.gross = gross
        self.status = status
        self.paid = paid
        self.cancelled_at = cancelled_at
        self.shipped_at = shipped_at

    @property
    def total(self):
        warnings.warn(_DEPRECATED, DeprecationWarning, stacklevel=2)
        return self.gross

    @total.setter
    def total(self, value):
        warnings.warn(_DEPRECATED, DeprecationWarning, stacklevel=2)
        self.gross = value


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


def describe(order: Order) -> str:
    return f"{order.order_id}: {order.gross:.2f} ({order.status})"
