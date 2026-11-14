"""Import supplier price lists (CSV: sku,name,qty,price; comma or semicolon)."""
import csv


def parse_price(value):
    text = value.strip()
    if "." in text and "," in text:
        decimal = "." if text.rfind(".") > text.rfind(",") else ","
        thousands = "," if decimal == "." else "."
        text = text.replace(thousands, "").replace(decimal, ".")
    elif "," in text:
        text = text.replace(",", ".")
    return float(text)


def import_file(path):
    rows = []
    with open(path, newline="", encoding="utf-8") as handle:
        header = handle.readline()
        delimiter = ";" if header.count(";") > header.count(",") else ","
        handle.seek(0)
        for number, row in enumerate(csv.DictReader(handle, delimiter=delimiter), start=1):
            item = {"sku": row["sku"], "name": row["name"], "qty": int(row["qty"]),
                    "price": parse_price(row["price"])}
            rows.append(item)
            print(f"imported row {number} sku={item['sku']} qty={item['qty']} price={item['price']}")
    return rows
