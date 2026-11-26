"""Gate for 2.13.0: PLAIN vs FLOW_ASK only (40 runs), using score.py's loader."""
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import score
rows, problems = score.load(Path(sys.argv[1]))
problems = [p for p in problems if "-flow-" not in p]
agg = defaultdict(lambda: defaultdict(float))
for r in rows.values():
    a = agg[r["arm"]]
    for k in ("p1", "pf", "cost", "retry", "false_done"):
        a[k] += r[k]
    a["n"] += 1
    a.setdefault("turns", 0); a["turns"] += r["turns"]
for arm in ("plain", "flowask"):
    a = agg[arm]
    print(f"{arm}: n={int(a['n'])} P1={int(a['p1'])} PF={int(a['pf'])} retry={int(a['retry'])} false_done={int(a['false_done'])} "
          f"cost={a['cost']:.3f} per_fix={a['cost']/max(a['pf'],1):.3f} mean_turns={a['turns']/max(a['n'],1):.1f}")
pt = defaultdict(dict)
for r in rows.values():
    pt[r["task"]].setdefault(r["arm"], []).append(r["cost"])
for t in sorted(pt):
    p = sum(pt[t].get("plain", [0])) / max(len(pt[t].get("plain", [])), 1)
    f = sum(pt[t].get("flowask", [0])) / max(len(pt[t].get("flowask", [])), 1)
    print(f"{t}\tplain {p:.3f}\tflowask {f:.3f}\tratio {f/p if p else 0:.2f}")
ask = agg["flowask"]
per_fix = ask["cost"] / max(ask["pf"], 1)
gate = ask["n"] == 20 and agg["plain"]["n"] == 20 and not problems and ask["p1"] >= 19 and per_fix <= 0.337
print("problems:", problems or "none")
print("GATE:", "PASS" if gate else "FAIL", f"(FLOW_ASK P1 {int(ask['p1'])}/20, per fix {per_fix:.3f} vs limit 0.337)")
