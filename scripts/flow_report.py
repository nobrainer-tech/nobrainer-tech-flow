#!/usr/bin/env python3
"""Build the Flow quality, reliability, speed and cost report from repository data.

Offline and deterministic: the report uses no clock and no network. It reads the
checkout, `docs/reports/data/*.json` and git history. Anything the repository
cannot show is reported as `NOT_RUN`, never estimated.

    python3 scripts/flow_report.py              # print the report
    python3 scripts/flow_report.py --write      # refresh docs/reports/flow-quality-report.md
    python3 scripts/flow_report.py --check      # fail when the committed report is stale
    python3 scripts/flow_report.py --run-tests  # also run the full suite and record the result
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import platform
import re
import statistics
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs" / "reports" / "data"
REPORT = ROOT / "docs" / "reports" / "flow-quality-report.md"
BYTES_PER_TOKEN = 4  # rough heuristic for English text; an estimate, not billing


def read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def git(*args: str) -> str:
    out = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else ""


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.1f}%" if whole else "n/a"


def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(q * (len(ordered) - 1)))]


def minutes(seconds: float) -> str:
    return f"{seconds / 60:.1f} min"


# --- quality ---------------------------------------------------------------

def validators() -> dict:
    result = {}
    for flag in ([], ["--suite"]):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "validate_skills.py"), *flag],
                              capture_output=True, text=True, cwd=ROOT)
        result["suite" if flag else "skills"] = proc.returncode == 0
    return result


def test_inventory() -> dict:
    """Count test methods the way unittest discovery does: one per (file, class, name).

    A method name defined twice in one class is shadowed by the later definition and never runs,
    so it is counted once.
    """
    files = sorted((ROOT / "tests").glob("test_*.py"))
    cases: set[tuple[str, str, str]] = set()
    for path in files:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef):
                cases.update((path.name, node.name, n.name) for n in node.body
                             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test"))
    return {"files": len(files), "defined_cases": len(cases)}


def eval_records() -> dict:
    return {
        "eval_records": len(list((ROOT / "docs" / "evals").glob("*.md"))),
        "release_records": len([p for p in (ROOT / "docs" / "releases").glob("v*.md")
                                if re.fullmatch(r"v\d+\.\d+\.\d+\.md", p.name)]),
    }


# --- reliability and speed -------------------------------------------------

def ci_stats(snapshot: dict | None) -> dict | None:
    if not snapshot:
        return None

    def group(runs: list[dict]) -> dict:
        done = [r for r in runs if r["conclusion"] in ("success", "failure")]
        ok = [r for r in done if r["conclusion"] == "success"]
        cancelled = sum(r["conclusion"] == "cancelled" for r in runs)
        seconds = [(parse_time(r["updated_at"]) - parse_time(r["started_at"])).total_seconds() for r in ok]
        return {
            "runs": len(runs), "success": len(ok), "failure": len(done) - len(ok), "cancelled": cancelled,
            "pass_rate": pct(len(ok), len(done)),
            "median_s": statistics.median(seconds) if seconds else None,
            "p90_s": percentile(seconds, 0.9) if seconds else None,
        }

    runs = snapshot["runs"]
    by_month: dict[str, list[float]] = {}
    for r in runs:
        if r["conclusion"] == "success":
            by_month.setdefault(r["started_at"][:7], []).append(
                (parse_time(r["updated_at"]) - parse_time(r["started_at"])).total_seconds())
    main_push = [r for r in runs if r["event"] == "push" and r["branch"] == "main"]
    pull_request = [r for r in runs if r["event"] == "pull_request"]
    other = [r for r in runs if r not in main_push and r not in pull_request]
    return {
        "monthly": {m: (len(v), statistics.median(v), percentile(v, 0.9)) for m, v in sorted(by_month.items())},
        "all": group(runs),
        "main_push": group(main_push),
        "pull_request": group(pull_request),
        "other": group(other),
        "other_events": sorted({r["event"] for r in other}),
        "captured_at": snapshot["captured_at"],
        "complete": snapshot.get("complete", False),
    }


def release_cadence() -> dict | None:
    """Stable version tags per month; `None` in a shallow clone, where tags and dates are unreliable."""
    if git("rev-parse", "--is-shallow-repository") != "false":
        return None
    months: dict[str, int] = {}
    for line in git("for-each-ref", "--format=%(refname:short) %(creatordate:short)", "refs/tags").splitlines():
        tag, _, day = line.partition(" ")
        if re.fullmatch(r"v\d+\.\d+\.\d+", tag):
            months[day[:7]] = months.get(day[:7], 0) + 1
    return {"releases": sum(months.values()), "months": dict(sorted(months.items()))} if months else None


def workflow_change_dates() -> list[str] | None:
    """Days on which the CI workflow file changed; `None` in a shallow clone, where history is partial."""
    if git("rev-parse", "--is-shallow-repository") != "false":
        return None
    days = git("log", "--format=%ad", "--date=short", "--", ".github/workflows/validate.yml").splitlines()
    return sorted(set(days)) or None


def run_suite() -> dict:
    start = time.monotonic()
    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                          capture_output=True, text=True, cwd=ROOT)
    tail = proc.stderr.strip().splitlines()[-3:]
    ran = re.search(r"Ran (\d+) tests? in ([\d.]+)s", proc.stderr)
    counts = dict(re.findall(r"(failures|errors|skipped)=(\d+)", proc.stderr))
    return {
        "schema": "nobrainer-flow-test-run/1",
        "exit_code": proc.returncode,
        "tests": int(ran.group(1)) if ran else None,
        "seconds": float(ran.group(2)) if ran else round(time.monotonic() - start, 1),
        "failures": int(counts.get("failures", 0)), "errors": int(counts.get("errors", 0)),
        "skipped": int(counts.get("skipped", 0)),
        "failed_tests": sorted({f"{mod}.{name}" for name, mod in re.findall(r"^(?:FAIL|ERROR): (\S+) \(([\w.]+)", proc.stderr, re.M)}),
        "summary": tail[-1] if tail else "",
        "python": platform.python_version(), "system": platform.system(),
        "cpus": os.cpu_count(),
        "commit": git("rev-parse", "HEAD"),
        "note": "One run on one machine. Wall time depends on load; the suite runs a recursive archive acceptance test.",
    }


# --- cost ------------------------------------------------------------------

def skill_files(skill_dir: Path) -> list[Path]:
    """Files a skill ships: the tracked ones when git knows them, else everything but bytecode caches.

    A plain directory walk would also count `__pycache__` and other untracked files that a local
    test run leaves behind, so the same commit would report different sizes on different machines.
    """
    tracked = [ROOT / p for p in git("ls-files", "--", skill_dir.relative_to(ROOT).as_posix()).splitlines()]
    if tracked:
        return [p for p in tracked if p.is_file()]
    return [p for p in skill_dir.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]


def footprint() -> dict:
    skills = []
    for skill in sorted((ROOT / "skills").glob("*/SKILL.md")):
        text = skill.read_text(encoding="utf-8")
        desc = re.search(r'^description:\s*"(.*)"\s*$', text, re.M)
        refs = sum(p.stat().st_size for p in skill_files(skill.parent) if p != skill)
        skills.append({"name": skill.parent.name, "skill_md": len(text.encode()), "description": len((desc.group(1) if desc else "").encode()),
                       "on_demand_files": refs})
    bootstrap = (ROOT / "adapters" / "bootstrap.md").stat().st_size
    always = bootstrap + sum(s["description"] for s in skills)
    return {"skills": skills, "bootstrap": bootstrap, "always_visible_bytes": always,
            "largest": max(skills, key=lambda s: s["skill_md"])}


def tokens(n: int) -> str:
    return f"~{round(n / BYTES_PER_TOKEN):,}"


# --- ledger ----------------------------------------------------------------

def check_ledger() -> list[dict]:
    ledger = read_json(DATA / "evidence-ledger.json") or {"entries": []}
    rows = []
    for entry in ledger["entries"]:
        path = ROOT / entry["source"]
        text = " ".join(path.read_text(encoding="utf-8").split()) if path.exists() else ""
        quotes = entry["quote"] if isinstance(entry["quote"], list) else [entry["quote"]]
        rows.append({**entry, "verified": bool(quotes) and all(" ".join(q.split()) in text for q in quotes)})
    return rows


# --- render ----------------------------------------------------------------

def render(include_tests: dict | None) -> tuple[str, bool]:
    pkg = read_json(ROOT / "package.json") or {}
    val, inv, evals = validators(), test_inventory(), eval_records()
    ci = ci_stats(read_json(DATA / "ci-validate-runs.json"))
    cadence, foot, ledger = release_cadence(), footprint(), check_ledger()
    workflow_days = workflow_change_dates()
    tests = include_tests or read_json(DATA / "test-run.json")
    problems = [e["id"] for e in ledger if not e["verified"]] + [k for k, v in val.items() if not v]
    L: list[str] = []
    add = L.append

    add(f"# Flow quality, reliability, speed and cost report")
    add("")
    add(f"Flow version `{pkg.get('version', 'unknown')}`. Generated by `python3 scripts/flow_report.py --write` from repository data only. "
        "The script calls no model and uses no network, so regenerating the report costs only a local run.")
    add("")
    add("## What this report can and cannot say")
    add("")
    add("It measures **Flow as a piece of software and a body of instructions**: do its gates pass, how stable is its CI, how fast is its "
        "pipeline, and how much context does it add. It does **not** yet measure **Flow as a way of working**: whether an agent using Flow "
        "finishes real tasks better, faster or cheaper than the same agent without it. That needs paid, repeated, paired model runs, "
        "planned in [paid-run-plan.md](paid-run-plan.md) and not yet approved or run. Until then no claim about task quality, speed or "
        "cost savings is made, in line with the release records.")
    add("")
    add("Each metric on the scoreboard carries a status: `MEASURED`, `PARTIAL` (a real number with a stated limit) or `NOT_RUN`. "
        "Figures quoted from earlier records are listed in the evidence ledger at the end, and the script re-checks each quote against its source.")
    add("")
    add("## Scoreboard")
    add("")
    add("| Metric | Definition | Status | Headline |")
    add("|---|---|---|---|")
    add(f"| Quality | Whether Flow's own gates hold, plus recorded behavior evaluations | PARTIAL | validators {'pass' if all(val.values()) else 'FAIL'}; "
        f"{inv['defined_cases']:,} test cases in {inv['files']} files; installer mutation catch 30 of 34; behavior evaluations quoted below: one measured promotion (3 paired repetitions), one rejected (1.6.1) |")
    if ci:
        a, m = ci["all"], ci["main_push"]
        add(f"| Reliability | CI pass rate of the `Validate` workflow, cancelled runs excluded | PARTIAL | {a['pass_rate']} of {a['success'] + a['failure']} finished runs "
            f"(`main` pushes {m['pass_rate']} of {m['success'] + m['failure']}) |")
        add(f"| Speed | Wall time of a green `Validate` run, and version tags per month | PARTIAL | latest month median {minutes(list(ci['monthly'].values())[-1][1])}, p90 {minutes(list(ci['monthly'].values())[-1][2])}"
            + (f"; {cadence['releases']} version tags" if cadence else "") + " |")
    else:
        add("| Reliability | CI pass rate | NOT_RUN | no CI snapshot in `docs/reports/data/` |")
        add("| Speed | CI wall time | NOT_RUN | no CI snapshot |")
    add(f"| Cost | Context Flow adds before any work starts, and recorded token receipts | PARTIAL | {tokens(foot['always_visible_bytes'])} tokens shipped for every session (estimate); no dollars-per-task figure |")
    add("")
    add("## Quality")
    add("")
    add(f"- Structure validators (`validate_skills.py`, `--suite`): {'pass' if all(val.values()) else '**FAIL**'} on this checkout.")
    add(f"- Test suite: {inv['defined_cases']:,} test cases defined across {inv['files']} files (counted statically, one per class and method name, which is how unittest discovery counts them; the run result is under Reliability).")
    add(f"- Records: {evals['release_records']} release records and {evals['eval_records']} evaluation records in `docs/`.")
    for e in ledger:
        if e["metric"] == "quality" and e.get("display", True):
            add(f"- {e['claim']} ([{e['source']}](../../{e['source']}))")
    add("- **Not measured:** whether work done with Flow is more correct, more complete or better verified than work done without it.")
    add("")
    add("## Reliability")
    add("")
    if ci:
        add(f"CI snapshot of the `Validate` workflow, captured {ci['captured_at'][:10]} from the GitHub Actions API"
            f"{'' if ci['complete'] else ' (incomplete)'}. Pass rate = success / (success + failure); cancelled runs are listed apart.")
        add("")
        add("| Scope | Runs | Success | Failure | Cancelled | Pass rate |")
        add("|---|---|---|---|---|---|")
        rows = [("All", "all"), ("Pushes to `main`", "main_push"), ("Pull requests", "pull_request")]
        if ci["other"]["runs"]:
            rows.append((f"Other ({', '.join(f'`{e}`' for e in ci['other_events'])})", "other"))
        for label, key in rows:
            g = ci[key]
            add(f"| {label} | {g['runs']} | {g['success']} | {g['failure']} | {g['cancelled']} | {g['pass_rate']} |")
        add("")
        add("A failed run on a pull-request branch can be the gate catching a problem before merge, so the pull-request rate is not a defect rate; "
            "the snapshot does not record why a run failed. The `main` row covers runs after merge. The snapshot keeps only the final attempt of each run.")
    else:
        add("`NOT_RUN`: no CI snapshot is stored.")
    add("")
    if tests:
        add(f"Local full suite (`{tests['system']}`, Python {tests['python']}, {tests.get('cpus', '?')} CPUs): **{tests['tests']} tests, exit {tests['exit_code']}** "
            f"({tests['failures']} failures, {tests['errors']} errors, {tests['skipped']} skipped) in {tests['seconds']:.0f} s on commit `{tests['commit'][:10]}`; "
            f"the report files were regenerated after the run. {tests['note']}")
    else:
        add("Local full suite: `NOT_RUN` for this report. Run `python3 scripts/flow_report.py --run-tests` to record it.")
    add("")
    for e in ledger:
        if e["metric"] == "reliability":
            add(f"- {e['claim']} ([{e['source']}](../../{e['source']}))")
    add("- **Not measured:** how often an agent following Flow completes a task correctly across repeated runs. Single runs do not estimate it.")
    add("")
    add("## Speed")
    add("")
    if ci:
        add("Green `Validate` runs, start to last update of the whole workflow run (every job of the workflow, on Linux, macOS and Windows runners). "
            "The workflow file and the suite changed over this period"
            + (f" (the workflow file changed on {', '.join(workflow_days)})" if workflow_days else " (see `git log` for `.github/workflows/validate.yml`)")
            + ", and this report does not attribute the differences to any change, so compare within a month only. p90 is a nearest-rank estimate.")
        add("")
        add("| Month | Green runs | Median | p90 |")
        add("|---|---|---|---|")
        for month, (n, med, p90) in ci["monthly"].items():
            add(f"| {month} | {n} | {minutes(med)} | {minutes(p90)} |")
    if cadence:
        add("")
        add(f"Stable version tags per month: "
            + ", ".join(f"{m}: {n}" for m, n in cadence["months"].items())
            + f" ({cadence['releases']} in total). The date is the tag date for an annotated tag and the commit date for a lightweight tag.")
        add("")
    for e in ledger:
        if e["metric"] == "speed":
            add(f"- {e['claim']} ([{e['source']}](../../{e['source']}))")
    add("- **Not measured:** time from request to verified delivery with and without Flow, or any gain from delegation.")
    add("")
    add("## Cost")
    add("")
    add(f"Flow's standing cost is context. Sizes below are bytes of text; tokens are bytes divided by {BYTES_PER_TOKEN}, a rough English-text heuristic, **not** a tokenizer count or a bill.")
    add("")
    add(f"- Shipped for every session: the session bootstrap ({foot['bootstrap']:,} B) plus the {len(foot['skills'])} skill descriptions ({sum(s['description'] for s in foot['skills']):,} B) = "
        f"{foot['always_visible_bytes']:,} B, {tokens(foot['always_visible_bytes'])} tokens. This is visible at session start only on hosts that inject the bootstrap and list skill descriptions "
        "(observed on Claude Code and Codex in [docs/COMPATIBILITY.md](../../docs/COMPATIBILITY.md)); a host may shorten descriptions, so this is the size Flow ships, not a measure of what any host shows.")
    add(f"- Loaded when a skill triggers: `SKILL.md` per skill, from {min(s['skill_md'] for s in foot['skills']):,} B to {foot['largest']['skill_md']:,} B (`{foot['largest']['name']}`), "
        f"{tokens(sum(s['skill_md'] for s in foot['skills']))} tokens if all {len(foot['skills'])} loaded at once, an upper bound rather than expected use. Reference files load on demand; "
        "the last column counts the files git tracks in each skill directory.")
    add("")
    add("| Skill | `SKILL.md` (B) | Description (B) | On-demand files (B) |")
    add("|---|---|---|---|")
    for s in sorted(foot["skills"], key=lambda s: -s["skill_md"]):
        add(f"| `{s['name']}` | {s['skill_md']:,} | {s['description']:,} | {s['on_demand_files']:,} |")
    add("")
    for e in ledger:
        if e["metric"] == "cost":
            add(f"- {e['claim']} ([{e['source']}](../../{e['source']}))")
    add("- **Not measured:** tokens or dollars per finished task, with or without Flow, and how much delegation changes either.")
    add("")
    add("## Evidence ledger")
    add("")
    add("Each figure quoted above is copied from an existing record. The script re-checks that the quote is still in its source.")
    add("")
    add("| Entry | Metric | Source | Quote still present |")
    add("|---|---|---|---|")
    for e in ledger:
        add(f"| `{e['id']}` | {e['metric']} | `{e['source']}` | {'yes' if e['verified'] else '**NO**'} |")
    add("")
    add("## Reproduce")
    add("")
    add("```bash")
    add("python3 scripts/flow_report.py --check     # fail if this file is stale")
    add("python3 scripts/flow_report.py --write     # regenerate it")
    add("python3 scripts/flow_report.py --run-tests --write   # also re-run the full suite ("
        + (f"the recorded run took about {tests['seconds'] / 60:.0f} minutes" if tests else "expect over ten minutes") + ")")
    add("```")
    add("")
    add("The CI snapshot is stored in `docs/reports/data/ci-validate-runs.json` and has to be refreshed from the GitHub Actions API by hand; the script never touches the network.")
    return "\n".join(L) + "\n", not problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="write docs/reports/flow-quality-report.md")
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed report differs from a fresh render")
    ap.add_argument("--run-tests", action="store_true", help="run the full suite and record docs/reports/data/test-run.json")
    args = ap.parse_args()

    tests = None
    if args.run_tests:
        tests = run_suite()
        DATA.mkdir(parents=True, exist_ok=True)
        (DATA / "test-run.json").write_text(json.dumps(tests, indent=1) + "\n", encoding="utf-8")
    text, ok = render(tests)
    if args.check:
        current = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
        if current != text:
            print("STALE: docs/reports/flow-quality-report.md differs from a fresh render", file=sys.stderr)
            return 1
        print("OK: report is current" if ok else "report is current but a gate or ledger quote failed", file=sys.stderr)
        return 0 if ok else 1
    if args.write:
        REPORT.write_text(text, encoding="utf-8")
        print(f"wrote {REPORT.relative_to(ROOT)}")
    else:
        sys.stdout.write(text)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
