"""Assign orders to couriers.

`assign(orders, couriers)` returns a dict mapping every order id to a courier
name, or to None when no courier can take the order.

    order:   {"id": str, "zone": str, "weight": int}
    courier: {"name": str, "zones": [str, ...], "capacity": int}

Rules, applied in this order:

1. Orders are served in ascending order id.
2. A courier is eligible for an order if it serves the order's zone and its
   remaining capacity is at least the order's weight.
3. Among eligible couriers the one with the largest remaining capacity gets the
   order. Ties are broken by courier name, ascending.
4. The order's weight is deducted from that courier's remaining capacity.
5. An order with no eligible courier is assigned None and does not stop the
   orders after it.

The result must not depend on the order of the input lists or on the process
that runs it.
"""


def assign(orders, couriers):
    remaining = {c["name"]: c["capacity"] for c in couriers}
    zones = {c["name"]: set(c["zones"]) for c in couriers}
    result = {}
    for order in sorted(orders, key=lambda o: o["id"]):
        eligible = {
            name for name in remaining
            if order["zone"] in zones[name] and remaining[name] >= order["weight"]
        }
        if not eligible:
            result[order["id"]] = None
            continue
        best = max(eligible, key=lambda name: remaining[name])
        remaining[best] -= order["weight"]
        result[order["id"]] = best
    return result
