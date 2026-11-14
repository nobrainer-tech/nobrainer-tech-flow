"""Aggregate token-cost eval runs as defined in scoring.md.

Usage: python3 score.py EVAL_DIR/runs [BASE,CANDIDATE] [--tasks T1,...] [--repeats N]
Defaults: plain,flow; tasks T1-T6; 2 repeats. Hard tasks: --tasks H1,H2,H3,H4,H5 --repeats 3.
Prints one row per run, per-task means and the primary result.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

KEYS = ("inputTokens", "cacheCreationInputTokens", "cacheReadInputTokens", "outputTokens")
TASKS = ("T1", "T2", "T3", "T4", "T5", "T6")
REPEATS = (1, 2)


def turn_numbers(turn):
    result = (turn or {}).get("result") or {}
    tokens = dict.fromkeys(KEYS, 0)
    for usage in (result.get("modelUsage") or {}).values():
        for key in KEYS:
            tokens[key] += usage.get(key) or 0
    complete = result.get("total_cost_usd") is not None and bool(result.get("modelUsage"))
    numbers = (result.get("total_cost_usd") or 0.0, tokens, result.get("num_turns") or 0, (turn or {}).get("seconds") or 0)
    return numbers, complete


def load(runs_dir: Path):
    rows = []
    for path in sorted(runs_dir.glob("*/result.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        all_turns = data.get("turns") or [t for t in (data["turn1"], data.get("turn2")) if t]
        cost, tokens, turns, seconds, complete = 0.0, dict.fromkeys(KEYS, 0), 0, 0, True
        for turn in all_turns:
            (c, t, n, sec), ok = turn_numbers(turn)
            cost, turns, seconds, complete = cost + c, turns + n, seconds + sec, complete and ok
            tokens = {k: tokens[k] + t[k] for k in KEYS}
        flow_loaded = any("nobrainer-tech-flow" in s for s in data["turn1"].get("skills", []))
        # A run without the final cost telemetry is an incomplete measurement, not a free fix.
        valid = complete and flow_loaded == (data["arm"] in ("flow", "slim"))
        if data["arm"] == "lean":
            valid = valid and (path.parent / "repo" / "CLAUDE.md").exists()
        if data["arm"] == "slim":
            entry = path.parent / "repo" / ".claude" / "skills" / "nobrainer-tech-flow" / "SKILL.md"
            valid = valid and "delegate only where it helps" in entry.read_text(encoding="utf-8")
        data = {k: v for k, v in data.items() if k != "turns"}
        rows.append({**data, "cost": cost, "tokens": tokens, "turns": turns, "seconds": seconds,
                     "retries": len(all_turns) - 1, "valid": valid})
    return rows


def main() -> int:
    args = sys.argv[1:]
    tasks, repeats = TASKS, REPEATS
    if "--tasks" in args:
        i = args.index("--tasks")
        tasks = tuple(args[i + 1].split(","))
        del args[i:i + 2]
    if "--repeats" in args:
        i = args.index("--repeats")
        repeats = tuple(range(1, int(args[i + 1]) + 1))
        del args[i:i + 2]
    base, cand = (args[1] if len(args) > 1 else "plain,flow").split(",")
    rows = [r for r in load(Path(args[0])) if r["arm"] in (base, cand)]
    print("run\tP1\tP2\tcost_usd\tinput\tcache_write\tcache_read\toutput\tturns\tseconds\tvalid\tretries")
    for r in rows:
        t = r["tokens"]
        print(f"{r['name']}\t{int(r['p1'])}\t{int(r['p2'])}\t{r['cost']:.4f}\t{t['inputTokens']}\t"
              f"{t['cacheCreationInputTokens']}\t{t['cacheReadInputTokens']}\t{t['outputTokens']}\t"
              f"{r['turns']}\t{r['seconds']:.0f}\t{int(r['valid'])}\t{r['retries']}")
    rows = [r for r in rows if r["valid"]]
    per_task = defaultdict(lambda: defaultdict(list))
    for r in rows:
        per_task[r["task"]][r["arm"]].append(r["cost"])
    print(f"\ntask\t{base}_mean\t{cand}_mean\tratio")
    for task in sorted(per_task):
        plain = per_task[task][base]
        flow = per_task[task][cand]
        if plain and flow:
            pm, fm = sum(plain) / len(plain), sum(flow) / len(flow)
            print(f"{task}\t{pm:.4f}\t{fm:.4f}\t{fm / pm:.2f}")
    summary = {}
    for arm in (base, cand):
        mine = [r for r in rows if r["arm"] == arm]
        passed = sum(r["p2"] for r in mine)
        total = sum(r["cost"] for r in mine)
        tokens = {k: sum(r["tokens"][k] for r in mine) for k in KEYS}
        summary[arm] = {"runs": len(mine), "p1": sum(r["p1"] for r in mine), "p2": passed,
                        "retries": sum(r["retries"] for r in mine),
                        "cost": round(total, 4), "per_fix": round(total / passed, 4) if passed else None,
                        "tokens": tokens}
    print("\n" + json.dumps(summary, indent=1))
    expected = {(t, a, rep) for t in tasks for a in (base, cand) for rep in repeats}
    missing = sorted(expected - {(r["task"], r["arm"], r["rep"]) for r in rows})
    if missing:
        names = ", ".join(f"{t}-{a}-{rep}" for t, a, rep in missing)
        print(f"RESULT=INCOMPLETE (rerun missing or invalid runs: {names})")
        return 1
    plain, flow = summary[base], summary[cand]
    if plain["per_fix"] and flow["per_fix"]:
        ratio = flow["per_fix"] / plain["per_fix"]
        if ratio <= 0.90 and flow["p2"] >= plain["p2"]:
            verdict = f"{cand.upper()}_SAVES"
        elif ratio >= 1.10:
            verdict = f"{cand.upper()}_COSTS_MORE"
        elif ratio < 1.10 and ratio > 0.90:
            verdict = "EVEN"
        else:
            verdict = "UNDECIDED (ratio <= 0.90 but fewer verified fixes)"
        print(f"RATIO={ratio:.3f} RESULT={verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
