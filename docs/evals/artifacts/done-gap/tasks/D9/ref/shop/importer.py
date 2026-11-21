"""Import supplier price lists (CSV: sku,name,qty,price)."""
import csv
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def parse_price(value):
    return Decimal(value.strip().replace(",", ".")).quantize(CENT, rounding=ROUND_HALF_UP)


def import_file(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        for number, row in enumerate(csv.DictReader(handle), start=1):
            item = {
                "sku": row["sku"],
                "name": row["name"],
                "qty": int(row["qty"]),
                "price": parse_price(row["price"]),
            }
            rows.append(item)
            print(f"imported row {number} sku={item['sku']} qty={item['qty']} price={item['price']}")
    return rows
