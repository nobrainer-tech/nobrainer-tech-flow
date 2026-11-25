import hashlib
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEST_FILE = ROOT / "tests" / "test_couriers.py"
TEST_SHA256 = "a4e548e11923640a42becc6a2f15441a045efe0a8e90427f68fb2cec1ae15a03"

CHECK = r'''
import random, sys
from shop.couriers import assign

def expected(orders, couriers):
    remaining = {c["name"]: c["capacity"] for c in couriers}
    zones = {c["name"]: c["zones"] for c in couriers}
    out = {}
    for order in sorted(orders, key=lambda o: o["id"]):
        names = [n for n in sorted(remaining) if order["zone"] in zones[n] and remaining[n] >= order["weight"]]
        if not names:
            out[order["id"]] = None
            continue
        best = max(names, key=lambda n: (remaining[n], [-ord(ch) for ch in n]))
        remaining[best] -= order["weight"]
        out[order["id"]] = best
    return out

rng = random.Random(81)
cases = []
for _ in range(40):
    couriers = [{"name": n, "zones": sorted(rng.sample(["N", "S", "E"], rng.randint(1, 3))),
                 "capacity": rng.choice([6, 8, 10])} for n in ("ann", "ben", "cy", "dee", "eli")]
    orders = [{"id": f"R{i}", "zone": rng.choice(["N", "S", "E"]), "weight": rng.choice([2, 3, 4, 5])}
              for i in range(1, rng.randint(6, 10))]
    cases.append((orders, couriers))
# a pure tie: four identical couriers
cases.append(([{"id": "R1", "zone": "N", "weight": 1}],
              [{"name": n, "zones": ["N"], "capacity": 5} for n in ("dee", "cy", "ben", "ann")]))
for orders, couriers in cases:
    got = assign(orders, couriers)
    want = expected(orders, couriers)
    if got != want:
        print("MISMATCH", orders, couriers, got, want)
        sys.exit(1)
    shuffled = list(orders); rng.shuffle(shuffled)
    if assign(shuffled, list(reversed(couriers))) != want:
        print("ORDER DEPENDENT")
        sys.exit(1)
'''


def with_seed(seed, *argv):
    env = dict(os.environ, PYTHONHASHSEED=str(seed))
    return subprocess.run([sys.executable, *argv], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)


class FlakyTest(unittest.TestCase):
    def test_test_file_unchanged(self):
        self.assertEqual(hashlib.sha256(TEST_FILE.read_bytes()).hexdigest(), TEST_SHA256)

    def test_visible_test_passes_for_every_seed(self):
        failed = [s for s in range(50)
                  if with_seed(s, "-m", "unittest", "tests.test_couriers").returncode != 0]
        self.assertEqual(failed, [])

    def test_assignment_follows_the_rules_for_every_seed(self):
        for seed in range(50):
            result = with_seed(seed, "-c", CHECK)
            self.assertEqual(result.returncode, 0, f"seed {seed}: {result.stdout[-500:]}{result.stderr[-500:]}")


if __name__ == "__main__":
    unittest.main()
