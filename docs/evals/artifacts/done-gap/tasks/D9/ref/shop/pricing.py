"""Discount rules used on invoices."""
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def discount_rate(total):
    if total >= Decimal("1000"):
        return Decimal("0.10")
    if total >= Decimal("500"):
        return Decimal("0.05")
    return Decimal("0.00")


def discount(total):
    return (total * discount_rate(total)).quantize(CENT, rounding=ROUND_HALF_UP)
