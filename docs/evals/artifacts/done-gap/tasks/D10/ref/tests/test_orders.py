import unittest
import warnings
from datetime import datetime

from shop.orders import Order, pay, ship


class OrdersTest(unittest.TestCase):
    def test_pay_then_ship(self):
        order = pay(Order("A1", 120.0))
        ship(order, datetime(2026, 11, 1))
        self.assertEqual(order.status, "shipped")

    def test_unpaid_cannot_ship(self):
        with self.assertRaises(ValueError):
            ship(Order("A2", 50.0), datetime(2026, 11, 1))

    def test_total_alias_warns(self):
        with self.assertWarns(DeprecationWarning):
            order = Order("A3", total=9.0)
        self.assertEqual(order.gross, 9.0)
        with self.assertWarns(DeprecationWarning):
            self.assertEqual(order.total, 9.0)
        with self.assertWarns(DeprecationWarning):
            order.total = 4.0
        self.assertEqual(order.gross, 4.0)

    def test_gross_does_not_warn(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            self.assertEqual(Order("A4", gross=3.0).gross, 3.0)


if __name__ == "__main__":
    unittest.main()
