"""Streaming totals report for large order files.

Reads the CSV row by row and keeps only running sums, so memory use does not
grow with the number of orders.
"""
import csv

from shop import pricing


def summarize_path(path):
    orders = 0
    gross = 0.0
    disc = 0.0
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            if row["status"] == "cancelled":
                continue
            total = float(row["total"])
            orders += 1
            gross += total
            disc += pricing.discount(total)
    gross = round(gross, 2)
    disc = round(disc, 2)
    return {"orders": orders, "gross": gross, "discount": disc, "net": round(gross - disc, 2)}
