import unittest

from shop.couriers import assign

ORDERS = [
    {"id": "R1", "zone": "N", "weight": 3},
    {"id": "R2", "zone": "S", "weight": 5},
    {"id": "R3", "zone": "N", "weight": 5},
    {"id": "R4", "zone": "E", "weight": 3},
    {"id": "R5", "zone": "N", "weight": 2},
    {"id": "R6", "zone": "S", "weight": 3},
    {"id": "R7", "zone": "N", "weight": 5},
]
COURIERS = [
    {"name": "ann", "zones": ["E", "N", "S"], "capacity": 6},
    {"name": "ben", "zones": ["E", "S"], "capacity": 8},
    {"name": "cy", "zones": ["N"], "capacity": 10},
    {"name": "dee", "zones": ["E", "N", "S"], "capacity": 10},
]


class CouriersTest(unittest.TestCase):
    def test_single_courier(self):
        result = assign([{"id": "R1", "zone": "N", "weight": 2}],
                        [{"name": "cy", "zones": ["N"], "capacity": 5}])
        self.assertEqual(result, {"R1": "cy"})

    def test_every_order_is_served(self):
        result = assign(ORDERS, COURIERS)
        self.assertEqual(sorted(result), [o["id"] for o in ORDERS])
        self.assertNotIn(None, result.values())

    def test_capacity_is_respected(self):
        result = assign(ORDERS, COURIERS)
        load = {}
        for order in ORDERS:
            name = result[order["id"]]
            load[name] = load.get(name, 0) + order["weight"]
        for courier in COURIERS:
            self.assertLessEqual(load.get(courier["name"], 0), courier["capacity"])

    def test_unservable_order_gets_none(self):
        result = assign([{"id": "R1", "zone": "W", "weight": 1}], COURIERS)
        self.assertEqual(result, {"R1": None})


if __name__ == "__main__":
    unittest.main()
