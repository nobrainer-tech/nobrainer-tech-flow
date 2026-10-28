from __future__ import annotations

import re
import unittest
from pathlib import Path

from scripts import validate_skills

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "skills" / "nobrainer-tech-flow" / "SKILL.md"
DONE_TOOL = ROOT / "mcp" / "src" / "tools" / "done.ts"


class HandoffBlockTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = ENTRY.read_text(encoding="utf-8")

    def test_entry_skill_requires_the_fixed_handoff_block(self) -> None:
        self.assertEqual([], validate_skills.handoff_block_errors(self.text))

    def test_each_missing_heading_is_reported(self) -> None:
        for label in validate_skills.HANDOFF_LINES:
            with self.subTest(label=label):
                broken = re.sub(rf"^{re.escape(label)}.*$", "", self.text, count=1, flags=re.M)
                errors = validate_skills.handoff_block_errors(broken)
                self.assertTrue(any(label in error for error in errors), errors)

    def test_a_removed_block_is_reported(self) -> None:
        broken = self.text.replace("End every non-trivial task with this handoff block.", "")
        self.assertEqual(
            ["entry skill: missing the required final handoff block"],
            validate_skills.handoff_block_errors(broken),
        )

    def test_checked_lines_pair_a_command_with_its_result(self) -> None:
        broken = self.text.replace("<command or check> -> <observed result>", "<command or check>")
        errors = validate_skills.handoff_block_errors(broken)
        self.assertTrue(any("->" in error for error in errors), errors)

    def test_gap_semantics_mirror_the_mcp_done_gate(self) -> None:
        self.assertIn("DONE_WITH_GAPS", DONE_TOOL.read_text(encoding="utf-8"))
        words = " ".join(self.text.split())
        self.assertIn("A listed gap means done with gaps, not done", words)
        broken = self.text.replace("DONE_WITH_GAPS", "DONE")
        self.assertIn(
            "entry skill: handoff block must name the DONE_WITH_GAPS meaning",
            validate_skills.handoff_block_errors(broken),
        )

    def test_done_gate_lists_doc_and_code_drift(self) -> None:
        words = " ".join(self.text.split())
        verify = words[words.index("## `VERIFY` and `RECEIVE_AUDIT`") : words.index("## Correction hooks")]
        self.assertIn("where docs and code disagree", verify)


if __name__ == "__main__":
    unittest.main()
