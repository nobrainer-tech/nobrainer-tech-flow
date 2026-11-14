import unittest
from shop.listing import paginate

class T1(unittest.TestCase):
    def test_pages_cover_items_once(self):
        items = list(range(10))
        for size in (1, 3, 4, 10):
            pages, page = [], 1
            while True:
                chunk = paginate(items, page, size)
                if not chunk:
                    break
                pages += chunk
                page += 1
                self.assertLess(page, 20)
            self.assertEqual(pages, items, f"size={size}")

    def test_page_two(self):
        self.assertEqual(paginate(list(range(10)), 2, 4), [4, 5, 6, 7])
