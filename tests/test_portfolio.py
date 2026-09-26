from __future__ import annotations

import hashlib
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "docs" / "evals" / "portfolio-autoimprove-2026-08-29.md"

ACTIVE_SKILLS = (
    "nobrainer-ultra",
    "nobrainer-team",
    "nobrainer-dispatcher",
    "nobrainer-research",
    "nobrainer-writing",
    "nobrainer-build",
    "nobrainer-security",
    "nobrainer-sessions",
    "nobrainer-spec-driven-development",
    "nobrainer-wiki",
    "nobrainer-browser",
    "nobrainer-autoimprove",
    "nobrainer-decide",
    "nobrainer-rca",
    "nobrainer-review",
)


def sha256(relative: str) -> str | None:
    path = ROOT / relative
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def git_sha256(commit: str, relative: str) -> str:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    )
    return hashlib.sha256(result.stdout).hexdigest()


class PortfolioAuditTests(unittest.TestCase):
    def test_portfolio_audit_binds_source_contract(self) -> None:
        report = REPORT.read_text(encoding="utf-8")
        self.assertNotIn("<filled", report)
        self.assertIn(
            "HISTORICAL_BINDING: docs/evals/portfolio-autoimprove-2026-08-29.md",
            report,
        )
        source_commit = re.search(
            r"^SOURCE_COMMIT: ([0-9a-f]{40})$", report, re.MULTILINE
        )
        self.assertIsNotNone(source_commit)
        source_ref = source_commit.group(1)
        has_git_repository = (
            subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=ROOT,
                capture_output=True,
                check=False,
            ).returncode
            == 0
        )
        if has_git_repository:
            source_is_reachable = subprocess.run(
                ["git", "merge-base", "--is-ancestor", source_ref, "HEAD"],
                cwd=ROOT,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                0,
                source_is_reachable.returncode,
                "historical source commit must remain reachable from the current history",
            )

        rows = {}
        row_pattern = re.compile(
            r"^\| `([^`]+)` \| `([0-9a-f]{64})` \| [^|]* \| "
            r"`?(PROMOTED|NO_CHANGE|REVERTED|BLOCKED)`?[^|]* \| [^|]* \|$",
            re.MULTILINE,
        )
        for name, baseline, result in row_pattern.findall(report):
            rows[name] = (baseline, result)
        self.assertEqual(set(rows), set(ACTIVE_SKILLS))
        self.assertEqual(
            {name for name, (_, result) in rows.items() if result == "PROMOTED"},
            {"nobrainer-ultra", "nobrainer-autoimprove", "nobrainer-review"},
        )

        bindings = (
            ("ULTRA_SHA256", "skills/nobrainer-ultra/SKILL.md"),
            ("REVIEW_SHA256", "skills/nobrainer-review/SKILL.md"),
            ("AUTOIMPROVE_SHA256", "skills/nobrainer-autoimprove/SKILL.md"),
            ("BOOTSTRAP_SHA256", "adapters/bootstrap.md"),
        )
        for label, relative in bindings:
            declared = re.search(
                rf"^{label}: ([0-9a-f]{{64}})$", report, re.MULTILINE
            )
            self.assertIsNotNone(declared)
            if has_git_repository:
                self.assertEqual(
                    git_sha256(source_ref, relative), declared.group(1)
                )
            if label in {
                "ULTRA_SHA256",
                "REVIEW_SHA256",
                "AUTOIMPROVE_SHA256",
                "BOOTSTRAP_SHA256",
            }:
                self.assertNotEqual(sha256(relative), declared.group(1))
            else:
                self.assertEqual(sha256(relative), declared.group(1))

        for pattern in (
            r"^DETERMINISTIC_SUITE: .*90/90 PASS$",
            r"^QUICK_VALIDATE: .*15/15 PASS$",
            r"^SECRET_SCAN: .*PASS$",
            r"^INDEPENDENT_REVIEW: CLEAN; .+$",
        ):
            self.assertIsNotNone(re.search(pattern, report, re.MULTILINE))
        self.assertIn("CLIENT_RUNTIME: NOT_VERIFIED", report)


if __name__ == "__main__":
    unittest.main()
