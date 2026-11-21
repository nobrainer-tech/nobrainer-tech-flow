import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

from shop.orders import Order, cancel, pay, return_order, ship

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T0 = datetime(2026, 11, 1, 12, 0, 0)
REASONS = ["damaged", "wrong_item", "not_as_described", "changed_mind"]


def shipped(order_id="R-1"):
    return ship(pay(Order(order_id, 100.0)), T0)


def run_cli(*args):
    return subprocess.run([sys.executable, "-m", "shop", *args], cwd=ROOT, capture_output=True, text=True)


def snapshot(order):
    return (order.status, order.paid, order.cancelled_at, order.shipped_at, order.returned_at, order.return_reason)


def report_lines(rows, header="order_id,customer,total,status"):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "orders.csv")
        with open(path, "w", newline="", encoding="utf-8") as handle:
            handle.write(header + "\n" + "".join(row + "\n" for row in rows))
        run = run_cli("report", path)
    assert run.returncode == 0, run.stderr
    return run.stdout.splitlines()


class HiddenTest(unittest.TestCase):
    def test_ac01_successful_return(self):
        order = shipped()
        now = T0 + timedelta(days=5)
        result = return_order(order, now, "damaged")
        self.assertIs(result, order)
        self.assertEqual(order.status, "returned")
        self.assertEqual(order.returned_at, now)
        self.assertEqual(order.return_reason, "damaged")
        self.assertTrue(order.paid)
        self.assertEqual(order.shipped_at, T0)
        self.assertIsNone(Order("X", 1.0).returned_at)
        self.assertIsNone(Order("X", 1.0).return_reason)

    def test_ac02_only_shipped(self):
        now = T0 + timedelta(days=1)
        paid_only = pay(Order("P", 10.0))
        cancelled = cancel(pay(Order("C", 10.0)), T0)
        for order in (Order("N", 10.0), paid_only, cancelled):
            before = snapshot(order)
            with self.assertRaises(ValueError):
                return_order(order, now, "damaged")
            self.assertEqual(snapshot(order), before)

    def test_ac03_thirty_day_window(self):
        on_the_limit = shipped("L")
        return_order(on_the_limit, T0 + timedelta(days=30), "changed_mind")
        self.assertEqual(on_the_limit.status, "returned")
        late = shipped("T")
        before = snapshot(late)
        with self.assertRaises(ValueError):
            return_order(late, T0 + timedelta(days=30, seconds=1), "changed_mind")
        self.assertEqual(snapshot(late), before)
        with self.assertRaises(ValueError):
            return_order(shipped("W"), T0 + timedelta(days=90), "damaged")

    def test_ac04_reason_required(self):
        now = T0 + timedelta(days=2)
        for reason in (None, "", "Damaged", "damaged ", "broken", "WRONG_ITEM"):
            order = shipped()
            before = snapshot(order)
            with self.assertRaises(ValueError, msg=repr(reason)):
                return_order(order, now, reason)
            self.assertEqual(snapshot(order), before, repr(reason))
        for reason in REASONS:
            order = shipped()
            return_order(order, now, reason)
            self.assertEqual(order.return_reason, reason)

    def test_ac05_no_second_return(self):
        order = shipped()
        first = T0 + timedelta(days=3)
        return_order(order, first, "wrong_item")
        with self.assertRaises(ValueError):
            return_order(order, T0 + timedelta(days=4), "damaged")
        self.assertEqual(order.returned_at, first)
        self.assertEqual(order.return_reason, "wrong_item")
        self.assertEqual(order.status, "returned")

    def test_ac06_frozen_after_return(self):
        order = return_order(shipped(), T0 + timedelta(days=3), "damaged")
        before = snapshot(order)
        with self.assertRaises(ValueError):
            cancel(order, T0 + timedelta(days=4))
        self.assertEqual(snapshot(order), before)
        with self.assertRaises(ValueError):
            ship(order, T0 + timedelta(days=4))
        self.assertEqual(snapshot(order), before)

    def test_ac07_report_counts_returns_separately(self):
        lines = report_lines([
            "R-1,C-1,600.00,shipped",
            "R-2,C-2,1200.00,returned",
            "R-3,C-3,80.00,paid",
            "R-4,C-4,520.00,returned",
            "R-5,C-5,1000.00,shipped",
        ])
        self.assertEqual(lines, [
            "orders: 3", "gross: 1680.00", "discount: 130.00", "net: 1550.00",
            "returned: 2", "returned_total: 1720.00",
        ])

    def test_ac07_status_column_anywhere_and_absent(self):
        lines = report_lines(["returned,R-1,C-1,300.00", "new,R-2,C-2,50.00"], header="status,order_id,customer,total")
        self.assertEqual(lines, [
            "orders: 1", "gross: 50.00", "discount: 0.00", "net: 50.00",
            "returned: 1", "returned_total: 300.00",
        ])
        lines = report_lines(["R-1,C-1,100.00", "R-2,C-2,250.50"], header="order_id,customer,total")
        self.assertEqual(lines, [
            "orders: 2", "gross: 350.50", "discount: 0.00", "net: 350.50",
            "returned: 0", "returned_total: 0.00",
        ])

    def test_ac08_return_reasons_command(self):
        run = run_cli("return-reasons")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.splitlines(), REASONS)
        for reason in run.stdout.splitlines():
            order = return_order(shipped(), T0 + timedelta(days=1), reason)
            self.assertEqual(order.return_reason, reason)


if __name__ == "__main__":
    unittest.main()
