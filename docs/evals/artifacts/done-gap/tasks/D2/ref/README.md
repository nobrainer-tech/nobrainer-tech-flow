# shop

Small order-processing package. Run the tests with:

    python3 -m unittest discover -s tests

See `CONTRIBUTING.md` before opening a pull request.

## CLI

### report

    python3 -m shop report PATH [--top N]

Reads an orders CSV (`order_id,customer,total`) and prints four lines: `orders`, `gross`,
`discount` and `net`.

With `--top N` it then prints the N largest orders, one per line as `ORDER_ID TOTAL`, largest
first (equal totals keep their order in the file).

## Layout

- `shop/orders.py` order lifecycle
- `shop/pricing.py` discount rules
- `shop/report.py` totals report
