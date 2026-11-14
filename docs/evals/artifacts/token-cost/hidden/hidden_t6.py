import unittest
from datetime import datetime, timedelta, timezone
from shop.schedule import is_overdue

class T6(unittest.TestCase):
    def test_aware_default_now(self):
        self.assertTrue(is_overdue(datetime.now(timezone.utc) - timedelta(days=1)))
        self.assertFalse(is_overdue(datetime.now(timezone.utc) + timedelta(days=1)))

    def test_naive_explicit_now(self):
        self.assertTrue(is_overdue(datetime(2026, 1, 1), now=datetime(2026, 6, 1)))
        self.assertFalse(is_overdue(datetime(2030, 1, 1), now=datetime(2026, 1, 1)))

    def test_naive_default_now(self):
        self.assertTrue(is_overdue(datetime.now() - timedelta(days=1)))
