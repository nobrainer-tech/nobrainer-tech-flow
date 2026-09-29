from __future__ import annotations

import importlib.util
import io
import re
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "install_skills.py"


class InstallerTests(unittest.TestCase):
    def run_installer(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(INSTALLER), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_dry_run_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            result = self.run_installer(
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-tech-flow",
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("SYMLINK: nobrainer-tech-flow", result.stdout)
            self.assertNotIn("LEGACY", result.stdout)
            self.assertIn("DRY_RUN", result.stdout)
            self.assertFalse(destination.exists())

    def test_apply_and_idempotent_readback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            args = (
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-tech-flow",
                "--apply",
            )
            first = self.run_installer(*args)
            second = self.run_installer(*args)
            target = destination / "nobrainer-tech-flow"
            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(0, second.returncode, second.stderr)
            self.assertTrue(target.is_symlink())
            self.assertTrue((target / "SKILL.md").is_file())
            self.assertIn("1 unchanged", second.stdout)

    def test_conflict_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "skills" / "nobrainer-tech-flow"
            target.mkdir(parents=True)
            marker = target / "keep.txt"
            marker.write_text("owned by user\n", encoding="utf-8")
            result = self.run_installer(
                "--client",
                "codex",
                "--dest",
                str(target.parent),
                "--skill",
                "nobrainer-tech-flow",
                "--apply",
            )
            self.assertEqual(3, result.returncode)
            self.assertEqual("owned by user\n", marker.read_text(encoding="utf-8"))

    def test_relocated_legacy_symlink_requires_explicit_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            target = destination / "nobrainer-browser"
            old_source = ROOT / "nobrainer-browser"
            target.symlink_to(old_source, target_is_directory=True)

            refused = self.run_installer(
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-browser",
                "--apply",
            )
            self.assertEqual(3, refused.returncode)
            self.assertIn("legacy symlink", refused.stderr)
            self.assertEqual(str(old_source), str(target.readlink()))

            migrated = self.run_installer(
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-browser",
                "--migrate-legacy",
                "--apply",
            )
            self.assertEqual(0, migrated.returncode, migrated.stderr)
            self.assertIn("MIGRATE", migrated.stdout)
            self.assertEqual(
                (ROOT / "skills" / "nobrainer-browser").resolve(),
                target.resolve(),
            )

    def test_unknown_symlink_remains_a_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            target = destination / "nobrainer-browser"
            foreign = Path(temp) / "foreign-target"
            target.symlink_to(foreign, target_is_directory=True)
            result = self.run_installer(
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-browser",
                "--migrate-legacy",
                "--apply",
            )
            self.assertEqual(3, result.returncode)
            self.assertEqual(foreign, target.readlink())

    def test_renamed_legacy_alias_is_migrated_only_with_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            legacy = destination / "karpathy-auto-improver"
            old_source = ROOT / "karpathy-auto-improver"
            legacy.symlink_to(old_source, target_is_directory=True)

            refused = self.run_installer(
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-autoimprove",
                "--apply",
            )
            self.assertEqual(3, refused.returncode)
            self.assertIn("LEGACY_ALIAS", refused.stdout)
            self.assertTrue(legacy.is_symlink())
            self.assertFalse((destination / "nobrainer-autoimprove").exists())

            migrated = self.run_installer(
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-autoimprove",
                "--migrate-legacy",
                "--apply",
            )
            canonical = destination / "nobrainer-autoimprove"
            self.assertEqual(0, migrated.returncode, migrated.stderr)
            self.assertIn("MIGRATE_ALIAS", migrated.stdout)
            self.assertFalse(legacy.exists())
            self.assertFalse(legacy.is_symlink())
            self.assertEqual(
                (ROOT / "skills" / "nobrainer-autoimprove").resolve(),
                canonical.resolve(),
            )

    def test_previous_skills_layout_alias_is_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            legacy = destination / "deep-audit"
            legacy.symlink_to(
                ROOT / "skills" / "deep-audit",
                target_is_directory=True,
            )

            result = self.run_installer(
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-review",
                "--migrate-legacy",
                "--apply",
            )

            canonical = destination / "nobrainer-review"
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("MIGRATE_ALIAS: deep-audit", result.stdout)
            self.assertFalse(legacy.exists())
            self.assertFalse(legacy.is_symlink())
            self.assertEqual(
                (ROOT / "skills" / "nobrainer-review").resolve(),
                canonical.resolve(),
            )

    def test_relative_legacy_alias_is_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = (Path(temp) / "skills").resolve()
            destination.mkdir()
            legacy = destination / "karpathy-auto-improver"
            relative_source = os.path.relpath(
                ROOT / "karpathy-auto-improver", destination
            )
            legacy.symlink_to(relative_source, target_is_directory=True)

            result = self.run_installer(
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-autoimprove",
                "--migrate-legacy",
                "--apply",
            )

            canonical = destination / "nobrainer-autoimprove"
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("MIGRATE_ALIAS: karpathy-auto-improver", result.stdout)
            self.assertFalse(legacy.exists())
            self.assertFalse(legacy.is_symlink())
            self.assertEqual(
                (ROOT / "skills" / "nobrainer-autoimprove").resolve(),
                canonical.resolve(),
            )

    def test_canonical_target_linked_to_renamed_predecessor_is_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            canonical = destination / "nobrainer-autoimprove"
            old_source = ROOT / "karpathy-auto-improver"
            canonical.symlink_to(old_source, target_is_directory=True)

            result = self.run_installer(
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-autoimprove",
                "--migrate-legacy",
                "--apply",
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("MIGRATE: nobrainer-autoimprove", result.stdout)
            self.assertEqual(
                (ROOT / "skills" / "nobrainer-autoimprove").resolve(),
                canonical.resolve(),
            )

    def test_playwright_cli_alias_migrates_into_browser(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            legacy = destination / "playwright-cli"
            legacy.symlink_to(ROOT / "playwright-cli", target_is_directory=True)

            result = self.run_installer(
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-browser",
                "--migrate-legacy",
                "--apply",
            )

            canonical = destination / "nobrainer-browser"
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("MIGRATE_ALIAS: playwright-cli", result.stdout)
            self.assertFalse(legacy.exists())
            self.assertFalse(legacy.is_symlink())
            self.assertEqual(
                (ROOT / "skills" / "nobrainer-browser").resolve(),
                canonical.resolve(),
            )

    def test_foreign_renamed_alias_blocks_migration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            legacy = destination / "karpathy-auto-improver"
            foreign = Path(temp) / "foreign-target"
            legacy.symlink_to(foreign, target_is_directory=True)

            result = self.run_installer(
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-autoimprove",
                "--migrate-legacy",
                "--apply",
            )
            self.assertEqual(3, result.returncode)
            self.assertIn("CONFLICT_ALIAS", result.stdout)
            self.assertEqual(foreign, legacy.readlink())
            self.assertFalse((destination / "nobrainer-autoimprove").exists())

    def test_failed_renamed_migration_restores_legacy_alias(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_legacy_rollback_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            legacy = destination / "karpathy-auto-improver"
            old_source = ROOT / "karpathy-auto-improver"
            canonical = destination / "nobrainer-autoimprove"
            legacy.symlink_to(old_source, target_is_directory=True)
            real_symlink = os.symlink
            symlink_calls = 0

            def fail_canonical_link(
                source: Path | str,
                target: Path | str,
                target_is_directory: bool = False,
            ) -> None:
                nonlocal symlink_calls
                symlink_calls += 1
                if symlink_calls == 1:
                    raise OSError("simulated canonical install failure")
                real_symlink(
                    source,
                    target,
                    target_is_directory=target_is_directory,
                )

            argv = [
                str(INSTALLER),
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-autoimprove",
                "--migrate-legacy",
                "--apply",
            ]
            stderr = io.StringIO()
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(module.os, "symlink", side_effect=fail_canonical_link),
                redirect_stdout(io.StringIO()),
                redirect_stderr(stderr),
            ):
                result = module.main()

            self.assertEqual(4, result)
            self.assertTrue(legacy.is_symlink())
            self.assertEqual(old_source, legacy.readlink())
            self.assertFalse(canonical.exists())
            self.assertFalse(canonical.is_symlink())
            self.assertIn("installation rolled back", stderr.getvalue())

    def test_alias_replacement_race_preserves_foreign_link(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_alias_race_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            legacy = destination / "karpathy-auto-improver"
            legacy.symlink_to(ROOT / "karpathy-auto-improver", target_is_directory=True)
            foreign = Path(temp) / "foreign-target"
            canonical = destination / "nobrainer-autoimprove"
            real_claim = module.claim_legacy_link

            def replace_then_claim(target: Path, legacy_name: str) -> Path:
                target.unlink()
                target.symlink_to(foreign, target_is_directory=True)
                return real_claim(target, legacy_name)

            argv = [
                str(INSTALLER),
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-autoimprove",
                "--migrate-legacy",
                "--apply",
            ]
            stderr = io.StringIO()
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(
                    module, "claim_legacy_link", side_effect=replace_then_claim
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(stderr),
            ):
                result = module.main()

            self.assertEqual(4, result)
            self.assertTrue(legacy.is_symlink())
            self.assertEqual(foreign, legacy.readlink())
            self.assertFalse(canonical.exists())
            self.assertFalse(canonical.is_symlink())
            self.assertEqual([], list(destination.glob(".nobrainer-migration-*")))
            self.assertIn("changed before claim", stderr.getvalue())

    def test_restore_race_never_overwrites_new_target(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_restore_race_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            claim_parent = destination / ".nobrainer-migration-test"
            claim_parent.mkdir(parents=True)
            target = destination / "karpathy-auto-improver"
            claim = claim_parent / target.name
            claimed_legacy = ROOT / "karpathy-auto-improver"
            concurrent_foreign = Path(temp) / "concurrent-foreign"
            claim.symlink_to(claimed_legacy, target_is_directory=True)
            expected = module.entry_fingerprint(claim)
            self.assertIsNotNone(expected)
            real_atomic_rename = module.atomic_rename_no_replace

            def install_concurrent_target_then_restore(
                source: Path,
                destination: Path,
            ) -> None:
                destination.symlink_to(
                    concurrent_foreign,
                    target_is_directory=True,
                )
                real_atomic_rename(source, destination)

            with (
                mock.patch.object(
                    module,
                    "atomic_rename_no_replace",
                    side_effect=install_concurrent_target_then_restore,
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "restore blocked"):
                    module.restore_claim(target, claim, expected)

            self.assertTrue(target.is_symlink())
            self.assertEqual(concurrent_foreign, target.readlink())
            self.assertTrue(claim.is_symlink())
            self.assertEqual(claimed_legacy, claim.readlink())

    def test_alias_replacement_race_preserves_foreign_directory_in_place(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_alias_directory_race_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            legacy = destination / "karpathy-auto-improver"
            legacy.symlink_to(ROOT / "karpathy-auto-improver", target_is_directory=True)
            canonical = destination / "nobrainer-autoimprove"
            real_claim = module.claim_legacy_link

            def replace_then_claim(target: Path, legacy_name: str) -> Path:
                target.unlink()
                target.mkdir()
                (target / "user-data.txt").write_text(
                    "owned by another process\n", encoding="utf-8"
                )
                return real_claim(target, legacy_name)

            argv = [
                str(INSTALLER),
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-autoimprove",
                "--migrate-legacy",
                "--apply",
            ]
            stderr = io.StringIO()
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(
                    module, "claim_legacy_link", side_effect=replace_then_claim
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(stderr),
            ):
                result = module.main()

            self.assertEqual(4, result)
            self.assertTrue(legacy.is_dir())
            self.assertEqual(
                "owned by another process\n",
                (legacy / "user-data.txt").read_text(encoding="utf-8"),
            )
            self.assertFalse(canonical.exists())
            self.assertFalse(canonical.is_symlink())
            self.assertEqual([], list(destination.glob(".nobrainer-migration-*")))
            self.assertIn("changed before claim", stderr.getvalue())

    def test_snapshot_rejects_symlink_replaced_during_fingerprint(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_snapshot_race_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            target = destination / "karpathy-auto-improver"
            target.symlink_to(ROOT / "karpathy-auto-improver", target_is_directory=True)
            foreign = Path(temp) / "foreign-target"
            real_lstat = module.Path.lstat
            replaced = False

            def replace_after_first_lstat(path: Path):
                nonlocal replaced
                metadata = real_lstat(path)
                if path == target and not replaced:
                    replaced = True
                    path.unlink()
                    path.symlink_to(foreign, target_is_directory=True)
                return metadata

            with mock.patch.object(
                module.Path, "lstat", new=replace_after_first_lstat
            ):
                snapshot = module.legacy_link_snapshot(
                    target, "karpathy-auto-improver"
                )

            self.assertIsNone(snapshot)
            self.assertTrue(target.is_symlink())
            self.assertEqual(foreign, target.readlink())

    def test_claim_race_restores_foreign_directory_moved_after_snapshot(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_claim_window_race_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            target = destination / "karpathy-auto-improver"
            target.symlink_to(ROOT / "karpathy-auto-improver", target_is_directory=True)
            real_rename = module.Path.rename
            replaced = False

            def replace_immediately_before_rename(path: Path, claim: Path):
                nonlocal replaced
                if path == target and not replaced:
                    replaced = True
                    path.unlink()
                    path.mkdir()
                    (path / "user-data.txt").write_text(
                        "owned by another process\n", encoding="utf-8"
                    )
                return real_rename(path, claim)

            with mock.patch.object(
                module.Path, "rename", new=replace_immediately_before_rename
            ):
                with self.assertRaisesRegex(RuntimeError, "replacement restored"):
                    module.claim_legacy_link(target, "karpathy-auto-improver")

            self.assertTrue(target.is_dir())
            self.assertEqual(
                "owned by another process\n",
                (target / "user-data.txt").read_text(encoding="utf-8"),
            )
            self.assertEqual([], list(destination.glob(".nobrainer-migration-*")))

    def test_directory_restore_never_overwrites_concurrent_target(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_directory_restore_race_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            claim_parent = destination / ".nobrainer-migration-test"
            claim = claim_parent / "legacy"
            target = destination / "legacy"
            claim.mkdir(parents=True)
            target.mkdir()
            (claim / "claimed.txt").write_text("claimed\n", encoding="utf-8")
            (target / "concurrent.txt").write_text("concurrent\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "restore blocked"):
                module.restore_claim(target, claim)

            self.assertEqual(
                "claimed\n", (claim / "claimed.txt").read_text(encoding="utf-8")
            )
            self.assertEqual(
                "concurrent\n",
                (target / "concurrent.txt").read_text(encoding="utf-8"),
            )

    def test_restore_moves_symlink_claim_without_duplicate_cleanup(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_atomic_restore_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            claim_parent = destination / ".nobrainer-migration-test"
            claim_parent.mkdir(parents=True)
            claim = claim_parent / "legacy"
            target = destination / "legacy"
            original = os.path.relpath(ROOT / "karpathy-auto-improver", destination)
            claim.symlink_to(original, target_is_directory=True)
            expected = module.entry_fingerprint(claim)
            self.assertIsNotNone(expected)

            with (
                mock.patch.object(
                    module.os,
                    "symlink",
                    side_effect=AssertionError("restore must move, not recreate"),
                ),
                mock.patch.object(
                    module.shutil,
                    "rmtree",
                    side_effect=AssertionError("restore must not delete a claim"),
                ),
            ):
                module.restore_claim(target, claim, expected)

            self.assertTrue(target.is_symlink())
            self.assertEqual(Path(original), target.readlink())
            self.assertFalse(claim.exists())
            self.assertFalse(claim.is_symlink())
            self.assertFalse(claim_parent.exists())

    def test_successful_migration_preserves_verified_recovery_backup(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_migration_backup_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            legacy = destination / "karpathy-auto-improver"
            original = ROOT / "karpathy-auto-improver"
            legacy.symlink_to(original, target_is_directory=True)

            argv = [
                str(INSTALLER),
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-autoimprove",
                "--migrate-legacy",
                "--apply",
            ]
            stdout = io.StringIO()
            stderr = io.StringIO()
            with (
                mock.patch.object(sys, "argv", argv),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                result = module.main()

            canonical = destination / "nobrainer-autoimprove"
            self.assertEqual(0, result)
            self.assertEqual(
                (ROOT / "skills" / "nobrainer-autoimprove").resolve(),
                canonical.resolve(),
            )
            claim_dirs = list(destination.glob(".nobrainer-migration-*"))
            self.assertEqual(1, len(claim_dirs))
            preserved = claim_dirs[0] / legacy.name
            self.assertTrue(preserved.is_symlink())
            self.assertEqual(original, preserved.readlink())
            self.assertIn("BACKUP_PRESERVED", stdout.getvalue())
            self.assertEqual("", stderr.getvalue())

    def test_interrupted_copy_removes_partial_target(self) -> None:
        spec = importlib.util.spec_from_file_location("skill_installer_under_test", INSTALLER)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            target = destination / "nobrainer-tech-flow"

            def interrupted_copy(
                source: Path,
                partial: Path,
                *,
                symlinks: bool = False,
                ignore: object = None,
            ) -> None:
                self.assertTrue(symlinks)
                self.assertIsNotNone(ignore, "bytecode and litter are left out of a copy")
                self.assertFalse(partial.exists())
                partial.mkdir()
                (partial / "partial.txt").write_text("incomplete\n", encoding="utf-8")
                raise OSError("simulated interrupted copy")

            argv = [
                str(INSTALLER),
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-tech-flow",
                "--mode",
                "copy",
                "--apply",
            ]
            stderr = io.StringIO()
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(shutil, "copytree", side_effect=interrupted_copy),
                redirect_stdout(io.StringIO()),
                redirect_stderr(stderr),
            ):
                result = module.main()

            self.assertEqual(4, result)
            self.assertFalse(target.exists(), "partial copy must be rolled back")
            recovery_dirs = list(destination.glob(".nobrainer-install-*"))
            self.assertEqual(1, len(recovery_dirs))
            preserved = recovery_dirs[0] / target.name
            self.assertEqual(
                "incomplete\n",
                (preserved / "partial.txt").read_text(encoding="utf-8"),
            )
            self.assertIn("copy staging preserved", stderr.getvalue())

    def test_copy_rollback_preserves_post_create_replacement(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_post_create_race_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            target = destination / "nobrainer-tech-flow"
            foreign = Path(temp) / "foreign-skill"
            foreign.mkdir()
            (foreign / "foreign.txt").write_text(
                "owned by another process\n", encoding="utf-8"
            )

            real_publish = module.atomic_rename_no_replace

            def publish_then_replace(staged: Path, published: Path) -> None:
                real_publish(staged, published)
                shutil.rmtree(published)
                published.symlink_to(foreign, target_is_directory=True)

            argv = [
                str(INSTALLER),
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-tech-flow",
                "--mode",
                "copy",
                "--apply",
            ]
            stderr = io.StringIO()
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(
                    module,
                    "atomic_rename_no_replace",
                    side_effect=publish_then_replace,
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(stderr),
            ):
                result = module.main()

            self.assertEqual(4, result)
            self.assertEqual(
                "owned by another process\n",
                (target / "foreign.txt").read_text(encoding="utf-8"),
            )
            self.assertIn("ownership changed after creation", stderr.getvalue())

    def test_symlink_publish_binds_identity_before_concurrent_replacement(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_symlink_publish_race_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            target = destination / "nobrainer-tech-flow"
            foreign = Path(temp) / "foreign-skill"
            foreign.mkdir()
            (foreign / "foreign.txt").write_text(
                "owned by another process\n", encoding="utf-8"
            )
            real_publish = module.atomic_rename_no_replace

            def publish_then_replace(staged: Path, published: Path) -> None:
                real_publish(staged, published)
                if staged.parent.name.startswith(".nobrainer-install-"):
                    published.unlink()
                    published.symlink_to(foreign, target_is_directory=True)

            argv = [
                str(INSTALLER),
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-tech-flow",
                "--apply",
            ]
            stderr = io.StringIO()
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(
                    module,
                    "atomic_rename_no_replace",
                    side_effect=publish_then_replace,
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(stderr),
            ):
                result = module.main()

            self.assertEqual(4, result)
            self.assertTrue(target.is_symlink())
            self.assertTrue(target.samefile(foreign))
            self.assertEqual(
                "owned by another process\n",
                (target / "foreign.txt").read_text(encoding="utf-8"),
            )
            self.assertEqual([], list(destination.glob(".nobrainer-rollback-*")))
            self.assertIn("ownership changed after creation", stderr.getvalue())

    def test_copy_publish_race_never_overwrites_foreign_child(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_copy_publish_race_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            target = destination / "nobrainer-tech-flow"
            marker = target / "foreign.txt"
            real_publish = module.atomic_rename_no_replace

            def create_foreign_target_then_publish(
                staged: Path, published: Path
            ) -> None:
                published.mkdir()
                marker.write_text("owned by another process\n", encoding="utf-8")
                real_publish(staged, published)

            argv = [
                str(INSTALLER),
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-tech-flow",
                "--mode",
                "copy",
                "--apply",
            ]
            stderr = io.StringIO()
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(
                    module,
                    "atomic_rename_no_replace",
                    side_effect=create_foreign_target_then_publish,
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(stderr),
            ):
                result = module.main()

            self.assertEqual(4, result)
            self.assertEqual(
                "owned by another process\n", marker.read_text(encoding="utf-8")
            )
            self.assertFalse((target / "SKILL.md").exists())
            self.assertEqual(1, len(list(destination.glob(".nobrainer-install-*"))))
            self.assertIn("copy staging preserved", stderr.getvalue())

    def test_rollback_claim_restores_replacement_after_validation(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_rollback_claim_race_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            target = destination / "nobrainer-tech-flow"
            target.mkdir(parents=True)
            expected = module.entry_fingerprint(target)
            self.assertIsNotNone(expected)
            foreign = Path(temp) / "foreign-skill"
            foreign.mkdir()
            (foreign / "foreign.txt").write_text(
                "owned by another process\n", encoding="utf-8"
            )
            real_rename = module.Path.rename
            replaced = False

            def replace_between_check_and_claim(path: Path, claim: Path):
                nonlocal replaced
                if path == target and not replaced:
                    replaced = True
                    shutil.rmtree(path)
                    path.symlink_to(foreign, target_is_directory=True)
                return real_rename(path, claim)

            with mock.patch.object(
                module.Path, "rename", new=replace_between_check_and_claim
            ):
                with self.assertRaisesRegex(RuntimeError, "foreign target restored"):
                    module.remove_created_entry(target, expected)

            self.assertTrue(target.is_symlink())
            self.assertEqual(foreign.resolve(), target.resolve())
            self.assertEqual(
                "owned by another process\n",
                (target / "foreign.txt").read_text(encoding="utf-8"),
            )
            self.assertEqual([], list(destination.glob(".nobrainer-rollback-*")))

    def test_copy_rollback_restores_child_added_during_claim(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_copy_child_race_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            target = destination / "nobrainer-tech-flow"
            target.mkdir(parents=True)
            (target / "SKILL.md").write_text("original\n", encoding="utf-8")
            expected = module.entry_fingerprint(target)
            expected_manifest = module.tree_manifest(target)
            self.assertIsNotNone(expected)
            marker = target / "concurrent.txt"
            real_rename = module.Path.rename
            changed = False

            def add_child_then_claim(path: Path, claim: Path):
                nonlocal changed
                if path == target and not changed:
                    changed = True
                    marker.write_text("owned by another process\n", encoding="utf-8")
                return real_rename(path, claim)

            with mock.patch.object(
                module.Path, "rename", new=add_child_then_claim
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "content changed while claimed; target restored"
                ):
                    module.remove_created_entry(
                        target, expected, expected_manifest
                    )

            self.assertTrue(target.is_dir())
            self.assertEqual(
                "owned by another process\n", marker.read_text(encoding="utf-8")
            )
            self.assertEqual([], list(destination.glob(".nobrainer-rollback-*")))

    def test_unmapped_private_skill_is_reported_and_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            unknown = destination / "nobrainer-fast-audit"
            unknown.mkdir(parents=True)
            marker = unknown / "keep.txt"
            marker.write_text("private contract\n", encoding="utf-8")

            result = self.run_installer(
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-tech-flow",
                "--apply",
            )

            self.assertEqual(3, result.returncode)
            self.assertIn("UNMAPPED_CONFLICT: nobrainer-fast-audit", result.stdout)
            self.assertEqual("private contract\n", marker.read_text(encoding="utf-8"))
            self.assertFalse((destination / "nobrainer-tech-flow").exists())

    def test_copy_ownership_race_preserves_foreign_target(self) -> None:
        spec = importlib.util.spec_from_file_location("skill_installer_race_test", INSTALLER)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            target = destination / "nobrainer-tech-flow"
            target.mkdir(parents=True)
            marker = target / "foreign.txt"
            marker.write_text("owned by another process\n", encoding="utf-8")

            argv = [
                str(INSTALLER),
                "--client",
                "codex",
                "--dest",
                str(destination),
                "--skill",
                "nobrainer-tech-flow",
                "--mode",
                "copy",
                "--apply",
            ]
            with (
                mock.patch.object(sys, "argv", argv),
                mock.patch.object(module, "existing_state", return_value="missing"),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                result = module.main()

            self.assertEqual(4, result)
            self.assertTrue(target.is_dir())
            self.assertEqual(
                "owned by another process\n",
                marker.read_text(encoding="utf-8"),
            )

    def test_full_copy_install_has_exact_curated_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            result = self.run_installer(
                "--client",
                "agents",
                "--dest",
                str(destination),
                "--mode",
                "copy",
                "--apply",
            )
            installed = {
                path.parent.name for path in destination.glob("*/SKILL.md")
            }
            source = {
                path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")
            }
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual(source, installed)
            self.assertEqual(
                {
                    "nobrainer-codex-context",
                    "nobrainer-skill-doctor",
                    "nobrainer-autoimprove",
                    "nobrainer-auto-fine-tune",
                    "nobrainer-browser",
                    "nobrainer-build",
                    "nobrainer-decide",
                    "nobrainer-dispatcher",
                    "nobrainer-research",
                    "nobrainer-writing",
                    "nobrainer-rca",
                    "nobrainer-review",
                    "nobrainer-security",
                    "nobrainer-sessions",
                    "nobrainer-spec-driven-development",
                    "nobrainer-team",
                    "nobrainer-tech-flow",
                    "nobrainer-wiki",
                },
                installed,
            )
            self.assertEqual(18, len(installed))

    def test_inventory_drift_blocks_default_and_explicit_install(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "skill_installer_inventory_drift_test", INSTALLER
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            extra = root / "unreviewed"
            extra.mkdir()
            (extra / "SKILL.md").write_text(
                "---\nname: unreviewed\ndescription: test only\n---\n",
                encoding="utf-8",
            )
            catalogue = {**module.available_skills(), "unreviewed": extra}

            for suffix in (
                [],
                ["--skill", "nobrainer-tech-flow"],
                ["--skill", "unreviewed"],
            ):
                with self.subTest(suffix=suffix):
                    destination = root / ("dest-" + str(len(suffix)))
                    argv = [
                        str(INSTALLER),
                        "--client",
                        "agents",
                        "--dest",
                        str(destination),
                        *suffix,
                        "--apply",
                    ]
                    stderr = io.StringIO()
                    with (
                        mock.patch.object(sys, "argv", argv),
                        mock.patch.object(
                            module, "available_skills", return_value=catalogue
                        ),
                        redirect_stdout(io.StringIO()),
                        redirect_stderr(stderr),
                    ):
                        result = module.main()

                    self.assertEqual(2, result)
                    self.assertFalse(destination.exists())
                    self.assertIn("curated skill inventory drift", stderr.getvalue())


class InstallerRobustnessTests(unittest.TestCase):
    """Behaviours that broke real installs on Windows, in copy mode and with odd paths."""

    def run_installer(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(INSTALLER), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=None if env is None else {**os.environ, **env},
        )

    def load_module(self):
        spec = importlib.util.spec_from_file_location("install_skills_robustness", INSTALLER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_copy_mode_rerun_is_idempotent_and_a_modified_copy_still_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            args = (
                "--client", "agents", "--dest", str(destination), "--mode", "copy",
                "--skill", "nobrainer-tech-flow", "--skill", "nobrainer-auto-fine-tune",
            )
            first = self.run_installer(*args, "--apply")
            second = self.run_installer(*args, "--apply")

            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(0, second.returncode, second.stderr)
            self.assertIn("KEEP: nobrainer-tech-flow", second.stdout)
            self.assertIn("2 unchanged", second.stdout)

            edited = destination / "nobrainer-auto-fine-tune" / "SKILL.md"
            edited.write_text(edited.read_text(encoding="utf-8") + "\nlocal edit\n", encoding="utf-8")
            third = self.run_installer(*args, "--apply")

            self.assertEqual(3, third.returncode)
            self.assertIn("CONFLICT: nobrainer-auto-fine-tune", third.stdout)
            self.assertTrue(edited.read_text(encoding="utf-8").endswith("local edit\n"))

    def test_destination_that_is_a_file_is_reported_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            blocker = Path(temp) / "afile"
            blocker.write_text("not a directory\n", encoding="utf-8")
            for destination in (blocker, blocker / "nested"):
                for extra in ((), ("--apply",)):
                    with self.subTest(destination=destination.name, apply=bool(extra)):
                        result = self.run_installer(
                            "--client", "agents", "--dest", str(destination),
                            "--skill", "nobrainer-build", *extra,
                        )
                        self.assertEqual(2, result.returncode, result.stdout)
                        self.assertIn("not a directory", result.stderr)
                        self.assertNotIn("Traceback", result.stderr)

    @unittest.skipIf(os.name == "nt", "symlink loops need POSIX symlinks")
    def test_symlink_loop_at_the_target_is_a_conflict_not_a_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            destination.mkdir()
            (destination / "nobrainer-build").symlink_to("nobrainer-build")
            result = self.run_installer(
                "--client", "agents", "--dest", str(destination), "--skill", "nobrainer-build",
            )
            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            self.assertNotIn("Traceback", result.stderr)

    def test_client_destinations_follow_the_variables_the_clients_read(self) -> None:
        module = self.load_module()
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp) / "home"
            profile = Path(temp) / "claude-profile"
            xdg = Path(temp) / "xdg"

            default = module.client_destinations({}, home)
            custom = module.client_destinations(
                {"CLAUDE_CONFIG_DIR": str(profile), "XDG_CONFIG_HOME": str(xdg)}, home
            )
            blank = module.client_destinations(
                {"CLAUDE_CONFIG_DIR": "", "XDG_CONFIG_HOME": "  "}, home
            )

            self.assertEqual(home / ".claude" / "skills", default["claude"])
            self.assertEqual(profile / "skills", custom["claude"])
            self.assertEqual(xdg / "opencode" / "skills", custom["opencode"])
            self.assertEqual(default, blank)
            self.assertEqual(home / ".agents" / "skills", custom["codex"])
            self.assertEqual(custom["codex"], custom["agents"])
            # A relative value would resolve against wherever the script runs from.
            with self.assertRaises(ValueError):
                module.client_destinations({"CLAUDE_CONFIG_DIR": "claude-profile"}, home)

    def test_a_broken_variable_only_matters_to_the_client_that_reads_it(self) -> None:
        module = self.load_module()
        home = Path("/home/u")
        broken = {"XDG_CONFIG_HOME": "~/.config", "CLAUDE_CONFIG_DIR": "relative"}

        self.assertEqual(
            home / ".claude" / "skills",
            module.client_destinations({"XDG_CONFIG_HOME": "~/.config"}, home, "claude")["claude"],
        )
        for client in ("codex", "copilot", "agents"):
            with self.subTest(client=client):
                module.client_destinations(broken, home, client)
        for client, variable in (("claude", "CLAUDE_CONFIG_DIR"), ("opencode", "XDG_CONFIG_HOME")):
            with self.subTest(client=client), self.assertRaises(ValueError):
                module.client_destinations({variable: "relative"}, home, client)

    def test_a_variable_is_used_exactly_as_written_unless_it_is_blank(self) -> None:
        module = self.load_module()
        home = Path("/home/u")

        self.assertEqual(
            Path("/profile ") / "skills",
            module.client_destinations({"CLAUDE_CONFIG_DIR": "/profile "}, home)["claude"],
        )
        self.assertEqual(
            home / ".claude" / "skills",
            module.client_destinations({"CLAUDE_CONFIG_DIR": " \t"}, home)["claude"],
        )

    def test_a_variable_the_selected_client_never_reads_does_not_stop_the_install(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = self.run_installer(
                "--client", "claude", "--skill", "nobrainer-build",
                env={"XDG_CONFIG_HOME": "~/.config", "CLAUDE_CONFIG_DIR": "", "HOME": temp, "USERPROFILE": temp},
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn(str(Path(temp).resolve() / ".claude" / "skills" / "nobrainer-build"), result.stdout)

    def test_windows_publish_never_touches_ctypes(self) -> None:
        module = self.load_module()
        staged, target = Path("staged"), Path("target")  # built before os.name changes
        with mock.patch.object(module.os, "name", "nt"), mock.patch.object(
            module.os, "rename"
        ) as rename, mock.patch.object(
            module.ctypes, "CDLL", side_effect=AssertionError("ctypes.CDLL(None) raises on Windows")
        ):
            module.atomic_rename_no_replace(staged, target)
        rename.assert_called_once_with(staged, target)

    def test_preview_names_links_to_skills_that_will_be_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            partial = self.run_installer(
                "--client", "agents", "--dest", str(destination), "--skill", "nobrainer-build",
            )
            complete = self.run_installer("--client", "agents", "--dest", str(destination))

            self.assertEqual(0, partial.returncode, partial.stderr)
            self.assertIn(
                "NOTE: nobrainer-build links to nobrainer-tech-flow", partial.stdout
            )
            self.assertEqual(0, complete.returncode, complete.stderr)
            self.assertNotIn("NOTE:", complete.stdout)

    def test_client_environment_variable_selects_the_destination_without_dest(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            profile = Path(temp) / "claude-profile"
            result = self.run_installer(
                "--client", "claude", "--skill", "nobrainer-build",
                env={"CLAUDE_CONFIG_DIR": str(profile)},
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn(str(profile / "skills" / "nobrainer-build"), result.stdout)

    def test_a_relative_environment_variable_is_an_error_not_a_traceback(self) -> None:
        result = self.run_installer(
            "--client", "claude", "--skill", "nobrainer-build",
            env={"CLAUDE_CONFIG_DIR": "relative"},
        )

        self.assertEqual(2, result.returncode)
        self.assertIn("CLAUDE_CONFIG_DIR must be an absolute path", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    @unittest.skipIf(os.name == "nt", "creating symlinks needs elevated rights on Windows")
    def test_a_destination_that_is_a_symlink_loop_is_an_error_not_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            loop = Path(temp) / "loop"
            loop.symlink_to("loop")
            result = self.run_installer(
                "--client", "agents", "--dest", str(loop), "--skill", "nobrainer-build"
            )

            self.assertEqual(2, result.returncode)
            self.assertNotIn("Traceback", result.stderr)

    def test_bytecode_and_file_manager_litter_do_not_break_a_copy_reinstall(self) -> None:
        # Running an installed helper writes __pycache__ into the copy; that must not turn
        # the next identical install into a conflict.
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            args = (
                "--client", "agents", "--dest", str(destination), "--mode", "copy",
                "--skill", "nobrainer-sessions",
            )
            first = self.run_installer(*args, "--apply")
            self.assertEqual(0, first.returncode, first.stderr)
            installed = destination / "nobrainer-sessions"
            (installed / "scripts" / "__pycache__").mkdir()
            (installed / "scripts" / "__pycache__" / "session_title.cpython-311.pyc").write_bytes(b"\0")
            (installed / ".DS_Store").write_bytes(b"\0")

            second = self.run_installer(*args, "--apply")

            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            self.assertIn("KEEP: nobrainer-sessions", second.stdout)

    def test_only_bytecode_caches_and_file_manager_litter_are_ignored(self) -> None:
        module = self.load_module()

        self.assertTrue(module.is_junk("__pycache__", True))
        self.assertTrue(module.is_junk(".DS_Store", False))
        self.assertTrue(module.is_junk("Thumbs.db", False))
        # A loose .pyc next to a script is importable and shadows the standard library, and a
        # name that is litter as a file is content as a directory (and the other way round).
        self.assertFalse(module.is_junk("json.pyc", False))
        self.assertFalse(module.is_junk("__pycache__", False))
        self.assertFalse(module.is_junk(".DS_Store", True))
        self.assertFalse(module.is_junk("Thumbs.db", True))

    def test_a_loose_bytecode_file_in_a_copy_is_a_conflict_not_litter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / "skills"
            args = (
                "--client", "agents", "--dest", str(destination), "--mode", "copy",
                "--skill", "nobrainer-sessions",
            )
            first = self.run_installer(*args, "--apply")
            self.assertEqual(0, first.returncode, first.stderr)
            planted = destination / "nobrainer-sessions" / "scripts" / "json.pyc"
            planted.write_bytes(b"\0")

            second = self.run_installer(*args, "--apply")

            self.assertEqual(3, second.returncode, second.stdout + second.stderr)
            self.assertIn("CONFLICT: nobrainer-sessions", second.stdout)
            self.assertTrue(planted.exists())

    def test_copy_publish_leaves_bytecode_in_the_source_behind(self) -> None:
        module = self.load_module()
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            (source / "__pycache__").mkdir(parents=True)
            (source / "__pycache__" / "helper.cpython-311.pyc").write_bytes(b"x")
            (source / "SKILL.md").write_text("skill\n", encoding="utf-8")
            parent = Path(temp) / "out"
            parent.mkdir()

            module.stage_and_publish_copy(source, parent / "skill")

            self.assertTrue((parent / "skill" / "SKILL.md").is_file())
            self.assertFalse((parent / "skill" / "__pycache__").exists())

    def test_a_foreign_directory_is_rejected_without_reading_its_files(self) -> None:
        # Reading a conflicting directory used to be impossible; comparing it must not
        # cost memory or time proportional to what the owner keeps there.
        module = self.load_module()
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "nobrainer-sessions"
            target.mkdir()
            (target / "big.bin").write_bytes(b"\0" * 4096)
            with mock.patch.object(
                module, "file_digest", side_effect=AssertionError("must not hash a foreign file")
            ):
                state = module.existing_state(target, module.SKILLS / "nobrainer-sessions", "copy")

            self.assertEqual("conflict", state)

    def test_digest_is_computed_in_bounded_chunks(self) -> None:
        module = self.load_module()
        import hashlib

        payload = b"abc" * 1_000_000
        reads: list[int | None] = []

        class Recording(io.BytesIO):
            def read(self, size: int | None = -1) -> bytes:
                reads.append(size)
                return super().read(size)

        with mock.patch.object(Path, "open", return_value=Recording(payload)):
            digest = module.file_digest(Path("data.bin"))

        self.assertEqual(hashlib.sha256(payload).hexdigest(), digest)
        # A whole-file read (size -1 or None) would need memory in proportion to the file.
        self.assertGreater(len(reads), 2)
        self.assertTrue(all(size is not None and 0 < size <= 4 * 1024 * 1024 for size in reads), reads)


class CrossSkillLinkTests(unittest.TestCase):
    """A subset install has dead links when a skill links into a skill that is absent."""

    def load_module(self):
        spec = importlib.util.spec_from_file_location("install_skills_links", INSTALLER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def catalogue(self, module) -> dict[str, Path]:
        return {path.parent.name: path.parent for path in module.SKILLS.glob("*/SKILL.md")}

    def test_cross_skill_links_are_the_documented_dependencies(self) -> None:
        # Adding a dependency is fine, but it must be deliberate: update this map and the
        # subset example in docs/INSTALL.md together.
        module = self.load_module()
        catalogue = self.catalogue(module)
        actual = {
            name: sorted(module.linked_skills(name, catalogue))
            for name in sorted(catalogue)
            if module.linked_skills(name, catalogue)
        }
        self.assertEqual(
            {
                "nobrainer-build": ["nobrainer-tech-flow"],
                "nobrainer-dispatcher": ["nobrainer-tech-flow"],
                "nobrainer-review": ["nobrainer-tech-flow"],
                "nobrainer-sessions": ["nobrainer-tech-flow"],
                "nobrainer-spec-driven-development": ["nobrainer-tech-flow"],
                "nobrainer-team": ["nobrainer-auto-fine-tune", "nobrainer-tech-flow"],
                "nobrainer-tech-flow": ["nobrainer-auto-fine-tune", "nobrainer-sessions"],
            },
            actual,
        )

    def test_the_subset_documented_in_install_md_has_no_dead_links(self) -> None:
        module = self.load_module()
        text = (ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8")
        example = re.search(r"repeating `--skill`:\n\n```bash\n(.*?)```", text, re.DOTALL)
        self.assertIsNotNone(example, "the explicit-subset example moved")
        names = re.findall(r"--skill (\S+)", example.group(1))
        self.assertGreaterEqual(len(names), 2)
        with tempfile.TemporaryDirectory() as temp:
            self.assertEqual(
                [], module.unmet_references(names, self.catalogue(module), Path(temp) / "skills")
            )


if __name__ == "__main__":
    unittest.main()
