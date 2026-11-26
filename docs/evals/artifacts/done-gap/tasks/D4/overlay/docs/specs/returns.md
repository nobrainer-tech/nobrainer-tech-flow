# Returns

Status: approved. Owner: fulfilment.

Customers can send back an order after it has shipped. This spec adds returns to the order
lifecycle, the totals report and the CLI. Everything outside it is unchanged.

## Background

Today an order moves `new -> paid -> shipped`, and can be `cancelled` until it ships
(`shop/orders.py`). Support currently records returns by hand in a spreadsheet, so the totals
report overstates revenue. Returns are for the whole order only; there are no partial returns.

## Order model

`Order` gets two optional fields, both `None` by default:

- `returned_at: Optional[datetime]`
- `return_reason: Optional[str]`

A returned order has `status == "returned"`. A returned order keeps `paid == True` and its
`shipped_at`.

Every refusal in this spec is a `ValueError`, and a refused call leaves the order exactly as
it was.

## Allowed reasons

The reason of a return is one of these strings, matched exactly (lower case, no surrounding
spaces), listed here in the order used everywhere else in this spec:

1. `damaged`
2. `wrong_item`
3. `not_as_described`
4. `changed_mind`

## Acceptance criteria

**AC01. Returning a shipped order.** `return_order(order, now, reason)` in `shop/orders.py`
takes an order that is shipped and still inside the return window, with an allowed reason. It
sets `status` to `"returned"`, `returned_at` to `now`, `return_reason` to `reason`, and returns
the same order object.

**AC02. Only shipped orders.** An order whose status is not `"shipped"` (`new`, `paid`,
`cancelled`) cannot be returned.

**AC03. Thirty-day window.** An order can be returned up to and including 30 days after
`shipped_at`: `now - shipped_at <= timedelta(days=30)`. Anything later, for example 30 days
and one second, is refused.

**AC04. Reason required.** The reason must be one of the allowed reasons. `None`, an empty
string, a different case (`Damaged`), or any other text is refused.

**AC05. No second return.** A returned order cannot be returned again. Its `returned_at` and
`return_reason` keep the values of the first return.

**AC06. Frozen after return.** `cancel` and `ship` refuse a returned order, with the order
unchanged (status still `"returned"`, `cancelled_at` still `None`, `shipped_at` untouched).

**AC07. Report.** The orders CSV read by `python3 -m shop report PATH` may have a `status`
column. Rows whose status is exactly `returned` are left out of `orders`, `gross`, `discount`
and `net`, which are computed over the other rows as before. Two lines follow the `net:`
line: `returned: K`, the number of returned rows, and `returned_total: T`, the sum of their
totals with two decimals. Both lines are always printed, so a file without a `status` column
prints `returned: 0` and `returned_total: 0.00`. The first four lines keep their format.

**AC08. Reasons on the command line.** `python3 -m shop return-reasons` prints the allowed
reasons, one per line, in the order of the list above, and exits with status 0. Every reason it
prints is accepted by `return_order`.

## Out of scope

Refund payments, restocking, partial returns, and changing the CSV format for anything but
`status`.
