"""Aggregate token-cost eval runs as defined in scoring.md.

Usage: python3 score.py EVAL_DIR/runs
Prints one row per run, per-task means and the primary result.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

KEYS = ("inputTokens", "cacheCreationInputTokens", "cacheReadInputTokens", "outputTokens")


def turn_numbers(turn):
    result = (turn or {}).get("result") or {}
    tokens = dict.fromkeys(KEYS, 0)
    for usage in (result.get("modelUsage") or {}).values():
        for key in KEYS:
            tokens[key] += usage.get(key) or 0
    return result.get("total_cost_usd") or 0.0, tokens, result.get("num_turns") or 0, (turn or {}).get("seconds") or 0


def load(runs_dir: Path):
    rows = []
    for path in sorted(runs_dir.glob("*/result.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        cost, tokens, turns, seconds = turn_numbers(data["turn1"])
        if data.get("turn2"):
            c2, t2, n2, s2 = turn_numbers(data["turn2"])
            cost += c2
            turns += n2
            seconds += s2
            tokens = {k: tokens[k] + t2[k] for k in KEYS}
        flow_loaded = any("nobrainer-tech-flow" in s for s in data["turn1"].get("skills", []))
        valid = flow_loaded == (data["arm"] == "flow")
        rows.append({**data, "cost": cost, "tokens": tokens, "turns": turns, "seconds": seconds, "valid": valid})
    return rows


def main() -> int:
    rows = load(Path(sys.argv[1]))
    print("run\tP1\tP2\tcost_usd\tinput\tcache_write\tcache_read\toutput\tturns\tseconds\tvalid")
    for r in rows:
        t = r["tokens"]
        print(f"{r['name']}\t{int(r['p1'])}\t{int(r['p2'])}\t{r['cost']:.4f}\t{t['inputTokens']}\t"
              f"{t['cacheCreationInputTokens']}\t{t['cacheReadInputTokens']}\t{t['outputTokens']}\t"
              f"{r['turns']}\t{r['seconds']:.0f}\t{int(r['valid'])}")
    rows = [r for r in rows if r["valid"]]
    per_task = defaultdict(lambda: defaultdict(list))
    for r in rows:
        per_task[r["task"]][r["arm"]].append(r["cost"])
    print("\ntask\tplain_mean\tflow_mean\tratio")
    for task in sorted(per_task):
        plain = per_task[task]["plain"]
        flow = per_task[task]["flow"]
        if plain and flow:
            pm, fm = sum(plain) / len(plain), sum(flow) / len(flow)
            print(f"{task}\t{pm:.4f}\t{fm:.4f}\t{fm / pm:.2f}")
    summary = {}
    for arm in ("plain", "flow"):
        mine = [r for r in rows if r["arm"] == arm]
        passed = sum(r["p2"] for r in mine)
        total = sum(r["cost"] for r in mine)
        tokens = {k: sum(r["tokens"][k] for r in mine) for k in KEYS}
        summary[arm] = {"runs": len(mine), "p1": sum(r["p1"] for r in mine), "p2": passed,
                        "cost": round(total, 4), "per_fix": round(total / passed, 4) if passed else None,
                        "tokens": tokens}
    print("\n" + json.dumps(summary, indent=1))
    plain, flow = summary["plain"], summary["flow"]
    if plain["per_fix"] and flow["per_fix"]:
        ratio = flow["per_fix"] / plain["per_fix"]
        if ratio <= 0.90 and flow["p2"] >= plain["p2"]:
            verdict = "FLOW_SAVES"
        elif ratio >= 1.10:
            verdict = "FLOW_COSTS_MORE"
        elif ratio < 1.10 and ratio > 0.90:
            verdict = "EVEN"
        else:
            verdict = "UNDECIDED (ratio <= 0.90 but fewer verified fixes)"
        print(f"RATIO={ratio:.3f} RESULT={verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
