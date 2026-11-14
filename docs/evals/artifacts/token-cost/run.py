"""Run the token-cost eval: PLAIN vs FLOW on six tasks, two repeats, one retry turn.

Usage: python3 run.py EVAL_DIR FLOW_CHECKOUT  (EVAL_DIR/skills.tar = git archive <commit> skills) [--only T1-plain-1,...] [--workers 4]
Writes EVAL_DIR/runs/<task>-<arm>-<rep>/{turn1.jsonl,turn2.jsonl,check*.txt,result.json}.
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

PROMPTS = {
    "T1": "Customers say page 2 of the order list repeats the last order from page 1. Fix the paging in this repo.",
    "T2": "Last night's supplier import failed. The log is logs/import-2026-11-13.log (about 2500 lines). Find the cause and fix it so the import works.",
    "T3": "Add a `--format json` option to `python3 -m shop report` that prints the same totals as JSON. Text stays the default.",
    "T4": "A customer's order was cancelled and still got shipped. Make sure an order can never end up both cancelled and shipped.",
    "T5": "The totals report disagrees with our invoices for some large orders. The pricing module is the source of truth. Fix the report.",
    "T6": "CI is red on main. Make the test suite pass.",
}
RETRY = "An acceptance check failed after your change:\n```\n{tail}\n```\nFix it."
FLAGS = [
    "--model", "claude-opus-5-5", "--effort", "medium",
    "--setting-sources", "project,local", "--strict-mcp-config",
    "--output-format", "stream-json", "--verbose",
    "--permission-mode", "acceptEdits",
    "--allowedTools", "Bash Read Edit Write Grep Glob TodoWrite Agent Task Skill",
    "--disallowedTools", "WebFetch WebSearch",
]
GIT = ["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false"]


def prepare(eval_dir: Path, flow: Path, task: str, arm: str, repo: Path) -> None:
    if repo.exists():
        shutil.rmtree(repo)
    subprocess.run([sys.executable, "-I", str(eval_dir / "make_fixture.py"), str(repo)], check=True)
    extra = repo / "_extra_t6_test_schedule.py"
    if task == "T6":
        extra.rename(repo / "tests" / "test_schedule.py")
    else:
        extra.unlink()
    if arm in ("flow", "slim"):
        (repo / ".claude").mkdir()
        subprocess.run(["tar", "-x", "-f", str(eval_dir / "skills.tar"), "-C", str(repo / ".claude")], check=True)
        shutil.copy(flow / "adapters" / "bootstrap.md", repo / "CLAUDE.md")
    if arm == "slim":
        short = json.loads((eval_dir / "slim-descriptions.json").read_text(encoding="utf-8"))
        for name, text in short.items():
            skill = repo / ".claude" / "skills" / name / "SKILL.md"
            body = skill.read_text(encoding="utf-8")
            start = body.index("\ndescription:") + 1
            end = body.index("\n", start)
            skill.write_text(body[:start] + "description: " + json.dumps(text) + body[end:], encoding="utf-8")
        shutil.copy(eval_dir / "slim-bootstrap.md", repo / "CLAUDE.md")
    if arm == "lean":
        shutil.copy(eval_dir / "lean-claude-md.md", repo / "CLAUDE.md")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(GIT + ["add", "-A"], cwd=repo, check=True)
    subprocess.run(GIT + ["commit", "-q", "-m", "base"], cwd=repo, check=True)


def claude(args: list, repo: Path, out: Path) -> dict:
    start = time.time()
    with out.open("w", encoding="utf-8") as handle:
        proc = subprocess.run(["claude", *args, *FLAGS], cwd=repo, stdout=handle, stderr=subprocess.STDOUT, timeout=1500)
    info = {"exit": proc.returncode, "seconds": round(time.time() - start, 1), "session": None,
            "skills": [], "result": None}
    for line in out.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "system" and event.get("subtype") == "init":
            info["session"] = event.get("session_id")
            info["skills"] = event.get("skills") or []
        elif event.get("type") == "result":
            info["result"] = {k: event.get(k) for k in ("total_cost_usd", "num_turns", "usage", "modelUsage", "is_error", "subtype")}
    return info


def check(eval_dir: Path, task: str, repo: Path, out: Path) -> bool:
    hidden = repo / "tests_hidden"
    hidden.mkdir(exist_ok=True)
    (hidden / "__init__.py").write_text("", encoding="utf-8")
    shutil.copy(eval_dir / "hidden" / f"hidden_{task.lower()}.py", hidden)
    visible = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=repo,
                             capture_output=True, text=True, timeout=300)
    secret = subprocess.run([sys.executable, "-m", "unittest", f"tests_hidden.hidden_{task.lower()}", "-v"], cwd=repo,
                            capture_output=True, text=True, timeout=300)
    shutil.rmtree(hidden)
    lines = [ln for ln in visible.stderr.splitlines() if not ln.startswith("imported row")]
    out.write_text("VISIBLE exit=%d\n%s\nHIDDEN exit=%d\n%s\n" % (
        visible.returncode, "\n".join(lines[-40:]), secret.returncode, secret.stderr[-4000:]), encoding="utf-8")
    return visible.returncode == 0 and secret.returncode == 0


def run_one(eval_dir: Path, flow: Path, name: str) -> dict:
    task, arm, rep = name.split("-")
    run_dir = eval_dir / "runs" / name
    run_dir.mkdir(parents=True, exist_ok=True)
    repo = run_dir / "repo"
    prepare(eval_dir, flow, task, arm, repo)
    first = claude(["-p", PROMPTS[task]], repo, run_dir / "turn1.jsonl")
    p1 = check(eval_dir, task, repo, run_dir / "check1.txt")
    second, p2 = None, p1
    if not p1 and first["session"]:
        tail = "\n".join((run_dir / "check1.txt").read_text(encoding="utf-8").splitlines()[-30:])
        second = claude(["-p", RETRY.format(tail=tail), "--resume", first["session"]], repo, run_dir / "turn2.jsonl")
        p2 = check(eval_dir, task, repo, run_dir / "check2.txt")
    diff = subprocess.run(["git", "diff", "--stat", "HEAD"], cwd=repo, capture_output=True, text=True).stdout
    result = {"name": name, "task": task, "arm": arm, "rep": int(rep), "p1": p1, "p2": p2,
              "turn1": first, "turn2": second, "diffstat": diff}
    (run_dir / "result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"{name}\tp1={p1}\tp2={p2}\tcost={(first['result'] or {}).get('total_cost_usd')}", flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("eval_dir", type=Path)
    parser.add_argument("flow", type=Path)
    parser.add_argument("--only")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--arms", default="plain,flow", help="two arms, e.g. plain,lean")
    args = parser.parse_args()
    names = []
    for rep in (1, 2):
        for i, task in enumerate(PROMPTS):
            first, second = args.arms.split(",")
            arms = (first, second) if (i + rep) % 2 else (second, first)
            names += [f"{task}-{arm}-{rep}" for arm in arms]
    if args.only:
        names = [n for n in names if n in args.only.split(",")]
    def safe(name):
        try:
            return run_one(args.eval_dir.resolve(), args.flow.resolve(), name)
        except Exception as error:  # keep the other runs going; the failure is reported
            print(f"{name}\tHARNESS_ERROR\t{error!r}", flush=True)
            return None

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(safe, names))
    return 0


if __name__ == "__main__":
    sys.exit(main())
