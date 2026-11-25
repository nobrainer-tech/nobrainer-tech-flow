import ast
import dataclasses
import unittest
import warnings
from datetime import datetime
from pathlib import Path

from shop import invoice, refunds, report
from shop.orders import Order, cancel, describe, pay, ship

ROOT = Path(__file__).resolve().parent.parent


def silently(fn, *args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return fn(*args, **kwargs)


class GrossTest(unittest.TestCase):
    def test_gross_keyword_and_positional(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            self.assertEqual(Order("A", gross=10).gross, 10)
            order = Order("A", 10, "paid")
            self.assertEqual((order.gross, order.status), (10, "paid"))

    def test_constructor_alias(self):
        with self.assertWarns(DeprecationWarning):
            order = Order("A", total=10)
        self.assertEqual(order.gross, 10)
        self.assertEqual(order.status, "new")

    def test_read_alias(self):
        order = Order("A", 7)
        with self.assertWarns(DeprecationWarning):
            value = order.total
        self.assertEqual(value, 7)

    def test_write_alias(self):
        order = Order("A", 7)
        with self.assertWarns(DeprecationWarning):
            order.total = 9
        self.assertEqual(order.gross, 9)

    def test_repr_eq_and_fields_use_gross(self):
        order = Order("A", 10)
        self.assertIn("gross=10", repr(order))
        self.assertNotIn("total", repr(order))
        self.assertEqual(order, Order("A", gross=10))
        self.assertEqual(order, silently(Order, "A", total=10))
        self.assertNotEqual(order, Order("A", 11))
        names = [f.name for f in dataclasses.fields(Order)]
        self.assertEqual(names[:3], ["order_id", "gross", "status"])
        self.assertNotIn("total", names)


class InternalUseTest(unittest.TestCase):
    def test_public_functions_raise_no_deprecation(self):
        now = datetime(2026, 11, 1)
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            order = pay(Order("A", 600.0))
            self.assertEqual(describe(order), "A: 600.00 (paid)")
            self.assertEqual(refunds.refund_amount(order, 0.5), 300.0)
            self.assertEqual(refunds.net_refund(order), 570.0)
            text = invoice.render_invoice(order)
            self.assertIn("to pay: 570.00", text)
            self.assertEqual(report.summarize_orders([order, Order("B", 100.0)])["gross"], 700.0)
            ship(order, now)
            cancel(Order("C", 5.0), now)

    def test_no_alias_use_in_shop_sources(self):
        problems = []
        for path in sorted((ROOT / "shop").glob("*.py")):
            if path.name == "orders.py":
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Attribute) and node.attr == "total":
                    problems.append(f"{path.name}:{node.lineno} .total")
                if isinstance(node, ast.keyword) and node.arg == "total":
                    problems.append(f"{path.name}:{node.lineno} total=")
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
