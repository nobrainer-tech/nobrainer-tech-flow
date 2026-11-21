# Order file schema

Each order is stored as one JSON file in `data/store/`, named `<order_id>.json`
(plus whatever tooling leaves there). Files are UTF-8, indented with 2 spaces.

## Version 1 (no version field)

```json
{"order_id": "O-0001", "total": 120.5, "status": "paid"}
```

`total` is a JSON number.

## Version 2

```json
{
  "schema": 2,
  "order_id": "O-0001",
  "gross": "120.50",
  "currency": "PLN",
  "status": "paid",
  "history": [{"event": "migrated_v2"}]
}
```

- `schema` is the integer `2`.
- `gross` replaces `total`. It is a string with exactly two decimals.
- `currency` is `"PLN"` for every migrated file.
- `order_id` and `status` are copied unchanged.
- `history` is a list of events. Migrating a v1 file appends
  `{"event": "migrated_v2"}` exactly once; any events already present are kept.
- `total` no longer appears in a v2 file.

A file that already has `"schema": 2` is already migrated.
