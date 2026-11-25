"""Shared helpers for the done-gap eval: build a task repo and run its checks."""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = tuple(f"D{i}" for i in range(1, 11))
GIT = ["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid", "-c", "commit.gpgsign=false"]


def copy_tree(src: Path, dst: Path) -> None:
    if not src.is_dir():
        return
    for path in sorted(src.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            target = dst / path.relative_to(src)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


def build(task: str, repo: Path, with_ref: bool = False) -> None:
    """Write base + overlay (+ ref) into `repo` and commit it as the base commit."""
    if repo.exists():
        shutil.rmtree(repo)
    subprocess.run([sys.executable, "-I", str(HERE / "make_base.py"), str(repo)], check=True)
    copy_tree(HERE / "tasks" / task / "overlay", repo)
    if with_ref:
        copy_tree(HERE / "tasks" / task / "ref", repo)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(GIT + ["add", "-A"], cwd=repo, check=True)
    subprocess.run(GIT + ["commit", "-q", "-m", "base"], cwd=repo, check=True)


def prompt(task: str) -> str:
    return (HERE / "tasks" / task / "prompt.txt").read_text(encoding="utf-8").strip()


def check(task: str, repo: Path, out: Path = None) -> bool:
    """Visible suite plus the hidden check; the hidden files are removed again afterwards."""
    hidden = repo / "tests_hidden"
    if hidden.exists():
        shutil.rmtree(hidden)
    hidden.mkdir()
    (hidden / "__init__.py").write_text("", encoding="utf-8")
    copy_tree(HERE / "tasks" / task / "hidden", hidden)
    try:
        visible = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=repo,
                                 capture_output=True, text=True, timeout=600)
        secret = subprocess.run([sys.executable, "-m", "unittest", "tests_hidden.test_hidden", "-v"], cwd=repo,
                                capture_output=True, text=True, timeout=600)
    finally:
        shutil.rmtree(hidden)
    if out is not None:
        lines = [ln for ln in visible.stderr.splitlines() if not ln.startswith("imported row")]
        out.write_text("VISIBLE exit=%d\n%s\nHIDDEN exit=%d\n%s\n" % (
            visible.returncode, "\n".join(lines[-40:]), secret.returncode, secret.stderr[-4000:]), encoding="utf-8")
    return visible.returncode == 0 and secret.returncode == 0
