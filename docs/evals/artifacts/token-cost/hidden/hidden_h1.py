import unittest
from datetime import datetime
from shop.orders import Order, cancel, pay, refund
from shop.report import render_text, summarize

NOW = datetime(2026, 11, 14, 12, 0)

class H1(unittest.TestCase):
    def test_starts_at_zero(self):
        self.assertEqual(Order("R0", 10.0).refunded, 0)

    def test_float_parts_reach_total(self):
        order = pay(Order("R1", 0.3))
        refund(order, 0.1, NOW)
        refund(order, 0.2, NOW)
        self.assertAlmostEqual(order.refunded, 0.3)
        self.assertEqual(order.status, "refunded")

    def test_three_parts(self):
        order = pay(Order("R2", 100.0))
        for amount in (33.33, 33.33, 33.34):
            refund(order, amount, NOW)
        self.assertEqual(order.status, "refunded")

    def test_over_refund_changes_nothing(self):
        order = pay(Order("R3", 50.0))
        refund(order, 30.0, NOW)
        with self.assertRaises(ValueError):
            refund(order, 20.01, NOW)
        self.assertAlmostEqual(order.refunded, 30.0)
        self.assertNotEqual(order.status, "refunded")

    def test_unpaid_and_cancelled(self):
        order = Order("R4", 20.0)
        with self.assertRaises(ValueError):
            refund(order, 5.0, NOW)
        self.assertEqual(order.refunded, 0)
        gone = cancel(Order("R5", 20.0), NOW)
        with self.assertRaises(ValueError):
            refund(gone, 5.0, NOW)

    def test_report_refunds(self):
        summary = summarize([100.0, 250.5], refunds=[10.0, 5.5])
        self.assertAlmostEqual(summary["refunds"], 15.5)
        self.assertAlmostEqual(summary["net"], 335.0)
        text = render_text(summary)
        self.assertIn("refunds: 15.50", text)
        self.assertIn("net: 335.00", text)

    def test_report_without_refunds(self):
        self.assertIn("net: 100.00", render_text(summarize([100.0])))
