from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "skills/nobrainer-tech-flow/scripts/cleanup_worktree.py"
SPEC = importlib.util.spec_from_file_location("cleanup_worktree", SCRIPT_PATH)
assert SPEC and SPEC.loader
cleanup = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cleanup
SPEC.loader.exec_module(cleanup)


def git(*args: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args], cwd=cwd, check=True, text=True, capture_output=True
    )
    return result.stdout.strip()


class WorktreeCleanupTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.remote = self.root / "remote.git"
        self.repo = self.root / "repo"
        self.worktree = self.root / "worktree"
        self.merge_repo = self.root / "merge-repo"
        self.gh = self.root / "gh"
        self.gh.mkdir()
        self.git_wrapper = self.root / "git-wrapper"
        git("init", "-q", "--bare", "--initial-branch=main", str(self.remote))
        seed = self.root / "seed"
        git("init", "-q", "--initial-branch=main", str(seed))
        git("-C", str(seed), "config", "user.email", "test@example.invalid")
        git("-C", str(seed), "config", "user.name", "Test")
        (seed / "file.txt").write_text("base\n", encoding="utf-8")
        git("-C", str(seed), "add", "file.txt")
        git("-C", str(seed), "commit", "-qm", "base")
        git("-C", str(seed), "remote", "add", "origin", str(self.remote))
        git("-C", str(seed), "push", "-q", "-u", "origin", "main")
        git("clone", "-q", str(self.remote), str(self.repo))
        git("-C", str(self.repo), "config", "user.email", "test@example.invalid")
        git("-C", str(self.repo), "config", "user.name", "Test")
        git("-C", str(self.repo), "worktree", "add", "-q", "-b", "codex/task-1", str(self.worktree), "main")
        (self.worktree / "file.txt").write_text("task change\n", encoding="utf-8")
        git("-C", str(self.worktree), "add", "file.txt")
        git("-C", str(self.worktree), "commit", "-qm", "task change")
        self.head_sha = git("-C", str(self.worktree), "rev-parse", "HEAD")
        git("-C", str(self.worktree), "push", "-q", "origin", "codex/task-1")
        git("clone", "-q", str(self.remote), str(self.merge_repo))
        git("-C", str(self.merge_repo), "config", "user.email", "test@example.invalid")
        git("-C", str(self.merge_repo), "config", "user.name", "Test")
        git("-C", str(self.merge_repo), "fetch", "-q", "origin", "codex/task-1")
        git("-C", str(self.merge_repo), "merge", "--no-ff", "-qm", "PR #7", "FETCH_HEAD")
        self.merge_sha = git("-C", str(self.merge_repo), "rev-parse", "HEAD")
        git("-C", str(self.merge_repo), "push", "-q", "origin", "main")

        self.repo_data_path = self.root / "repo-data.json"
        self.pr_data_path = self.root / "pr-data.json"
        (self.gh / "gh").write_text(
            "#!/usr/bin/env python3\n"
            "import json, os, sys\n"
            "print(open(os.environ['GH_REPO_DATA' if sys.argv[1] == 'repo' else 'GH_PR_DATA'], encoding='utf-8').read())\n",
            encoding="utf-8",
        )
        (self.gh / "gh").chmod(0o755)
        actual_git = shutil.which("git")
        assert actual_git
        self.git_wrapper.write_text(
            "#!/usr/bin/env python3\n"
            "import os, sys\n"
            f"real = {actual_git!r}\n"
            "args = sys.argv[1:]\n"
            f"if args[:5] == ['-C', {str(self.repo.resolve())!r}, 'remote', 'get-url', 'origin']:\n"
            " print('https://github.com/acme/project.git')\n"
            "else:\n"
            " os.execv(real, [real, *args])\n",
            encoding="utf-8",
        )
        self.git_wrapper.chmod(0o755)
        self.repo_data = {"nameWithOwner": "acme/project", "defaultBranchRef": {"name": "main"}}
        self.pr_data = {
            "number": 7,
            "state": "MERGED",
            "mergedAt": "2026-09-26T10:00:00Z",
            "headRefName": "codex/task-1",
            "headRefOid": self.head_sha,
            "baseRefName": "main",
            "mergeCommit": {"oid": self.merge_sha},
            "url": "https://github.com/acme/project/pull/7",
        }
        self.write_gh_data()
        self.manifest_path = self.root / "task.json"
        self.write_manifest()
        self.env = {
            **os.environ,
            "PATH": str(self.gh) + os.pathsep + os.environ.get("PATH", ""),
            "GH_REPO_DATA": str(self.repo_data_path),
            "GH_PR_DATA": str(self.pr_data_path),
        }

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_gh_data(self) -> None:
        self.repo_data_path.write_text(json.dumps(self.repo_data), encoding="utf-8")
        self.pr_data_path.write_text(json.dumps(self.pr_data), encoding="utf-8")

    def write_manifest(self, *, writer_status: str = "IDLE", active_writers: list | None = None,
                       observed_at: str | None = None) -> None:
        manifest = {
            "schema_version": 1,
            "task_id": "task-1",
            "repository_path": str(self.repo),
            "worktree_path": str(self.worktree),
            "remote": "origin",
            "repository": "acme/project",
            "pr_number": 7,
            "branch": "codex/task-1",
            "submitted_head_sha": self.head_sha,
            "writer_readback": {
                "status": writer_status,
                "active_writers": [] if active_writers is None else active_writers,
                "worktree_path": str(self.worktree),
                "source": "current host session registry",
                "observed_at": observed_at or dt.datetime.now(dt.timezone.utc).isoformat(),
            },
        }
        self.manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def run_cleanup(self, apply: bool = False) -> dict:
        with patch.dict(os.environ, self.env), patch.object(cleanup.shutil, "which", return_value=None):
            return cleanup.verify_and_cleanup(
                self.manifest_path, apply=apply, git_bin=str(self.git_wrapper)
            )

    def test_dry_run_is_default_and_reports_verified_pr_without_removal(self) -> None:
        result = self.run_cleanup()
        self.assertEqual("DRY_RUN_READY", result["status"])
        self.assertTrue(self.worktree.exists())
        self.assertEqual(self.head_sha, result["submitted_head_sha"])
        self.assertEqual(self.merge_sha, result["merge_sha"])

    def test_apply_removes_only_verified_clean_task_worktree_and_reads_back(self) -> None:
        result = self.run_cleanup(apply=True)
        self.assertEqual("REMOVED", result["status"])
        self.assertFalse(self.worktree.exists())
        self.assertNotIn(str(self.worktree), git("-C", str(self.repo), "worktree", "list", "--porcelain"))
        self.assertTrue(self.repo.exists())

    def test_unmerged_pr_is_preserved(self) -> None:
        self.pr_data["mergedAt"] = None
        self.write_gh_data()
        with self.assertRaisesRegex(cleanup.CleanupError, "not verified as merged"):
            self.run_cleanup(apply=True)
        self.assertTrue(self.worktree.exists())

    def test_closed_state_is_not_accepted_as_gh_merged_state(self) -> None:
        self.pr_data["state"] = "CLOSED"
        self.write_gh_data()
        with self.assertRaisesRegex(cleanup.CleanupError, "not verified as merged"):
            self.run_cleanup(apply=True)
        self.assertTrue(self.worktree.exists())

    def test_wrong_submitted_head_is_preserved(self) -> None:
        self.pr_data["headRefOid"] = "0" * 40
        self.write_gh_data()
        with self.assertRaisesRegex(cleanup.CleanupError, "submitted head SHA"):
            self.run_cleanup(apply=True)
        self.assertTrue(self.worktree.exists())

    def test_merge_result_must_be_in_fetched_default_branch_history(self) -> None:
        git("-C", str(self.repo), "checkout", "-qb", "unrelated", "main")
        git("-C", str(self.repo), "commit", "--allow-empty", "-qm", "unmerged result")
        self.pr_data["mergeCommit"]["oid"] = git("-C", str(self.repo), "rev-parse", "HEAD")
        self.write_gh_data()
        with self.assertRaisesRegex(cleanup.CleanupError, "not in fetched default-branch history"):
            self.run_cleanup(apply=True)
        self.assertTrue(self.worktree.exists())

    def test_dirty_or_untracked_worktree_is_preserved(self) -> None:
        (self.worktree / "owner-note.txt").write_text("keep me", encoding="utf-8")
        with self.assertRaisesRegex(cleanup.CleanupError, "untracked files"):
            self.run_cleanup(apply=True)
        self.assertTrue((self.worktree / "owner-note.txt").exists())

    def test_ignored_user_content_is_preserved(self) -> None:
        (self.repo / ".git" / "info" / "exclude").write_text("secret.cache\n", encoding="utf-8")
        (self.worktree / "secret.cache").write_text("keep me", encoding="utf-8")
        with self.assertRaisesRegex(cleanup.CleanupError, "ignored or other removable"):
            self.run_cleanup(apply=True)
        self.assertTrue((self.worktree / "secret.cache").exists())

    def test_active_or_stale_writer_readback_blocks_cleanup(self) -> None:
        self.write_manifest(writer_status="ACTIVE", active_writers=["worker-2"])
        with self.assertRaisesRegex(cleanup.CleanupError, "does not prove IDLE"):
            self.run_cleanup(apply=True)
        self.write_manifest(observed_at="2020-01-01T00:00:00Z")
        with self.assertRaisesRegex(cleanup.CleanupError, "stale"):
            self.run_cleanup(apply=True)
        self.assertTrue(self.worktree.exists())

    def test_github_remote_identity_accepts_https_and_ssh_only(self) -> None:
        self.assertEqual(("github.com", "acme/project"), cleanup.remote_identity("https://github.com/acme/project.git"))
        self.assertEqual(("github.com", "acme/project"), cleanup.remote_identity("git@github.com:acme/project.git"))
        with self.assertRaisesRegex(cleanup.CleanupError, "not a verifiable GitHub URL"):
            cleanup.remote_identity(str(self.remote))

    def test_process_using_worktree_blocks_cleanup(self) -> None:
        result = subprocess.CompletedProcess(
            ["lsof"], 0, f"p4321\ncagent\nfcwd\nn{self.worktree}\n", ""
        )
        with patch.object(cleanup, "run", return_value=result):
            with self.assertRaisesRegex(cleanup.CleanupError, "active process"):
                cleanup.lsof_writer_check("lsof", self.worktree)

    def test_lsof_exit_one_without_output_means_no_matching_process(self) -> None:
        no_match = subprocess.CompletedProcess(["lsof"], 1, "", "")
        with patch.object(cleanup.subprocess, "run", return_value=no_match):
            cleanup.lsof_writer_check("lsof", self.worktree)

    def test_lsof_inspection_error_still_blocks_cleanup(self) -> None:
        results = [
            subprocess.CompletedProcess(["lsof"], 0, "", ""),
            subprocess.CompletedProcess(["lsof"], 1, "", "permission denied\n"),
        ]
        with patch.object(cleanup.subprocess, "run", side_effect=results):
            with self.assertRaisesRegex(cleanup.CleanupError, "permission denied"):
                cleanup.lsof_writer_check("lsof", self.worktree)


if __name__ == "__main__":
    unittest.main()
