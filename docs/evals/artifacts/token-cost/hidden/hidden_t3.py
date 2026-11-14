import json, subprocess, sys, unittest

def run(*args):
    return subprocess.run([sys.executable, "-m", "shop", "report", "data/orders.csv", *args],
                          capture_output=True, text=True, check=True).stdout

class T3(unittest.TestCase):
    def test_json_matches_text(self):
        text = dict(line.split(": ") for line in run().strip().splitlines())
        data = json.loads(run("--format", "json"))
        self.assertEqual(set(data), {"orders", "gross", "discount", "net"})
        self.assertEqual(int(data["orders"]), int(text["orders"]))
        for key in ("gross", "discount", "net"):
            self.assertAlmostEqual(float(data[key]), float(text[key]), places=2)

    def test_text_is_default(self):
        self.assertEqual(run(), run("--format", "text"))
