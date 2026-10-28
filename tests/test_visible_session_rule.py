from __future__ import annotations

from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "skills" / "nobrainer-tech-flow"
CANONICAL = (
    "visible conversations require an explicit user request or an authorized main-agent restart; "
    "isolation, reuse or handoff alone never authorize one"
)
ANCHOR = "SKILL.md#choose-the-smallest-workflow"
REPLACED = (
    FLOW / "references" / "long-run-state.md",
    FLOW / "references" / "setup.md",
    FLOW / "references" / "routing.md",
    FLOW / "references" / "delivery.md",
    ROOT / "skills" / "nobrainer-team" / "SKILL.md",
)


def words(path: Path) -> str:
    return " ".join(path.read_text(encoding="utf-8").split())


class VisibleSessionRuleTests(unittest.TestCase):
    def test_flow_skill_holds_the_single_canonical_rule(self) -> None:
        self.assertEqual(1, words(FLOW / "SKILL.md").count(CANONICAL))

    def test_former_copies_link_to_the_canonical_rule_instead_of_restating_it(self) -> None:
        for path in REPLACED:
            with self.subTest(path=path.relative_to(ROOT)):
                text = words(path)
                self.assertNotIn("MAIN restart", text)
                self.assertIn(ANCHOR, text)


if __name__ == "__main__":
    unittest.main()
