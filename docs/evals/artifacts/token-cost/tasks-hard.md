# Token cost on hard tasks: tasks

The prompts are in `run_hard.py` (`PROMPTS`), sent unchanged to both arms. Data added to the
base fixture for these tasks: `data/supplier-c.csv` (semicolon-delimited, decimal comma,
thousands dots, a quoted name containing `;`) and `data/orders-dated.csv` (UTC timestamps
around weekend midnights in Warsaw, both DST changes and an order of exactly 1000.00).

| ID | What the hidden check holds the agent to (each from a prompt sentence) |
|---|---|
| H1 | 0.1 + 0.2 refunded on a 0.3 order reaches "refunded"; an over-refund raises and changes nothing; unpaid and cancelled orders refuse; the report shows refunds and subtracts them. |
| H2 | Semicolon file with a quoted `;`; `1.234,50`, `12,5`, `7`; a comma file with `"1,234.50"`; supplier-a and supplier-b (decimal comma) import. |
| H3 | Friday 23:30 UTC is Saturday in Warsaw; Sunday 22:30 UTC is Monday in summer but Sunday in winter; 1000.00 gets 0.12 on a weekend; dated and undated reports equal the pricing module. |
| H4 | Partial then full shipping; the same line twice, an unknown sku, unpaid and cancelled orders refuse and change nothing; cancel refuses after a shipped line; `ship()` still works. |
| H5 | The same payment id is a no-op; another id raises and keeps the first; a cancelled order cannot be paid, with or without an id; a second `pay()` without an id still raises. |
