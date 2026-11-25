"""Run the done-gap eval: PLAIN, FLOW and FLOW_ASK on ten tasks, two repeats, one retry turn.

Usage: python3 run.py WORK_DIR SKILLS_TAR BOOTSTRAP_MD [--only D1-plain-1,...] [--workers 2]
SKILLS_TAR = `git archive <frozen commit> skills`; BOOTSTRAP_MD = adapters/bootstrap.md of that commit.
Writes WORK_DIR/runs/<task>-<arm>-<rep>/{turn1.jsonl,turn2.jsonl,check*.txt,result.json}.
"""
import argparse
import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import common

sys.path.insert(0, str(common.HERE.parent / "token-cost"))
import run as cost_run  # noqa: E402  (same client flags, retry text and stream parser)

ARMS = ("plain", "flow", "flowask")
ASK = "Use NBFlow. "
REPEATS = (1, 2)


def install_flow(repo: Path, skills_tar: Path, bootstrap: Path) -> None:
    (repo / ".claude").mkdir(exist_ok=True)
    subprocess.run(["tar", "-x", "-f", str(skills_tar), "-C", str(repo / ".claude")], check=True)
    shutil.copyfile(bootstrap, repo / "CLAUDE.md")
    subprocess.run(common.GIT + ["add", "-A"], cwd=repo, check=True)
    subprocess.run(common.GIT + ["commit", "-q", "-m", "install flow"], cwd=repo, check=True)


def transcript(path: Path) -> dict:
    """Final message text and the skills the agent invoked."""
    final, invoked = "", []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result":
            final = event.get("result") or ""
        elif event.get("type") == "assistant":
            for block in (event.get("message") or {}).get("content") or []:
                if block.get("type") == "tool_use" and block.get("name") == "Skill":
                    invoked.append(str((block.get("input") or {}).get("skill") or (block.get("input") or {}).get("command")))
    return {"final": final, "invoked": invoked}


def run_one(work: Path, skills_tar: Path, bootstrap: Path, name: str) -> dict:
    task, arm, rep = name.split("-")
    run_dir = work / "runs" / name
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)
    repo = run_dir / "repo"
    common.build(task, repo)
    if arm in ("flow", "flowask"):
        install_flow(repo, skills_tar, bootstrap)
    text = (ASK if arm == "flowask" else "") + common.prompt(task)
    turns = [cost_run.claude(["-p", text], repo, run_dir / "turn1.jsonl")]
    passes = [common.check(task, repo, run_dir / "check1.txt")]
    if not passes[0] and turns[0]["session"]:
        tail = "\n".join((run_dir / "check1.txt").read_text(encoding="utf-8").splitlines()[-30:])
        turns.append(cost_run.claude(["-p", cost_run.RETRY.format(tail=tail), "--resume", turns[0]["session"]], repo,
                                     run_dir / "turn2.jsonl"))
        passes.append(common.check(task, repo, run_dir / "check2.txt"))
    first = transcript(run_dir / "turn1.jsonl")
    diff = subprocess.run(["git", "diff", "--stat", "HEAD"], cwd=repo, capture_output=True, text=True).stdout
    result = {"name": name, "task": task, "arm": arm, "rep": int(rep), "prompt": text, "passes": passes,
              "p1": passes[0], "pf": passes[-1], "turns": turns, "turn1": turns[0], "final1": first["final"],
              "invoked1": first["invoked"], "diffstat": diff}
    (run_dir / "result.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    shutil.rmtree(repo / ".claude", ignore_errors=True)  # keep the agent's work, drop the copied skills
    costs = [(t["result"] or {}).get("total_cost_usd") for t in turns]
    print(f"{name}\tpasses={passes}\tcosts={costs}\tinvoked={first['invoked']}", flush=True)
    return result


def names(only=None):
    out = []
    for rep in REPEATS:
        for i, task in enumerate(common.TASKS):
            shift = (i + rep) % 3
            out += [f"{task}-{arm}-{rep}" for arm in ARMS[shift:] + ARMS[:shift]]
    return [n for n in out if not only or n in only.split(",")]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("work", type=Path)
    parser.add_argument("skills_tar", type=Path)
    parser.add_argument("bootstrap", type=Path)
    parser.add_argument("--only")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    work, tar, boot = args.work.resolve(), args.skills_tar.resolve(), args.bootstrap.resolve()

    def safe(name):
        try:
            return run_one(work, tar, boot, name)
        except Exception as error:  # keep the other runs going; the failure is reported and rerun
            print(f"{name}\tHARNESS_ERROR\t{error!r}", flush=True)
            return None

    with ThreadPoolExecutor(args.workers) as pool:
        list(pool.map(safe, names(args.only)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
