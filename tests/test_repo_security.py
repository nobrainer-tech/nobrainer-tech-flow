from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "scripts" / "check_public_commit.py"
FETCHER = ROOT / "scripts" / "fetch_public_refs.py"


def run_git(*args: str, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


class RepositorySecurityTests(unittest.TestCase):
    def test_public_commit_guard_rejects_automated_identity_and_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            global_config = repo / "empty-gitconfig"
            global_config.write_text("", encoding="utf-8")
            env = dict(os.environ)
            env["GIT_CONFIG_NOSYSTEM"] = "1"
            env["GIT_CONFIG_GLOBAL"] = str(global_config)

            subprocess.run(
                ["git", "-C", str(repo), "config", "user.name", "Automated Backup"],
                check=True,
                env=env,
            )
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "backup-bot@example.invalid"],
                check=True,
                env=env,
            )
            result = subprocess.run(
                ["python3", str(GUARD)],
                cwd=repo,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("PUBLIC_COMMIT_GUARD: BLOCKED", result.stderr)
            self.assertIn("Automated Backup", result.stderr)

            subprocess.run(
                ["git", "-C", str(repo), "config", "user.name", "nobrainer-tech"],
                check=True,
                env=env,
            )
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "arkadiusz@nobrainer.tech"],
                check=True,
                env=env,
            )
            result = subprocess.run(
                ["python3", str(GUARD)],
                cwd=repo,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

            artifact = repo / "backups" / "config.json"
            artifact.parent.mkdir()
            artifact.write_text("{}\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(repo), "add", "-f", "backups/config.json"],
                check=True,
                env=env,
            )
            result = subprocess.run(
                ["python3", str(GUARD)],
                cwd=repo,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(0, result.returncode)
            self.assertIn("staged backup path=backups/config.json", result.stderr)

            nested = repo / "runtime" / "backups" / "state.json"
            nested.parent.mkdir(parents=True)
            nested.write_text("{}\n", encoding="utf-8")
            subprocess.run(
                ["git", "-C", str(repo), "add", "-f", "runtime/backups/state.json"],
                check=True,
                env=env,
            )
            result = subprocess.run(
                ["python3", str(GUARD)],
                cwd=repo,
                env=env,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(0, result.returncode)
        self.assertIn(
            "staged backup path=runtime/backups/state.json",
            result.stderr,
        )

    def test_public_commit_guard_reports_a_missing_git_instead_of_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as empty_path:
            result = subprocess.run(
                [sys.executable, str(GUARD)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
                env={**os.environ, "PATH": empty_path},
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        self.assertIn("PUBLIC_COMMIT_GUARD: ERROR: git is unavailable", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_public_backup_ignore_patterns_and_hook_are_present(self) -> None:
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        pre_commit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        for pattern in ("backup/", "backups/", "*.bak", "*.backup-*"):
            self.assertIn(pattern, ignore)
        self.assertIn("id: public-commit-guard", pre_commit)
        self.assertIn("scripts/check_public_commit.py", pre_commit)

    def test_public_fetch_updates_remote_ref_without_touching_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bare = root / "remote.git"
            seed = root / "seed"
            local = root / "local"
            run_git("init", "-q", "--bare", bare, cwd=root).check_returncode()
            run_git("init", "-q", seed, cwd=root).check_returncode()
            run_git("config", "user.name", "test-owner", cwd=seed).check_returncode()
            run_git("config", "user.email", "test-owner@example.invalid", cwd=seed).check_returncode()
            (seed / "state.txt").write_text("remote-v1\n", encoding="utf-8")
            run_git("add", "state.txt", cwd=seed).check_returncode()
            run_git("commit", "-q", "-m", "seed", cwd=seed).check_returncode()
            run_git("branch", "-M", "main", cwd=seed).check_returncode()
            run_git("remote", "add", "origin", bare, cwd=seed).check_returncode()
            run_git("push", "-q", "origin", "main", cwd=seed).check_returncode()
            run_git("symbolic-ref", "HEAD", "refs/heads/main", cwd=bare).check_returncode()
            run_git("clone", "-q", bare, local, cwd=root).check_returncode()
            initial_tip = run_git("rev-parse", "HEAD", cwd=local).stdout.strip()

            (seed / "state.txt").write_text("remote-v2\n", encoding="utf-8")
            run_git("commit", "-q", "-am", "advance remote", cwd=seed).check_returncode()
            run_git("push", "-q", "origin", "main", cwd=seed).check_returncode()
            remote_tip = run_git("rev-parse", "HEAD", cwd=seed).stdout.strip()

            (local / "state.txt").write_text("local draft\n", encoding="utf-8")
            result = subprocess.run(
                ["python3", str(FETCHER)],
                cwd=local,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("PUBLIC_FETCH: PASS remote=origin branch=main", result.stdout)
            self.assertEqual("local draft\n", (local / "state.txt").read_text(encoding="utf-8"))
            self.assertEqual(initial_tip, run_git("rev-parse", "HEAD", cwd=local).stdout.strip())
            self.assertEqual(
                remote_tip,
                run_git("rev-parse", "refs/remotes/origin/main", cwd=local).stdout.strip(),
            )

    def test_gitleaks_policy_has_no_broad_allowlist(self) -> None:
        config = (ROOT / ".gitleaks.toml").read_text(encoding="utf-8")
        pre_commit = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
        self.assertIn("useDefault = true", config)
        self.assertNotIn("[allowlist]", config)
        self.assertNotIn("[[allowlists]]", config)
        self.assertNotIn(".*\\.md", config)
        self.assertIn("rev: v8.30.1", pre_commit)
        self.assertIn('args: ["--ignore-gitleaks-allow"]', pre_commit)

    @unittest.skipUnless(shutil.which("gitleaks"), "gitleaks CLI not installed")
    def test_current_cli_rejects_a_synthetic_staged_probe(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            shutil.copy2(ROOT / ".gitleaks.toml", repo / ".gitleaks.toml")
            probe = repo / ".gitleaks-verify.tmp"
            probe.write_text(
                "aws_access_key_id=" + "AKIA" + "ABCDEFGHIJKLMNOP" + "\n",
                encoding="utf-8",
            )
            subprocess.run(
                ["git", "-C", str(repo), "add", ".gitleaks-verify.tmp"],
                check=True,
            )
            result = subprocess.run(
                [
                    "gitleaks",
                    "git",
                    "--staged",
                    "--redact",
                    "--no-banner",
                    "--ignore-gitleaks-allow",
                ],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertNotEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
