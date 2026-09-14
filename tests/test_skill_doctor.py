from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "nobrainer-skill-doctor" / "SKILL.md"
ASTRA = ROOT / "skills" / "nobrainer-skill-doctor" / "references" / "astra.md"


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError(f"{path}: frontmatter must start on line 1")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise AssertionError(f"{path}: frontmatter is not closed") from exc

    values: dict[str, str] = {}
    for line in lines[1:end]:
        match = re.fullmatch(r"([a-zA-Z0-9_-]+):\s*(?:\"(.*)\"|(.*))", line)
        if match is None:
            raise AssertionError(f"{path}: unsupported frontmatter line: {line}")
        values[match.group(1)] = match.group(2) if match.group(2) is not None else match.group(3)
    return values


def skill_text() -> str:
    if not SKILL.is_file():
        raise AssertionError(f"missing public doctor entrypoint: {SKILL}")
    return SKILL.read_text(encoding="utf-8")


class SkillDoctorContractTests(unittest.TestCase):
    def test_entrypoint_defines_a_narrow_portable_read_only_owner(self) -> None:
        if not SKILL.is_file():
            self.fail(f"missing public doctor entrypoint: {SKILL}")
        values = frontmatter(SKILL)
        self.assertEqual({"name", "description"}, set(values))
        self.assertEqual("nobrainer-skill-doctor", values["name"])
        self.assertTrue(values["description"].startswith("Use when"))
        self.assertIn("nb-skill-doctor", values["description"])

        text = skill_text()
        for term in (
            "read-only",
            "portfolio",
            "discovery",
            "behavior",
            "PARTIAL",
            "nobrainer-review",
            "nobrainer-codex-context",
            "nobrainer-build",
            "nobrainer-team",
        ):
            self.assertIn(term, text)

    def test_completion_contract_covers_positive_negative_and_authority_cases(self) -> None:
        text = skill_text()
        for term in (
            "non-trigger",
            "substantial",
            "external action",
            "coverage",
            "UNREAD",
            "UNAVAILABLE",
            "does not prove",
            "Do not run every case for every skill",
            "exact file and line",
            "regression",
        ):
            self.assertIn(term, text)

    def test_reference_is_public_and_attributed(self) -> None:
        self.assertTrue(ASTRA.is_file())
        text = ASTRA.read_text(encoding="utf-8")
        self.assertIn("https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra", text)
        for forbidden in (
            "/" + "Users/",
            "nobrainer-" + "tech@",
            "--dangerously-" + "skip-permissions",
        ):
            self.assertNotIn(forbidden, text)


if __name__ == "__main__":
    unittest.main()
