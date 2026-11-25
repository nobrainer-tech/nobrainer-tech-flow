# shop

Small order-processing package. Run the tests with:

    python3 -m unittest discover -s tests

See `CONTRIBUTING.md` before opening a pull request.

## CLI

### report

    python3 -m shop report PATH

Reads an orders CSV (`order_id,customer,total`) and prints four lines: `orders`, `gross`,
`discount` and `net`.

## Layout

- `shop/orders.py` order lifecycle
- `shop/pricing.py` discount rules
- `shop/report.py` totals report
