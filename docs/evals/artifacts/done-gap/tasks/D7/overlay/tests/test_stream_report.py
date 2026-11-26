import os
import tempfile
import unittest

from shop import stream_report
from shop.report import summarize_rows


class StreamReportTest(unittest.TestCase):
    def test_matches_in_memory_summary(self):
        text = "order_id,customer,total,status\nO-1,C-1,120.00,paid\nO-2,C-2,640.50,shipped\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "orders.csv")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
            rows = [{"total": "120.00", "status": "paid"}, {"total": "640.50", "status": "shipped"}]
            self.assertEqual(stream_report.summarize_path(path), summarize_rows(rows))


if __name__ == "__main__":
    unittest.main()
