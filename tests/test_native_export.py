"""The Claude-directory copy: scripts/export_native.py builds it, verify_native_export.py checks it."""

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import export_native  # noqa: E402
import verify_native_export as verifier  # noqa: E402

COMMIT = "0" * 40


def quiet(main, args: list[str]) -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return main(args)


def current_copy() -> dict[str, bytes]:
    """The copy-only files a real nobrainer-tech-flow-plugin checkout holds before an export."""

    manifest = {"name": "nobrainer-tech-flow", "description": "old", "version": "0.0.1",
                "author": {"name": "NoBrainer Tech"}, "homepage": "https://github.com/nobrainer-tech/nobrainer-tech-flow",
                "displayName": "nobrainer-tech-flow",
                "privacyPolicyUrl": "https://example.invalid/privacy", "supportUrl": "https://example.invalid/support",
                "termsOfServiceUrl": "https://example.invalid/terms"}
    market = {"name": "nobrainer-tech", "plugins": [{"name": "nobrainer-tech-flow", "source": "./", "version": "0.0.1"}]}
    return {
        "README.md": b"See https://github.com/nobrainer-tech/nobrainer-tech-flow/releases/tag/v0.0.1 and /blob/v0.0.1/docs/INSTALL.md.\n",
        "AGENTS.md": b"# Distribution rules\n",
        ".claude-plugin/icon.png": (ROOT / "assets/plugin-logo.png").read_bytes(),
        ".claude-plugin/marketplace.json": json.dumps(market).encode(),
        ".claude-plugin/plugin.json": json.dumps(manifest).encode(),
        ".github/workflows/validate.yml": b"name: Verify native distribution\non: [push]\n",
        "SOURCE.json": json.dumps({"tag": "v0.0.1"}).encode(),
    }


class NativeExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.scratch = tempfile.TemporaryDirectory()
        output = Path(cls.scratch.name) / "plugin.zip"
        subprocess.run([sys.executable, str(ROOT / "scripts/build_plugin.py"), "--output", str(output)],
                       check=True, capture_output=True)
        cls.payload = output.read_bytes()
        with zipfile.ZipFile(io.BytesIO(cls.payload)) as archive:
            cls.release = {n: archive.read(n) for n in archive.namelist() if not n.endswith("/")}
        cls.tag = "v" + cls.release["skills/nobrainer-tech-flow/VERSION"].decode().strip()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.scratch.cleanup()

    def export(self) -> Path:
        out = Path(tempfile.mkdtemp(dir=self.scratch.name))
        export_native.write(export_native.build(self.payload, self.tag, COMMIT, current_copy()), out)
        return out

    def problems(self, out: Path) -> list[str]:
        return verifier.verify(out, self.payload, json.loads((out / "SOURCE.json").read_text()))

    def test_an_export_passes_the_verifier(self) -> None:
        self.assertEqual([], self.problems(self.export()))

    def test_the_export_leaves_out_exactly_the_scripts(self) -> None:
        out = self.export()
        kept = {p.relative_to(out).as_posix() for p in (out / "skills").rglob("*") if p.is_file()}
        left_out = {n for n in self.release if n.startswith("skills/")} - kept
        self.assertTrue(left_out)
        self.assertTrue(all("/scripts/" in name and name.endswith(".py") for name in left_out), left_out)
        self.assertFalse(any(p.suffix == ".py" or p.read_bytes().startswith(b"#!") for p in out.rglob("*") if p.is_file()))

    def test_the_copy_keeps_its_listing_fields_and_takes_the_release_version(self) -> None:
        out = self.export()
        manifest = json.loads((out / ".claude-plugin/plugin.json").read_text())
        release = json.loads(self.release[".claude-plugin/plugin.json"])
        self.assertEqual(self.tag[1:], manifest["version"])
        self.assertEqual(release["description"], manifest["description"])
        self.assertEqual("https://example.invalid/privacy", manifest["privacyPolicyUrl"])
        self.assertEqual("https://github.com/nobrainer-tech/nobrainer-tech-flow", manifest["homepage"])
        self.assertNotIn("icon", manifest)
        market = json.loads((out / ".claude-plugin/marketplace.json").read_text())
        self.assertEqual([self.tag[1:]], [p["version"] for p in market["plugins"]])
        self.assertIn(f"/tag/{self.tag}".encode(), (out / "README.md").read_bytes())
        source = json.loads((out / "SOURCE.json").read_text())
        self.assertEqual((self.tag, COMMIT), (source["tag"], source["commit"]))

    def test_the_verifier_refuses_a_python_file(self) -> None:
        out = self.export()
        (out / "skills/nobrainer-tech-flow/scripts").mkdir()
        (out / "skills/nobrainer-tech-flow/scripts/check_flow_update.py").write_bytes(
            self.release["skills/nobrainer-tech-flow/scripts/check_flow_update.py"])
        self.assertIn("skills/nobrainer-tech-flow/scripts/check_flow_update.py: type .py is not allowed", self.problems(out))

    def test_the_verifier_refuses_a_file_that_starts_with_a_shebang(self) -> None:
        out = self.export()
        (out / "README.md").write_bytes(b"#!/bin/sh\necho hi\n")
        (out / "run").write_bytes(b"#!/usr/bin/env python3\n")
        problems = self.problems(out)
        self.assertIn("README.md: starts with #!", problems)
        self.assertIn("run: starts with #!", problems)

    def test_the_verifier_refuses_one_changed_byte_in_a_skill(self) -> None:
        out = self.export()
        skill = out / "skills/nobrainer-review/SKILL.md"
        data = bytearray(skill.read_bytes())
        data[-2] ^= 1
        skill.write_bytes(bytes(data))
        self.assertEqual(["skills/nobrainer-review/SKILL.md: differs from the release ZIP"], self.problems(out))

    def test_the_verifier_refuses_package_files_and_missing_skill_files(self) -> None:
        out = self.export()
        (out / "package.json").write_text("{}")
        (out / "skills/nobrainer-review/SKILL.md").unlink()
        problems = self.problems(out)
        self.assertIn("package.json: package manager file", problems)
        self.assertIn("skills/nobrainer-review/SKILL.md: missing; only files of a refused type may be left out", problems)

    def test_the_verifier_refuses_text_that_is_not_what_its_name_says(self) -> None:
        out = self.export()
        (out / "notes.txt").write_bytes(b"caf\xe9\n")
        (out / "NOTICE").write_bytes(b"line\x00\n")
        (out / "extra.json").write_text("{not json")
        (out / "pnpm-workspace.yaml").write_text("packages: []\n")
        (out / ".gitignore").write_text("*.pyc\n")
        problems = self.problems(out)
        self.assertIn("notes.txt: is not UTF-8 text", problems)
        self.assertIn("NOTICE: holds a NUL byte", problems)
        self.assertIn("extra.json: is not valid JSON", problems)
        self.assertIn("pnpm-workspace.yaml: package manager file", problems)
        self.assertFalse([p for p in problems if p.startswith(".gitignore")])

    def test_the_verifier_refuses_a_disguised_image(self) -> None:
        out = self.export()
        (out / ".claude-plugin/icon.png").write_bytes(b"#!/bin/sh\n")
        self.assertIn(".claude-plugin/icon.png: not a PNG image", self.problems(out))

    def test_the_command_line_round_trip(self) -> None:
        zip_path = Path(self.scratch.name) / "plugin.zip"
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / "copy"
            for name, data in current_copy().items():
                (copy / name).parent.mkdir(parents=True, exist_ok=True)
                (copy / name).write_bytes(data)
            out = Path(folder) / "out"
            self.assertEqual(0, quiet(export_native.main, [str(zip_path), "--tag", self.tag, "--commit", COMMIT,
                                                    "--copy", str(copy), "--out", str(out)]))
            self.assertEqual(0, quiet(verifier.main, [str(out), "--zip", str(zip_path), "--offline"]))
            self.assertEqual(1, quiet(export_native.main, [str(zip_path), "--tag", self.tag, "--commit", COMMIT,
                                                    "--copy", str(copy), "--out", str(out)]))

    def test_an_archive_path_that_escapes_the_copy_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            # skills/../../victim.txt under nested/out resolves to nested/victim.txt.
            victim = base / "nested" / "victim.txt"
            victim.parent.mkdir()
            victim.write_text("original\n")
            bad_zip = base / "bad.zip"
            with zipfile.ZipFile(io.BytesIO(self.payload)) as source, zipfile.ZipFile(bad_zip, "w") as target:
                for item in source.infolist():
                    target.writestr(item, source.read(item.filename))
                target.writestr("skills/../../victim.txt", "overwritten\n")
            copy = base / "copy"
            for name, data in current_copy().items():
                (copy / name).parent.mkdir(parents=True, exist_ok=True)
                (copy / name).write_bytes(data)
            out = base / "nested" / "out"
            self.assertEqual(1, quiet(export_native.main, [str(bad_zip), "--tag", self.tag, "--commit", COMMIT,
                                                          "--copy", str(copy), "--out", str(out)]))
            self.assertEqual("original\n", victim.read_text())
            self.assertFalse(out.exists())
            with self.assertRaisesRegex(ValueError, "unsafe archive path"):
                export_native.build(bad_zip.read_bytes(), self.tag, COMMIT, current_copy())

    def test_an_in_place_export_needs_a_clean_checkout_and_keeps_git(self) -> None:
        zip_path = Path(self.scratch.name) / "plugin.zip"
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder)
            for name, data in current_copy().items():
                (copy / name).parent.mkdir(parents=True, exist_ok=True)
                (copy / name).write_bytes(data)
            (copy / "stale.py").write_text("print(1)\n")
            git = ["git", "-C", str(copy), "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
            subprocess.run([*git, "init", "-q"], check=True)
            subprocess.run([*git, "add", "-A"], check=True)
            subprocess.run([*git, "commit", "-qm", "fixture"], check=True)
            (copy / "AGENTS.md").write_text("uncommitted\n")
            args = [str(zip_path), "--tag", self.tag, "--commit", COMMIT, "--copy", str(copy)]
            self.assertEqual(1, quiet(export_native.main, args))
            self.assertEqual("uncommitted\n", (copy / "AGENTS.md").read_text())
            subprocess.run([*git, "checkout", "-q", "--", "AGENTS.md"], check=True)
            self.assertEqual(0, quiet(export_native.main, args))
            self.assertTrue((copy / ".git").is_dir())
            self.assertFalse((copy / "stale.py").exists())
            self.assertEqual([], verifier.verify(copy, self.payload, json.loads((copy / "SOURCE.json").read_text())))


if __name__ == "__main__":
    unittest.main()
