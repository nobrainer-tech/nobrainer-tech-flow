"""Upgrade order files to schema version 2 (see docs/schema.md)."""
import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path


def upgrade(data):
    """Return the v2 form of a parsed order, or the same object if it is already v2."""
    if not isinstance(data, dict):
        raise ValueError("not a JSON object")
    if data.get("schema") == 2:
        return data
    if "schema" in data:
        raise ValueError(f"unknown schema {data['schema']!r}")
    gross = Decimal(str(data["total"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {
        "schema": 2,
        "order_id": data["order_id"],
        "gross": f"{gross:.2f}",
        "currency": "PLN",
        "status": data["status"],
        "history": list(data.get("history", [])) + [{"event": "migrated_v2"}],
    }


def migrate_dir(directory, err=None):
    """Migrate every *.json file in `directory`; return (migrated, skipped_names)."""
    err = err or sys.stderr
    migrated, failed = 0, []
    for path in sorted(Path(directory).glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            new = upgrade(data)
        except (ValueError, KeyError, ArithmeticError) as exc:
            print(f"migrate: cannot migrate {path.name}: {exc!r}", file=err)
            failed.append(path.name)
            continue
        if new is not data:
            path.write_text(json.dumps(new, indent=2) + "\n", encoding="utf-8")
            migrated += 1
    return migrated, failed
