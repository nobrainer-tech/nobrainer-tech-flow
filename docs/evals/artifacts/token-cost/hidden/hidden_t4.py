import unittest
from datetime import datetime
from shop.orders import Order, cancel, pay, ship

NOW = datetime(2026, 11, 13, 12, 0)

def attempt(fn, *args):
    try:
        fn(*args)
    except Exception:
        pass

class T4(unittest.TestCase):
    def test_cancelled_cannot_ship(self):
        order = pay(Order("X1", 100.0))
        cancel(order, NOW)
        attempt(ship, order, NOW)
        self.assertIsNone(order.shipped_at)
        self.assertEqual(order.status, "cancelled")

    def test_shipped_cannot_cancel(self):
        order = pay(Order("X2", 100.0))
        ship(order, NOW)
        attempt(cancel, order, NOW)
        self.assertIsNone(order.cancelled_at)
        self.assertEqual(order.status, "shipped")

    def test_normal_paths(self):
        order = pay(Order("X3", 10.0))
        ship(order, NOW)
        self.assertEqual(order.status, "shipped")
        other = cancel(Order("X4", 10.0), NOW)
        self.assertEqual(other.status, "cancelled")
