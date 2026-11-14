"""Discount rules used on invoices."""
from zoneinfo import ZoneInfo

WARSAW = ZoneInfo("Europe/Warsaw")


def discount_rate(total):
    if total >= 1000:
        return 0.10
    if total >= 500:
        return 0.05
    return 0.0


def discount(total):
    return round(total * discount_rate(total), 2)


def discount_at(total, placed_at):
    weekend = placed_at.astimezone(WARSAW).weekday() >= 5
    return round(total * (discount_rate(total) + (0.02 if weekend else 0.0)), 2)
