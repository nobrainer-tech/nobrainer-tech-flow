#!/usr/bin/env python3
"""Safely remove one task-owned worktree after its exact PR is merged."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from urllib.parse import urlsplit


SHA_RE = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
WRITER_MAX_AGE_SECONDS = 60


class CleanupError(Exception):
    """A failed safety gate or an unverifiable cleanup result."""


def run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    allow_clean_no_match: bool = False,
) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise CleanupError(f"cannot run {Path(argv[0]).name}: {type(exc).__name__}") from None
    if result.returncode and not (
        allow_clean_no_match
        and result.returncode == 1
        and not result.stdout.strip()
        and not result.stderr.strip()
    ):
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise CleanupError(f"command failed ({Path(argv[0]).name}): {detail[:500]}")
    return result


def git(git_bin: str, repo: Path, *args: str) -> str:
    return run([git_bin, "-C", str(repo), *args]).stdout.strip()


def required_string(obj: dict, key: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CleanupError(f"manifest is missing non-empty {key}")
    return value.strip()


def read_manifest(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise CleanupError("cannot read a valid JSON task manifest") from None
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise CleanupError("unsupported worktree manifest schema")
    return data


def verify_writer_readback(data: dict, worktree: Path, now: dt.datetime | None = None) -> None:
    readback = data.get("writer_readback")
    if not isinstance(readback, dict):
        raise CleanupError("missing authoritative host writer readback")
    if readback.get("status") != "IDLE" or readback.get("active_writers") != []:
        raise CleanupError("host writer readback does not prove IDLE with no active writers")
    if Path(required_string(readback, "worktree_path")).expanduser().resolve() != worktree:
        raise CleanupError("writer readback names a different worktree")
    required_string(readback, "source")
    try:
        observed = dt.datetime.fromisoformat(required_string(readback, "observed_at").replace("Z", "+00:00"))
    except ValueError:
        raise CleanupError("writer readback has an invalid observed_at timestamp") from None
    if observed.tzinfo is None:
        raise CleanupError("writer readback timestamp must include a timezone")
    now = now or dt.datetime.now(dt.timezone.utc)
    age = (now - observed.astimezone(dt.timezone.utc)).total_seconds()
    if age < -5 or age > WRITER_MAX_AGE_SECONDS:
        raise CleanupError("host writer readback is stale or from the future")


def remote_identity(url: str) -> tuple[str, str]:
    """Extract host and owner/repository from common GitHub remote URL forms."""
    if re.match(r"^[^/@:]+@[^:]+:.+$", url):
        host, path = url.split(":", 1)
        host = host.rsplit("@", 1)[1]
    else:
        parsed = urlsplit(url)
        if parsed.scheme not in {"https", "ssh", "git"} or not parsed.hostname:
            raise CleanupError("task remote is not a verifiable GitHub URL")
        host, path = parsed.hostname, parsed.path.lstrip("/")
    path = path.removesuffix(".git").strip("/")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", path):
        raise CleanupError("task remote URL has no exact owner/repository identity")
    return host.lower(), path.lower()


def parse_worktrees(value: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []
    for block in value.split("\n\n"):
        entry: dict[str, str] = {}
        for line in block.splitlines():
            key, _, rest = line.partition(" ")
            if key in {"worktree", "HEAD", "branch"}:
                entry[key] = rest
        if "worktree" in entry:
            entries.append(entry)
    return entries


def lsof_writer_check(lsof_bin: str, worktree: Path) -> None:
    """Fail if lsof reports a process cwd or open file inside this worktree."""
    worktree = worktree.resolve()
    commands = [
        [lsof_bin, "-nP", "-Fpcfn", "-d", "cwd"],
        [lsof_bin, "-nP", "-Fpcfn", "+D", str(worktree)],
    ]
    for command in commands:
        result = run(command, allow_clean_no_match=True)
        offenders: list[str] = []
        process = "unknown process"
        for line in result.stdout.splitlines():
            if line.startswith("p"):
                process = line[1:]
            elif line.startswith("n"):
                raw = line[1:].removesuffix(" (deleted)")
                try:
                    candidate = Path(raw).resolve()
                    if candidate == worktree or worktree in candidate.parents:
                        offenders.append(process)
                except (OSError, RuntimeError):
                    continue
        if offenders:
            raise CleanupError("active process is using the task worktree (PID(s): " + ",".join(sorted(set(offenders))) + ")")


def verify_and_cleanup(manifest_path: Path, *, apply: bool, gh_bin: str = "gh", git_bin: str = "git") -> dict:
    manifest = read_manifest(manifest_path)
    repo_path = Path(required_string(manifest, "repository_path")).expanduser().resolve()
    worktree = Path(required_string(manifest, "worktree_path")).expanduser().resolve()
    task_id = required_string(manifest, "task_id")
    remote = required_string(manifest, "remote")
    repository = required_string(manifest, "repository").lower()
    branch = required_string(manifest, "branch")
    expected_head = required_string(manifest, "submitted_head_sha").lower()
    if not repo_path.is_dir() or not worktree.is_dir() or repo_path == worktree:
        raise CleanupError("repository or task worktree path is missing or ambiguous")
    if not SHA_RE.fullmatch(expected_head):
        raise CleanupError("submitted_head_sha must be a full 40-character commit SHA")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise CleanupError("repository must be an exact owner/repository slug")
    if remote.startswith("-") or remote not in git(git_bin, repo_path, "remote").splitlines():
        raise CleanupError("manifest remote is not an exact configured Git remote")
    git(git_bin, repo_path, "check-ref-format", "refs/heads/" + branch)

    registered = parse_worktrees(git(git_bin, repo_path, "worktree", "list", "--porcelain"))
    matching = [entry for entry in registered if Path(entry["worktree"]).resolve() == worktree]
    if len(matching) != 1:
        raise CleanupError("exact task worktree is not uniquely registered")
    entry = matching[0]
    if entry.get("branch") != "refs/heads/" + branch:
        raise CleanupError("registered worktree branch does not match the task manifest")
    if entry.get("HEAD", "").lower() != expected_head:
        raise CleanupError("registered worktree HEAD does not match the submitted PR head")
    if git(git_bin, worktree, "rev-parse", "--show-toplevel") != str(worktree):
        raise CleanupError("resolved worktree root does not match the task path")
    if git(git_bin, worktree, "status", "--porcelain=v1", "--untracked-files=all"):
        raise CleanupError("task worktree has staged, unstaged, conflicted, or untracked files")
    if git(git_bin, worktree, "clean", "-ndx"):
        raise CleanupError("task worktree contains ignored or other removable user data")

    remote_url = git(git_bin, repo_path, "remote", "get-url", remote)
    host, remote_repo = remote_identity(remote_url)
    try:
        pr_number = int(manifest["pr_number"])
    except (KeyError, TypeError, ValueError):
        raise CleanupError("manifest pr_number must be an integer") from None
    if pr_number <= 0:
        raise CleanupError("manifest pr_number must be positive")

    gh_repo = json.loads(run([gh_bin, "repo", "view", repository, "--json", "nameWithOwner,defaultBranchRef"]).stdout)
    if not isinstance(gh_repo, dict) or str(gh_repo.get("nameWithOwner", "")).lower() != repository:
        raise CleanupError("GitHub repository readback does not match the manifest repository")
    default_ref = gh_repo.get("defaultBranchRef")
    default_branch = default_ref.get("name") if isinstance(default_ref, dict) else None
    if not isinstance(default_branch, str) or not default_branch:
        raise CleanupError("GitHub did not return a verified default branch")

    pr = json.loads(
        run([
            gh_bin,
            "pr",
            "view",
            str(pr_number),
            "--repo",
            repository,
            "--json",
            "number,state,mergedAt,headRefName,headRefOid,baseRefName,mergeCommit,url",
        ]).stdout
    )
    if not isinstance(pr, dict):
        raise CleanupError("GitHub PR readback is invalid")
    try:
        returned_number = int(pr.get("number", 0))
    except (TypeError, ValueError):
        raise CleanupError("GitHub returned an invalid PR number") from None
    if returned_number != pr_number:
        raise CleanupError("GitHub returned a different PR number")
    if pr.get("state") != "CLOSED" or not isinstance(pr.get("mergedAt"), str) or not pr.get("mergedAt"):
        raise CleanupError("PR is not verified as merged")
    if pr.get("headRefName") != branch or str(pr.get("headRefOid", "")).lower() != expected_head:
        raise CleanupError("PR source branch or submitted head SHA does not match this task worktree")
    if pr.get("baseRefName") != default_branch:
        raise CleanupError("PR target is not the verified repository default branch")
    merge_commit = pr.get("mergeCommit")
    merge_sha = merge_commit.get("oid") if isinstance(merge_commit, dict) else None
    if not isinstance(merge_sha, str) or not SHA_RE.fullmatch(merge_sha):
        raise CleanupError("GitHub did not return a valid PR merge-result SHA")
    pr_url = urlsplit(str(pr.get("url", "")))
    if pr_url.scheme != "https" or pr_url.hostname != host:
        raise CleanupError("PR URL host does not match the task Git remote")
    expected_path = f"/{repository}/pull/{pr_number}"
    if pr_url.path.rstrip("/").lower() != expected_path.lower():
        raise CleanupError("PR URL does not identify the exact repository and PR")
    if remote_repo != repository:
        raise CleanupError("task Git remote and verified PR repository do not match")

    git(git_bin, repo_path, "check-ref-format", "refs/heads/" + default_branch)
    fetched_ref = "refs/nobrainer-tech-flow/cleanup/" + uuid.uuid4().hex + "/base"
    try:
        run([
            git_bin,
            "-C",
            str(repo_path),
            "fetch",
            "--no-tags",
            remote,
            f"+refs/heads/{default_branch}:{fetched_ref}",
        ])
        fetched_base = git(git_bin, repo_path, "rev-parse", fetched_ref).lower()
        if not SHA_RE.fullmatch(fetched_base):
            raise CleanupError("fetched target branch did not resolve to a full commit SHA")
        ancestor = subprocess.run(
            [git_bin, "-C", str(repo_path), "merge-base", "--is-ancestor", merge_sha, fetched_base],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )
        if ancestor.returncode != 0:
            raise CleanupError("verified PR merge-result SHA is not in fetched default-branch history")
    finally:
        run([git_bin, "-C", str(repo_path), "update-ref", "-d", fetched_ref])

    verify_writer_readback(manifest, worktree)
    lsof = shutil.which("lsof")
    if lsof:
        lsof_writer_check(lsof, worktree)

    result = {
        "status": "DRY_RUN_READY" if not apply else "REMOVED",
        "task_id": task_id,
        "repository": repository,
        "pr_number": pr_number,
        "branch": branch,
        "submitted_head_sha": expected_head,
        "merge_sha": merge_sha.lower(),
        "fetched_default_branch_sha": fetched_base,
        "worktree_path": str(worktree),
        "active_writer_check": "authoritative host readback is fresh and IDLE",
        "local_process_check": "lsof passed" if lsof else "UNAVAILABLE; host readback only",
    }
    if not apply:
        return result

    # Re-read volatile safety gates immediately before the destructive Git operation.
    verify_writer_readback(manifest, worktree)
    if lsof:
        lsof_writer_check(lsof, worktree)
    if git(git_bin, worktree, "status", "--porcelain=v1", "--untracked-files=all") or git(
        git_bin, worktree, "clean", "-ndx"
    ):
        raise CleanupError("worktree changed after verification; refusing removal")
    run([git_bin, "-C", str(repo_path), "worktree", "remove", str(worktree)])
    after = parse_worktrees(git(git_bin, repo_path, "worktree", "list", "--porcelain"))
    if any(Path(item["worktree"]).resolve() == worktree for item in after):
        raise CleanupError("Git removal returned but the task worktree is still registered")
    result["status"] = "REMOVED"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path, help="exact task worktree lifecycle JSON")
    parser.add_argument("--apply", action="store_true", help="remove the worktree after every safety gate passes")
    parser.add_argument("--gh-bin", default="gh", help=argparse.SUPPRESS)
    parser.add_argument("--git-bin", default="git", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    try:
        result = verify_and_cleanup(args.manifest, apply=args.apply, gh_bin=args.gh_bin, git_bin=args.git_bin)
    except (CleanupError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
