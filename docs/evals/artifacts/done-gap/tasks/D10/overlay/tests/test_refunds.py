import unittest

from shop.orders import Order, pay
from shop.refunds import net_refund, refund_amount


class RefundsTest(unittest.TestCase):
    def test_full_refund(self):
        self.assertEqual(refund_amount(pay(Order("R1", 80.0))), 80.0)

    def test_partial_refund(self):
        self.assertEqual(refund_amount(pay(Order("R2", 80.0)), 0.25), 20.0)

    def test_unpaid_refused(self):
        with self.assertRaises(ValueError):
            refund_amount(Order("R3", 80.0))

    def test_net_refund_subtracts_discount(self):
        self.assertEqual(net_refund(pay(Order("R4", 600.0))), 570.0)


if __name__ == "__main__":
    unittest.main()
