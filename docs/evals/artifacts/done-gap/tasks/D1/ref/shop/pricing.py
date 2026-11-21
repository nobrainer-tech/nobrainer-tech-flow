"""Discount rules used on invoices."""


def discount_rate(total):
    if total >= 1000:
        return 0.10
    if total >= 500:
        return 0.06
    return 0.0


def discount(total):
    return round(total * discount_rate(total), 2)
