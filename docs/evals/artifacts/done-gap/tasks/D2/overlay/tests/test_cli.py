import os
import subprocess
import sys
import tempfile
import unittest


class CliTest(unittest.TestCase):
    def test_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "orders.csv")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("order_id,customer,total\nA-1,C-1,100.00\nA-2,C-2,250.50\n")
            run = subprocess.run([sys.executable, "-m", "shop", "report", path], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(
            run.stdout.splitlines(),
            ["orders: 2", "gross: 350.50", "discount: 0.00", "net: 350.50"],
        )


if __name__ == "__main__":
    unittest.main()
