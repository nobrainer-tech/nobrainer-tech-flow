import unittest
from datetime import datetime
from shop.orders import Order, cancel, pay, ship, ship_line

NOW = datetime(2026, 11, 14, 12, 0)

def paid_order():
    return pay(Order("L1", 90.0, lines={"a": 1, "b": 2}))

class H4(unittest.TestCase):
    def test_default_lines(self):
        self.assertEqual(Order("L0", 1.0).lines, {})

    def test_line_by_line(self):
        order = paid_order()
        ship_line(order, "a", NOW)
        self.assertEqual(order.status, "partially_shipped")
        self.assertIsNone(order.shipped_at)
        ship_line(order, "b", NOW)
        self.assertEqual(order.status, "shipped")
        self.assertEqual(order.shipped_at, NOW)

    def test_same_line_twice(self):
        order = paid_order()
        ship_line(order, "a", NOW)
        with self.assertRaises(ValueError):
            ship_line(order, "a", NOW)
        self.assertEqual(order.status, "partially_shipped")

    def test_unknown_sku_and_unpaid(self):
        with self.assertRaises(ValueError):
            ship_line(paid_order(), "zz", NOW)
        unpaid = Order("L2", 10.0, lines={"a": 1})
        with self.assertRaises(ValueError):
            ship_line(unpaid, "a", NOW)
        self.assertNotIn(unpaid.status, ("shipped", "partially_shipped"))

    def test_cancelled_cannot_ship_a_line(self):
        order = cancel(paid_order(), NOW)
        with self.assertRaises(ValueError):
            ship_line(order, "a", NOW)
        self.assertEqual(order.status, "cancelled")

    def test_no_cancel_after_a_line_shipped(self):
        order = paid_order()
        ship_line(order, "a", NOW)
        with self.assertRaises(ValueError):
            cancel(order, NOW)
        self.assertEqual(order.status, "partially_shipped")
        self.assertIsNone(order.cancelled_at)

    def test_ship_without_lines(self):
        order = pay(Order("L3", 10.0))
        ship(order, NOW)
        self.assertEqual(order.status, "shipped")
