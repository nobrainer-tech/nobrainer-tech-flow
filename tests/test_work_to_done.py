from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "skills" / "nobrainer-tech-flow" / "SKILL.md"


def section(text: str, start: str, end: str) -> str:
    return text[text.index(start) : text.index(end)]


class WorkToDoneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = " ".join(ENTRY.read_text(encoding="utf-8").split())

    def test_contract_sits_before_workflow_selection(self) -> None:
        self.assertLess(self.text.index("## Work to done"), self.text.index("## Choose the smallest workflow"))

    def test_intent_decides_between_doing_and_answering(self) -> None:
        contract = section(self.text, "## Work to done", "## Choose the smallest workflow")
        self.assertIn("A request to do something means doing it", contract)
        self.assertIn("gets an answer and no unrequested changes", contract)

    def test_scope_is_neither_shrunk_nor_grown(self) -> None:
        contract = section(self.text, "## Work to done", "## Choose the smallest workflow")
        self.assertIn("including ones added mid-task", contract)
        self.assertIn("Never deliver the easier part as the whole", contract)
        self.assertIn("grow the task into your own project", contract)

    def test_autonomy_stays_inside_authority(self) -> None:
        contract = section(self.text, "## Work to done", "## Choose the smallest workflow")
        self.assertIn("known and authorized, take it", contract)
        self.assertIn("reuse permission already given", contract)
        self.assertIn("Silence is never consent", contract)
        self.assertIn("A real denial or missing access stays a limit", contract)
        # The explicit approval gates still exist after the contract was added.
        self.assertIn("Autonomy does not expand authority", self.text)

    def test_failure_is_diagnosed_not_repeated(self) -> None:
        contract = section(self.text, "## Work to done", "## Choose the smallest workflow")
        self.assertIn("never repeat an identical attempt", contract)

    def test_finish_check_runs_before_the_handoff_block(self) -> None:
        check = section(self.text, "Finish check:", "End every non-trivial task with this handoff block.")
        self.assertIn("would only promise an action that was requested, is possible and is allowed, do it first", check)
        self.assertIn("Never call a partial result done", check)
        self.assertIn("promise background work that nothing started", check)
        self.assertIn("the exact unblock condition", check)


if __name__ == "__main__":
    unittest.main()
