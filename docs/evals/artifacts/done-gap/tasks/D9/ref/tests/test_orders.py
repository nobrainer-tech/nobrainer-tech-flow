import unittest
from datetime import datetime
from decimal import Decimal

from shop.orders import Order, pay, ship


class OrdersTest(unittest.TestCase):
    def test_pay_then_ship(self):
        order = pay(Order("A1", Decimal("120.00")))
        ship(order, datetime(2026, 11, 1))
        self.assertEqual(order.status, "shipped")

    def test_unpaid_cannot_ship(self):
        with self.assertRaises(ValueError):
            ship(Order("A2", Decimal("50.00")), datetime(2026, 11, 1))


if __name__ == "__main__":
    unittest.main()
