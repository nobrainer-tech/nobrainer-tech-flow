import unittest
from datetime import datetime
from shop.orders import Order, cancel, pay

NOW = datetime(2026, 11, 14, 12, 0)

class H5(unittest.TestCase):
    def test_default(self):
        self.assertIsNone(Order("P0", 1.0).payment_id)

    def test_retry_same_id(self):
        order = pay(Order("P1", 10.0), "pay-1")
        again = pay(order, "pay-1")
        self.assertIs(again, order)
        self.assertEqual((order.status, order.paid, order.payment_id), ("paid", True, "pay-1"))

    def test_other_id_changes_nothing(self):
        order = pay(Order("P2", 10.0), "pay-1")
        with self.assertRaises(ValueError):
            pay(order, "pay-2")
        self.assertEqual(order.payment_id, "pay-1")

    def test_cancelled_cannot_be_paid(self):
        for payment_id in ("pay-1", None):
            order = cancel(Order("P3", 10.0), NOW)
            with self.assertRaises(ValueError):
                pay(order, payment_id)
            self.assertEqual(order.status, "cancelled")
            self.assertFalse(order.paid)

    def test_without_id_keeps_today(self):
        order = pay(Order("P4", 10.0))
        with self.assertRaises(ValueError):
            pay(order)
