import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
NPM = shutil.which("npm")


@unittest.skipUnless(NODE and NPM, "Node and npm are needed for packed-distribution checks")
class NpmDistributionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="flow-npm-proof-")
        cls.folder = Path(cls.temp.name).resolve()
        result = subprocess.run([NPM, "pack", "--json", "--pack-destination", str(cls.folder)],
                                cwd=ROOT, capture_output=True, text=True, check=True)
        cls.archive = cls.folder / json.loads(result.stdout)[0]["filename"]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.scope = tempfile.TemporaryDirectory(dir=self.folder, prefix="case-")
        self.folder_case = Path(self.scope.name)
        self.addCleanup(self.scope.cleanup)
        self.extract = self.folder_case / "a"
        self.extract.mkdir()
        with tarfile.open(self.archive) as archive:
            archive.extractall(self.extract, filter="data")
        self.package = self.extract / "package"
        self.home = self.folder_case / "profile"

    def call(self, *args, package=None, env=None):
        source = package or self.package
        return subprocess.run([NODE, str(source / "bin/nobrainer-tech-flow.mjs"), *args],
                              cwd=self.folder_case, env=env or {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                              capture_output=True, text=True, timeout=60)

    def install(self, *args, package=None):
        return self.call("--client", "codex", "--home", str(self.home), *args, package=package)

    def test_help_and_version_need_no_python_and_install_fails_before_writes(self):
        env = {**os.environ, "PATH": str(self.folder_case / "absent")}
        self.assertEqual(0, self.call("--help", env=env).returncode)
        self.assertEqual(0, self.call("--version", env=env).returncode)
        result = self.call("--client", "codex", "--home", str(self.home), "--apply", env=env)
        self.assertEqual(2, result.returncode)
        self.assertIn("Python 3.11+", result.stderr)
        self.assertFalse(self.home.exists())

    def test_preview_then_apply_survives_npm_cache_removal_and_undo_from_new_extraction(self):
        preview = self.install()
        self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
        self.assertFalse(self.home.exists())
        result = self.install("--apply")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        skills = self.home / ".agents/skills"
        self.assertEqual(18, len(list(skills.glob("*/SKILL.md"))))
        # The release is kept beside ~/.nobrainer-tech-flow, where a Git clone may live, not in it.
        retained = (self.home / ".nobrainer-tech-flow-npm" / self.version()).resolve()
        self.assertEqual(retained / "skills" / "nobrainer-tech-flow", (skills / "nobrainer-tech-flow").resolve())
        self.assertFalse((self.home / ".nobrainer-tech-flow").exists())
        self.assertTrue((skills / "nobrainer-tech-flow/references/communication.md").is_file())
        shutil.rmtree(self.extract)
        self.assertTrue((skills / "nobrainer-tech-flow/SKILL.md").is_file())
        extraction_b = self.folder_case / "b"
        extraction_b.mkdir()
        with tarfile.open(self.archive) as archive:
            archive.extractall(extraction_b, filter="data")
        def profile_snapshot():
            return {str(path.relative_to(self.home)): ("link", os.readlink(path)) if path.is_symlink()
                    else ("file", path.read_bytes()) if path.is_file() else ("directory", None)
                    for path in self.home.rglob("*")}
        before = profile_snapshot()
        ordinary_preview = self.install(package=extraction_b / "package")
        self.assertEqual(0, ordinary_preview.returncode, ordinary_preview.stdout + ordinary_preview.stderr)
        self.assertEqual(before, profile_snapshot())
        repeat = self.install("--apply", package=extraction_b / "package")
        self.assertEqual(0, repeat.returncode, repeat.stdout + repeat.stderr)
        undo_preview = self.install("--undo", package=extraction_b / "package")
        self.assertEqual(0, undo_preview.returncode, undo_preview.stdout + undo_preview.stderr)
        self.assertTrue((skills / "nobrainer-tech-flow/SKILL.md").is_file())
        undo = self.install("--undo", "--apply", package=extraction_b / "package")
        self.assertEqual(0, undo.returncode, undo.stdout + undo.stderr)
        self.assertFalse((skills / "nobrainer-tech-flow").exists())
        # A second undo finds nothing recorded: it succeeds and writes nothing.
        after_undo = profile_snapshot()
        for extra in ((), ("--apply",)):
            second = self.install("--undo", *extra, package=extraction_b / "package")
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            self.assertIn("NOTHING TO UNDO", second.stdout)
            self.assertEqual(after_undo, profile_snapshot())

    def test_undo_before_any_install_succeeds_without_retained_release_or_writes(self):
        for extra in ((), ("--apply",)):
            result = self.install("--undo", *extra)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("NOTHING TO UNDO", result.stdout)
            self.assertFalse(self.home.exists())

    def test_undo_without_a_record_ignores_whatever_the_retained_storage_holds(self):
        # A partial or modified copy is no reason to refuse when nothing is recorded to undo.
        partial = self.home / ".nobrainer-tech-flow-npm" / self.version()
        partial.mkdir(parents=True)
        (partial / "left-over.txt").write_text("partial copy\n", encoding="utf-8")
        for extra in ((), ("--apply",)):
            result = self.install("--undo", *extra)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("NOTHING TO UNDO", result.stdout)
            self.assertEqual(["left-over.txt"], sorted(path.name for path in partial.iterdir()))

    def test_undo_of_a_setup_from_an_earlier_release_names_where_that_release_kept_its_files(self):
        (self.home / ".nobrainer-tech-flow" / "npm" / "2.3.1").mkdir(parents=True)
        record = self.home / ".nobrainer-flow-onboarding-codex.json"
        record.write_text("{}\n", encoding="utf-8")
        result = self.install("--undo", "--apply")
        self.assertEqual(3, result.returncode, result.stdout + result.stderr)
        self.assertIn("HINT: an earlier release kept its files in", result.stderr)
        self.assertEqual("{}\n", record.read_text(encoding="utf-8"))

    def version(self):
        return json.loads((self.package / "package.json").read_text(encoding="utf-8"))["version"]

    def test_undo_with_a_record_but_no_retained_release_still_stops(self):
        self.home.mkdir()
        record = self.home / ".nobrainer-flow-onboarding-codex.json"
        record.write_text("{}\n", encoding="utf-8")
        result = self.install("--undo", "--apply")
        self.assertEqual(3, result.returncode, result.stdout + result.stderr)
        self.assertIn("retained npm release is missing", result.stderr)
        self.assertEqual("{}\n", record.read_text(encoding="utf-8"))

    def test_foreign_client_target_is_preserved(self):
        target = self.home / ".agents/skills/nobrainer-tech-flow"
        target.mkdir(parents=True)
        (target / "SKILL.md").write_text("foreign")
        before = (target / "SKILL.md").read_bytes()
        result = self.install("--apply")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(before, (target / "SKILL.md").read_bytes())
        self.assertFalse((self.home / ".agents/skills/nobrainer-writing").exists())

    def test_plugin_builder_preserves_dangling_output_symlink(self):
        output = self.folder_case / "plugin.zip"
        foreign = self.folder_case / "foreign.zip"
        output.symlink_to(foreign)
        result = subprocess.run([shutil.which("python3"), str(ROOT / "scripts/build_plugin.py"), "--output", str(output)],
                                capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertTrue(output.is_symlink())
        self.assertEqual(str(foreign), os.readlink(output))
        self.assertFalse(foreign.exists())

    def test_plugin_bundle_is_hook_free_and_skills_are_exact_source_bytes(self):
        output = self.folder_case / "plugin.zip"
        result = subprocess.run([shutil.which("python3"), str(ROOT / "scripts/build_plugin.py"), "--output", str(output)],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        with zipfile.ZipFile(output) as archive:
            self.assertFalse(any(p.startswith("hooks/") or p.endswith(".app.json") for p in archive.namelist()))
            self.assertFalse(any(p.startswith("docs/evals/") or p.endswith((".zip", ".tgz", ".tar", ".gz")) for p in archive.namelist()))
            self.assertNotIn("hooks", json.loads(archive.read(".claude-plugin/plugin.json")))
            skills = [name for name in archive.namelist() if name.startswith("skills/") and name.endswith("/SKILL.md")]
            self.assertEqual(18, len(skills))
            for name in skills:
                self.assertEqual((ROOT / name).read_bytes(), archive.read(name))
            manifest = json.loads(archive.read("plugin.json"))
            self.assertEqual("nobrainer-tech-flow", manifest["name"])
            icon = manifest["extensions"]["com.openai"]["interface"]["logo"].removeprefix("./")
            self.assertIn(icon, archive.namelist())
