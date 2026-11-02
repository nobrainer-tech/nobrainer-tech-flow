"""Coverage gate: a skill, hook or instruction change must come with a docs/evals/ record."""

from __future__ import annotations

import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import check_eval_coverage


def git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
         "-c", "commit.gpgsign=false", *args],
        check=True,
        capture_output=True,
    )


def write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class EvalCoverageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = Path(self._tmp.name)
        git(self.repo, "init", "-q", "-b", "main")
        write(self.repo, "skills/nobrainer-build/SKILL.md", "base\n")
        write(self.repo, "skills/nobrainer-review/SKILL.md", "base\n")
        write(self.repo, "hooks/session-start", "base\n")
        write(self.repo, "scripts/tool.py", "base\n")
        write(self.repo, "docs/evals/old.md", "nobrainer-review old record\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "base")
        git(self.repo, "branch", "base")
        git(self.repo, "checkout", "-q", "-b", "change")

    def run_check(self, *extra: str):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = check_eval_coverage.main(["--repo", str(self.repo), "base", "HEAD", *extra])
        return code, out.getvalue(), err.getvalue()

    def test_skill_change_without_eval_fails_and_names_the_skill(self):
        write(self.repo, "skills/nobrainer-build/SKILL.md", "changed\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "head")
        code, _, err = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("nobrainer-build", err)
        self.assertNotIn("nobrainer-review", err)

    def test_an_unrelated_eval_does_not_cover_a_skill(self):
        write(self.repo, "skills/nobrainer-build/SKILL.md", "changed\n")
        write(self.repo, "docs/evals/other.md", "mentions nobrainer-review only\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "head")
        code, _, err = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("nobrainer-build", err)

    def test_skill_change_with_matching_eval_passes(self):
        write(self.repo, "skills/nobrainer-build/references/x.md", "changed\n")
        write(self.repo, "docs/evals/build.md", "PRESSURE_RESULT: nobrainer-build\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "head")
        code, out, _ = self.run_check()
        self.assertEqual(code, 0)
        self.assertIn("EVAL_COVERAGE_OK", out)

    def test_each_changed_skill_needs_a_mention(self):
        write(self.repo, "skills/nobrainer-build/SKILL.md", "changed\n")
        write(self.repo, "skills/nobrainer-review/SKILL.md", "changed\n")
        write(self.repo, "docs/evals/build.md", "nobrainer-build only\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "head")
        code, _, err = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("nobrainer-review", err)
        self.assertNotIn("uncovered skill: nobrainer-build", err)

    def test_hooks_change_with_any_eval_passes(self):
        write(self.repo, "hooks/session-start", "changed\n")
        write(self.repo, "docs/evals/any.md", "record\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "head")
        self.assertEqual(self.run_check()[0], 0)

    def test_hooks_change_without_eval_fails(self):
        write(self.repo, "hooks/session-start", "changed\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "head")
        code, _, err = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("hooks/session-start", err)

    def test_scripts_only_change_passes(self):
        write(self.repo, "scripts/tool.py", "changed\n")
        write(self.repo, "README.md", "docs\n")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "head")
        self.assertEqual(self.run_check()[0], 0)

    def test_unknown_ref_is_an_error_not_a_pass(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = check_eval_coverage.main(["--repo", str(self.repo), "no-such-ref", "HEAD"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
