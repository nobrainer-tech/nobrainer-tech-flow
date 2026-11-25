import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "data" / "store"
BROKEN = "0000-import-damaged.json"


def run(directory):
    return subprocess.run([sys.executable, "-m", "shop", "migrate", str(directory)], cwd=ROOT,
                          capture_output=True, text=True, timeout=120)


def snapshot(directory):
    return {p.name: p.read_bytes() for p in sorted(Path(directory).iterdir())}


class MigrateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.store = self.tmp / "store"
        shutil.copytree(STORE, self.store)
        self.orig = snapshot(self.store)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_v1_files_become_valid_v2(self):
        run(self.store)
        count = 0
        for name, raw in self.orig.items():
            old = json.loads(raw) if name != BROKEN else None
            if old is None or old.get("schema") == 2:
                continue
            new = json.loads((self.store / name).read_text(encoding="utf-8"))
            count += 1
            self.assertEqual(new["schema"], 2, name)
            self.assertEqual(new["order_id"], old["order_id"])
            self.assertEqual(new["status"], old["status"])
            self.assertEqual(new["currency"], "PLN")
            self.assertIsInstance(new["gross"], str)
            self.assertRegex(new["gross"], r"^\d+\.\d{2}$", name)
            self.assertEqual(Decimal(new["gross"]), Decimal(str(old["total"])), name)
            self.assertNotIn("total", new)
            self.assertEqual(new["history"], [{"event": "migrated_v2"}], name)
        self.assertEqual(count, 12)

    def test_second_run_changes_nothing(self):
        run(self.store)
        after_one = snapshot(self.store)
        run(self.store)
        self.assertEqual(snapshot(self.store), after_one)

    def test_already_v2_files_untouched(self):
        run(self.store)
        for name in ("O-0013.json", "O-0014.json"):
            self.assertEqual((self.store / name).read_bytes(), self.orig[name])

    def test_broken_file_reported_and_untouched(self):
        for _ in range(2):
            result = run(self.store)
            self.assertIn(BROKEN, result.stderr)
            self.assertEqual((self.store / BROKEN).read_bytes(), self.orig[BROKEN])

    def test_rerun_reports_no_new_problems(self):
        # Progress lines on stderr are allowed; a rerun must not name files the first run did not.
        named = []
        for _ in range(2):
            result = run(self.store)
            named.append({n for n in self.orig if n in result.stderr})
        self.assertLessEqual(named[1], named[0], "second run names files the first did not")

    def test_others_migrated_although_broken_sorts_first(self):
        self.assertEqual(sorted(self.orig)[0], BROKEN)
        run(self.store)
        for i in range(1, 13):
            data = json.loads((self.store / f"O-{i:04d}.json").read_text(encoding="utf-8"))
            self.assertEqual(data["schema"], 2, i)


if __name__ == "__main__":
    unittest.main()
