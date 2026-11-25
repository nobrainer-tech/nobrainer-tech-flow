import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROWS = [
    ("K-01", "C-1", "120.00"),
    ("K-02", "C-2", "700.00"),
    ("K-03", "C-3", "45.50"),
    ("K-04", "C-4", "700.00"),
    ("K-05", "C-5", "1500.00"),
    ("K-06", "C-6", "700.00"),
    ("K-07", "C-7", "300.25"),
]


def write_csv(tmp, rows=ROWS):
    path = os.path.join(tmp, "orders.csv")
    with open(path, "w", newline="", encoding="utf-8") as handle:
        handle.write("order_id,customer,total\n")
        for row in rows:
            handle.write(",".join(row) + "\n")
    return path


def run_report(*args):
    return subprocess.run([sys.executable, "-m", "shop", "report", *args], cwd=ROOT, capture_output=True, text=True)


def section(text, heading):
    """Body of the `## heading` section of a markdown file (up to the next `## `)."""
    match = re.search(r"^## " + re.escape(heading) + r"[ \t]*$(.*?)(?=^## |\Z)", text, re.S | re.M)
    return match.group(1) if match else ""


def top_lines(stdout):
    lines = stdout.splitlines()
    index = max(i for i, line in enumerate(lines) if line.startswith("net:"))
    return lines[index + 1:]


class HiddenTest(unittest.TestCase):
    def assert_top(self, stdout, expected):
        lines = [line for line in top_lines(stdout) if re.search(r"\bK-\d\d\b", line)]
        self.assertEqual(len(lines), len(expected), stdout)
        # Largest first. The prompt sets no tie-break, so any orders with the cutoff total
        # are valid: check each line's own total, unique ids and the descending totals.
        known = {order_id: float(total) for order_id, _, total in ROWS}
        got = []
        for line in lines:
            order_id = re.search(r"\bK-\d\d\b", line).group(0)
            numbers = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", line.replace(order_id, ""))]
            self.assertIn(known[order_id], numbers, line)
            got.append((order_id, known[order_id]))
        self.assertEqual(len({i for i, _ in got}), len(got), stdout)
        self.assertEqual([t for _, t in got], [float(t) for _, t in expected], stdout)

    def test_top_three_with_ties(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = run_report(write_csv(tmp), "--top", "3")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assert_top(run.stdout, [("K-05", "1500.00"), ("K-02", "700.00"), ("K-04", "700.00")])

    def test_option_before_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = run_report("--top", "1", write_csv(tmp))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assert_top(run.stdout, [("K-05", "1500.00")])

    def test_n_larger_than_count_prints_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = run_report(write_csv(tmp), "--top", "50")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assert_top(run.stdout, [
            ("K-05", "1500.00"), ("K-02", "700.00"), ("K-04", "700.00"), ("K-06", "700.00"),
            ("K-07", "300.25"), ("K-01", "120.00"), ("K-03", "45.50"),
        ])

    def test_totals_come_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = run_report(write_csv(tmp), "--top", "2")
        self.assertEqual(run.stdout.splitlines()[:4], [
            "orders: 7", "gross: 4065.75", "discount: 255.00", "net: 3810.75"])

    def test_default_output_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = run_report(write_csv(tmp))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.splitlines(), [
            "orders: 7", "gross: 4065.75", "discount: 255.00", "net: 3810.75"])

    def test_readme_documents_top(self):
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as handle:
            body = section(handle.read(), "CLI")
        self.assertIn("--top", body)

    def test_changelog_unreleased_mentions_top(self):
        with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as handle:
            body = section(handle.read(), "Unreleased")
        self.assertTrue(any("--top" in line for line in body.splitlines()), body)

    def test_cli_test_covers_top(self):
        with open(os.path.join(ROOT, "tests", "test_cli.py"), encoding="utf-8") as handle:
            body = handle.read()
        self.assertIn("--top", body)
        self.assertIn("subprocess", body)


if __name__ == "__main__":
    unittest.main()
