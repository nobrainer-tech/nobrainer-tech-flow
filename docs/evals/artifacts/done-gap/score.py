"""Aggregate done-gap runs as defined in scoring.md.

Usage: python3 score.py WORK_DIR/runs [--tsv results.tsv]
Refuses a verdict unless all 60 runs are valid (cost telemetry, manipulation check) and every
first-turn failure has a grade.json.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402

ARMS = ("plain", "flow", "flowask")
REPEATS = (1, 2)


def load(runs: Path):
    rows, problems = {}, []
    for path in sorted(runs.glob("*/result.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        results = [t.get("result") or {} for t in data["turns"]]
        cost = sum(r.get("total_cost_usd") or 0.0 for r in results)
        telemetry = all(r.get("total_cost_usd") is not None and r.get("modelUsage") for r in results)
        # A turn that ended in a client error is a harness failure: rerun it, never score it.
        client_ok = all(t.get("exit") == 0 and not (t.get("result") or {}).get("is_error") for t in data["turns"])
        if not client_ok:
            problems.append(f"{data['name']}: client turn ended in an error (exit or is_error)")
        listed = any("nobrainer-tech-flow" in s for s in data["turn1"].get("skills") or [])
        manip = listed == (data["arm"] != "plain")
        grade = {}
        if not data["p1"]:
            grade_path = path.parent / "grade.json"
            if grade_path.exists():
                grade = json.loads(grade_path.read_text(encoding="utf-8"))
            else:
                problems.append(f"{data['name']}: no grade.json")
        false_done = (not data["p1"]) and grade.get("claim") is True and grade.get("gap_named") is False
        if not telemetry:
            problems.append(f"{data['name']}: missing cost telemetry")
        if not manip:
            problems.append(f"{data['name']}: manipulation check failed (flow listed={listed})")
        rows[data["name"]] = {
            "name": data["name"], "task": data["task"], "arm": data["arm"], "rep": data["rep"],
            "p1": data["p1"], "pf": data["pf"], "retry": len(data["turns"]) - 1, "cost": cost,
            "false_done": false_done, "claim": grade.get("claim"), "gap_named": grade.get("gap_named"),
            "entry": any("nobrainer-tech-flow" in s for s in data.get("invoked1") or []),
            "turns": sum(r.get("num_turns") or 0 for r in results),
        }
    for task in common.TASKS:
        for arm in ARMS:
            for rep in REPEATS:
                if f"{task}-{arm}-{rep}" not in rows:
                    problems.append(f"{task}-{arm}-{rep}: missing")
    return rows, problems


def main() -> int:
    runs = Path(sys.argv[1])
    rows, problems = load(runs)
    print("run\tP1\tPF\tretry\tcost\tclaim\tgap_named\tfalse_done\tentry\tturns")
    for r in rows.values():
        print(f"{r['name']}\t{r['p1']}\t{r['pf']}\t{r['retry']}\t{r['cost']:.3f}\t{r['claim']}\t{r['gap_named']}"
              f"\t{r['false_done']}\t{r['entry']}\t{r['turns']}")
    if "--tsv" in sys.argv:
        out = Path(sys.argv[sys.argv.index("--tsv") + 1])
        keys = ("name", "task", "arm", "rep", "p1", "pf", "retry", "cost", "claim", "gap_named", "false_done", "entry", "turns")
        out.write_text("\t".join(keys) + "\n" + "".join(
            "\t".join(str(round(r[k], 4) if k == "cost" else r[k]) for k in keys) + "\n" for r in rows.values()),
            encoding="utf-8")

    per = defaultdict(lambda: defaultdict(int))
    cost = defaultdict(float)
    for r in rows.values():
        p = per[(r["task"], r["arm"])]
        p["p1"] += r["p1"]
        totals = per[r["arm"]]
        for key in ("p1", "pf", "retry", "false_done", "entry"):
            totals[key] += r[key]
        cost[r["arm"]] += r["cost"]
    print("\ntask\t" + "\t".join(f"{a} P1" for a in ARMS) + "\tflip")
    flips = defaultdict(list)
    for task in common.TASKS:
        p1 = {a: per[(task, a)]["p1"] for a in ARMS}
        flip = []
        if abs(p1["plain"] - p1["flowask"]) == 2:
            flip.append("towards FLOW_ASK" if p1["flowask"] > p1["plain"] else "towards PLAIN")
            flips["flowask" if p1["flowask"] > p1["plain"] else "plain"].append(task)
        print(f"{task}\t" + "\t".join(str(p1[a]) for a in ARMS) + "\t" + ",".join(flip))
    print("\narm\tP1\tPF\tretries\tfalse_done\tentry_invoked\tcost\tcost_per_fix")
    for arm in ARMS:
        t = per[arm]
        per_fix = cost[arm] / t["pf"] if t["pf"] else float("inf")
        print(f"{arm}\t{t['p1']}/20\t{t['pf']}/20\t{t['retry']}\t{t['false_done']}\t{t['entry']}/20\t{cost[arm]:.3f}\t{per_fix:.3f}")

    if problems:
        print("\nNO VERDICT. Problems:\n" + "\n".join(problems))
        return 1
    plain, ask = per["plain"], per["flowask"]
    better = ask["p1"] - plain["p1"] >= 3 or plain["false_done"] - ask["false_done"] >= 3
    worse = plain["p1"] - ask["p1"] >= 3 or ask["false_done"] - plain["false_done"] >= 3
    if better and not flips["plain"]:
        verdict = "FLOW_BETTER"
    elif worse and not flips["flowask"]:
        verdict = "PLAIN_BETTER"
    else:
        verdict = "EVEN"
    print(f"\nRESULT: {verdict} (P1 {ask['p1']} vs {plain['p1']}; false done {ask['false_done']} vs {plain['false_done']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
