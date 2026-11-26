# shop

Small order-processing package. Run the tests with:

    python3 -m unittest discover -s tests

CLI: `python3 -m shop report data/orders.csv`

## Orders files

`order_id,customer,total` with an optional `currency` column (any column order). Files
live in `data/` and `data/archive/`.

## Report output

`report` prints one block per currency that occurs in the file. Blocks are separated by one
blank line; the PLN block comes first, the other currencies follow in alphabetical order of
their code. A currency with no orders has no block. A block looks like this:

    currency: PLN
    orders: 3
    gross: 1450.00
    discount: 72.50
    net: 1377.50

The currency code is printed in upper case. The discount of each order follows the pricing
rule (`shop/pricing.py`) whatever the currency. A file without a currency column is reported
as a single PLN block.
