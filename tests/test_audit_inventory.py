import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


AUDIT_PATH = Path(__file__).resolve().parents[1] / "skills/nobrainer-skill-doctor/scripts/audit.py"


def load_audit_module():
    spec = importlib.util.spec_from_file_location("audit_under_test", AUDIT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load {AUDIT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AuditInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = load_audit_module()

    def test_regular_directory_is_inventoried_without_source_content(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "SKILL.md").write_text(
                "MUST read this before implementation\nUNSAFE_FIXTURE_CONTENT\n",
                encoding="utf-8",
            )
            nested = root / "nested"
            nested.mkdir()
            (nested / "AGENTS.md").write_text(
                "approval required\n", encoding="utf-8"
            )

            result = self.audit.scan(root)

            self.assertEqual(result["status"], "inventoried")
            self.assertEqual(
                {
                    Path(item["path"]).relative_to(root.resolve())
                    for item in result["files"]
                },
                {Path("SKILL.md"), Path("nested/AGENTS.md")},
            )
            self.assertEqual(result["skipped"], [])
            self.assertNotIn("UNSAFE_FIXTURE_CONTENT", json.dumps(result))

    def test_directory_symlink_is_reported_and_makes_inventory_partial(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "SKILL.md").write_text("regular\n", encoding="utf-8")
            linked_target = root / "linked-target"
            linked_target.mkdir()
            (linked_target / "AGENTS.md").write_text(
                "linked content\n", encoding="utf-8"
            )
            linked_directory = root / "linked-directory"
            linked_directory.symlink_to(linked_target, target_is_directory=True)

            result = self.audit.scan(root)

            self.assertEqual(result["status"], "partial")
            skipped_paths = {item["path"] for item in result["skipped"]}
            expected_link_path = str(root.resolve() / "linked-directory")
            self.assertIn(expected_link_path, skipped_paths)
            self.assertTrue(
                any(
                    "symlink" in item["reason"].lower()
                    for item in result["skipped"]
                    if item["path"] == expected_link_path
                )
            )
            self.assertNotIn(str(root.resolve() / "linked-directory" / "AGENTS.md"), {
                item["path"] for item in result["files"]
            })

    def test_broken_directory_symlink_is_reported_and_makes_inventory_partial(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            broken_directory = root / "broken-directory"
            broken_directory.symlink_to(
                root / "missing-target", target_is_directory=True
            )

            result = self.audit.scan(root)

            self.assertEqual(result["status"], "partial")
            self.assertIn(
                str(root.resolve() / "broken-directory"),
                {item["path"] for item in result["skipped"]},
            )

    def test_missing_root_is_reported_as_missing(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_root = Path(temporary_directory) / "not-present"

            result = self.audit.scan(missing_root)

            self.assertEqual(result["status"], "missing")
            self.assertEqual(result["files"], [])
            self.assertEqual(result["skipped"], [])

    def test_explicit_prompt_file_is_scanned_without_directory_walk(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            prompt_file = Path(temporary_directory) / "prompt.txt"
            prompt_file.write_text(
                "MUST inspect this prompt\nUNSAFE_FIXTURE_CONTENT\n",
                encoding="utf-8",
            )

            with patch.object(
                self.audit.os,
                "walk",
                side_effect=AssertionError("explicit files must not be walked"),
            ):
                result = self.audit.scan(prompt_file)

            self.assertEqual(result["status"], "inventoried")
            self.assertEqual(
                [item["path"] for item in result["files"]],
                [str(prompt_file.resolve())],
            )
            self.assertEqual(result["files"][0]["candidates"], [{"line": 1, "code": "mandatory-process"}])
            self.assertNotIn("UNSAFE_FIXTURE_CONTENT", json.dumps(result))

    def test_denied_walk_is_reported_as_partial_without_error_text(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            def denied_walk(_root, **kwargs):
                callback = kwargs.get("onerror")
                if callback is not None:
                    callback(PermissionError(13, "permission denied", str(root / "restricted")))
                return ()

            with patch.object(self.audit.os, "walk", side_effect=denied_walk):
                result = self.audit.scan(root)

            self.assertEqual(result["status"], "partial")
            self.assertEqual(result["files"], [])
            self.assertEqual(
                result["skipped"],
                [{"path": str(root / "restricted"), "reason": "PermissionError"}],
            )
            self.assertNotIn("permission denied", json.dumps(result).lower())


if __name__ == "__main__":
    unittest.main()
