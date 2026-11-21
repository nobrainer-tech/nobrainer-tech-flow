import os
import subprocess
import sys
import tempfile
import unittest


def run_report(rows, *extra):
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "orders.csv")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("order_id,customer,total\n" + rows)
        return subprocess.run([sys.executable, "-m", "shop", "report", path, *extra], capture_output=True, text=True)


class CliTest(unittest.TestCase):
    def test_report(self):
        run = run_report("A-1,C-1,100.00\nA-2,C-2,250.50\n")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(
            run.stdout.splitlines(),
            ["orders: 2", "gross: 350.50", "discount: 0.00", "net: 350.50"],
        )

    def test_report_top(self):
        run = run_report("A-1,C-1,100.00\nA-2,C-2,250.50\nA-3,C-3,90.00\n", "--top", "2")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.splitlines()[4:], ["A-2 250.50", "A-1 100.00"])


if __name__ == "__main__":
    unittest.main()
