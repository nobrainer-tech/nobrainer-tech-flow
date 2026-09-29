from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_personalization.py"
START = "<!-- NOBRAINER-TECH-FLOW:START -->"
END = "<!-- NOBRAINER-TECH-FLOW:END -->"


CONFIG_VARIABLES = ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "XDG_CONFIG_HOME")


class PersonalizationInstallerTests(unittest.TestCase):
    def run_installer(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_installer_in(
        self, home: Path, variables: dict[str, str], *args: str
    ) -> subprocess.CompletedProcess[str]:
        """Run with a private home and only the config variables the test names."""

        environment = {
            key: value for key, value in os.environ.items() if key not in CONFIG_VARIABLES
        }
        environment.update({"HOME": str(home), "USERPROFILE": str(home), **variables})
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )

    def test_known_client_paths_are_global_and_client_specific(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            expectations = {
                "codex": home / ".codex" / "AGENTS.md",
                "claude": home / ".claude" / "CLAUDE.md",
                "opencode": home / ".config" / "opencode" / "AGENTS.md",
                "copilot": home / ".copilot" / "copilot-instructions.md",
            }
            for client, target in expectations.items():
                with self.subTest(client=client):
                    result = self.run_installer("--client", client, "--home", raw)
                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertIn(f"TARGET: {target}", result.stdout)
                    self.assertIn("DRY_RUN", result.stdout)
                    self.assertFalse(target.exists())

    def test_dry_run_is_default_and_apply_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            target = home / ".codex" / "AGENTS.md"
            preview = self.run_installer("--client", "codex", "--home", raw)
            self.assertEqual(0, preview.returncode, preview.stderr)
            self.assertIn("DRY_RUN", preview.stdout)
            self.assertFalse(target.exists())

            first = self.run_installer("--client", "codex", "--home", raw, "--apply")
            second = self.run_installer("--client", "codex", "--home", raw, "--apply")
            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(0, second.returncode, second.stderr)
            content = target.read_text(encoding="utf-8")
            self.assertEqual(1, content.count(START))
            self.assertEqual(1, content.count(END))
            self.assertIn("$nobrainer-tech-flow", content)
            self.assertIn("MAIN model and effort", content)
            self.assertNotIn("gpt-6-luna", content.lower())
            self.assertIn("first `nobrainer-tech-flow` use each calendar day", content)
            self.assertIn("do not apply them automatically", content)
            self.assertIn("Assess context and checkpoint", content)
            self.assertIn("do not restart or archive automatically", content)
            self.assertIn("locate relevant `index.md` entries", content)
            self.assertIn("`nobrainer-ak` (`nbak`)", content)
            self.assertNotIn("Use NBAK", content)
            self.assertIn("UNCHANGED", second.stdout)

    def test_wiki_root_is_validated_and_recorded_in_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "profile.md"
            wiki = root / "project wiki"
            wiki.mkdir()
            (wiki / "WIKI.md").write_text("wiki instructions\n", encoding="utf-8")
            result = self.run_installer(
                "--client", "agents", "--path", str(target), "--wiki-root", str(wiki), "--apply"
            )
            self.assertEqual(0, result.returncode, result.stderr)
            content = target.read_text(encoding="utf-8")
            wiki_absolute = Path(os.path.abspath(wiki))
            self.assertIn(f"`{wiki_absolute / 'WIKI.md'}`", content)
            self.assertIn("targeted search", content)
            self.assertIn("read only the relevant pages", content)
            self.assertNotIn("Ask before creating a wiki", content)
            self.assertIn(f"WIKI_ROOT: {wiki_absolute}", result.stdout)

    def test_wiki_root_keeps_absolute_symlink_alias_in_saved_instructions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            canonical = root / "archive" / "wiki"
            canonical.mkdir(parents=True)
            (canonical / "WIKI.md").write_text("wiki instructions\n", encoding="utf-8")
            alias = root / "canonical-wiki"
            alias.symlink_to(canonical, target_is_directory=True)
            target = root / "profile.md"

            result = self.run_installer(
                "--client", "agents", "--path", str(target), "--wiki-root", str(alias), "--apply"
            )

            self.assertEqual(0, result.returncode, result.stderr)
            content = target.read_text(encoding="utf-8")
            self.assertIn(f"`{Path(os.path.abspath(alias)) / 'WIKI.md'}`", content)
            self.assertNotIn(str(canonical), content)
            self.assertIn(f"WIKI_ROOT: {Path(os.path.abspath(alias))}", result.stdout)

    def test_missing_wiki_manifest_fails_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "profile.md"
            wiki = root / "empty-wiki"
            wiki.mkdir()
            result = self.run_installer(
                "--client", "agents", "--path", str(target), "--wiki-root", str(wiki), "--apply"
            )
            self.assertEqual(3, result.returncode)
            self.assertIn("must contain WIKI.md", result.stderr)
            self.assertFalse(target.exists())

    def test_auto_update_is_explicit_and_limited_to_safe_verified_flow_updates(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "profile.md"
            default = self.run_installer(
                "--client", "agents", "--path", str(target), "--apply"
            )
            self.assertEqual(0, default.returncode, default.stderr)
            self.assertIn("AUTO_UPDATE: CHECK_AND_NOTIFY", default.stdout)
            default_content = target.read_text(encoding="utf-8")
            self.assertIn("do not apply them automatically", default_content)
            self.assertNotIn("standing authorization", default_content.lower())

            authorized = self.run_installer(
                "--client", "agents", "--path", str(target), "--auto-update", "--apply"
            )
            self.assertEqual(0, authorized.returncode, authorized.stderr)
            content = target.read_text(encoding="utf-8")
            self.assertIn("standing authorization", content)
            self.assertIn("canonical source/version", content)
            self.assertIn("reviewing the exact changes", content)
            self.assertIn("`nobrainer-tech-flow`-only update", content)
            self.assertIn("If the client is inactive", content)
            self.assertIn("AUTO_UPDATE: AUTHORIZED_SAFE_VERIFIED_ONLY", authorized.stdout)

    def test_session_restart_authority_is_opt_in_and_evidence_gated(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "profile.md"
            default = self.run_installer(
                "--client", "agents", "--path", str(target), "--apply"
            )
            self.assertEqual(0, default.returncode, default.stderr)
            self.assertIn("AUTO_SESSION_RESTART: ASSESS_CHECKPOINT_RECOMMEND", default.stdout)
            default_content = target.read_text(encoding="utf-8")
            self.assertIn("do not restart or archive automatically", default_content)
            self.assertNotIn("grants standing authorization for session rotation", default_content)

            authorized = self.run_installer(
                "--client", "agents", "--path", str(target), "--auto-session-restart", "--apply"
            )
            self.assertEqual(0, authorized.returncode, authorized.stderr)
            content = target.read_text(encoding="utf-8")
            self.assertIn("grants standing authorization for session rotation", content)
            self.assertIn("host supports creating a fresh successor", content)
            self.assertIn("context or checkpoint evidence warrants rotation", content)
            self.assertIn("no write is in flight", content)
            self.assertIn("verify exact takeover by ID/readback", content)
            self.assertIn("archive the old session only after that readback", content)
            self.assertIn("Do not create recursive visible workers", content)
            self.assertIn("claim a restart when unsupported", content)
            self.assertIn("AUTO_SESSION_RESTART: AUTHORIZED_EVIDENCE_GATED", authorized.stdout)

    def test_explicit_path_preserves_foreign_content_and_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "nested" / "instructions.md"
            target.parent.mkdir()
            original = "# My existing rules\nkeep this exactly\n"
            target.write_text(original, encoding="utf-8")
            target.chmod(0o640)
            result = self.run_installer(
                "--client", "agents", "--path", str(target), "--apply"
            )
            self.assertEqual(0, result.returncode, result.stderr)
            content = target.read_text(encoding="utf-8")
            self.assertTrue(content.startswith(original))
            self.assertEqual(1, content.count(START))
            self.assertEqual(0o640, target.stat().st_mode & 0o777)
            backups = list(target.parent.glob("instructions.md.bak.*"))
            self.assertEqual(1, len(backups))
            self.assertEqual(original, backups[0].read_text(encoding="utf-8"))

    def test_update_changes_only_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "rules.md"
            old_block = f"{START}\n## Old Flow block\n{END}"
            before = f"before\n{old_block}\nafter\n"
            target.write_text(before, encoding="utf-8")
            result = self.run_installer(
                "--client", "codex", "--path", str(target), "--apply"
            )
            self.assertEqual(0, result.returncode, result.stderr)
            content = target.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("before\n"))
            self.assertTrue(content.endswith("\nafter\n"))
            self.assertIn("## nobrainer-tech-flow", content)
            self.assertNotIn("Old Flow block", content)
            self.assertEqual(1, content.count(START))
            self.assertEqual(1, content.count(END))

    def test_malformed_or_duplicate_markers_fail_without_mutation(self) -> None:
        bad_contents = (
            f"{START}\nno end\n",
            f"{END}\nno start\n",
            f"{START}\n{END}\n{START}\n{END}\n",
            f"{START}\n{START}\n{END}\n",
            f"{END}\n{START}\n",
        )
        with tempfile.TemporaryDirectory() as raw:
            for index, original in enumerate(bad_contents):
                with self.subTest(index=index):
                    target = Path(raw) / f"rules-{index}.md"
                    target.write_text(original, encoding="utf-8")
                    result = self.run_installer(
                        "--client", "codex", "--path", str(target), "--apply"
                    )
                    self.assertEqual(3, result.returncode)
                    self.assertIn("malformed", result.stderr)
                    self.assertEqual(original, target.read_text(encoding="utf-8"))
                    self.assertEqual([], list(target.parent.glob(target.name + ".bak.*")))

    def test_unmarked_legacy_flow_instructions_fail_closed(self) -> None:
        legacy_texts = (
            "# Global preferences\nUse NoBrainer.Tech Flow through nobrainer-ultra.\n",
            "## NoBrainer Tech Flow\n- Keep MAIN in charge.\n- Delegate work.\n",
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for index, original in enumerate(legacy_texts):
                with self.subTest(index=index):
                    target = root / f"legacy-{index}.md"
                    target.write_text(original, encoding="utf-8")
                    result = self.run_installer(
                        "--client", "codex", "--path", str(target), "--apply"
                    )
                    self.assertEqual(3, result.returncode)
                    self.assertIn("unmarked existing nobrainer-tech-flow", result.stderr)
                    self.assertIn("explicit migration is required", result.stderr)
                    self.assertEqual(original, target.read_text(encoding="utf-8"))
                    self.assertEqual([], list(target.parent.glob(target.name + ".bak.*")))

    def test_agents_without_exact_target_is_reported_as_unsupported(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result = self.run_installer("--client", "agents", "--home", raw)
        self.assertEqual(2, result.returncode)
        self.assertIn("UNSUPPORTED", result.stderr)
        self.assertIn("no single documented global instruction path", result.stderr)

    def test_claude_inheriting_codex_does_not_get_duplicate_block(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            codex = self.run_installer("--client", "codex", "--home", raw, "--apply")
            self.assertEqual(0, codex.returncode, codex.stderr)
            claude_file = home / ".claude" / "CLAUDE.md"
            claude_file.parent.mkdir()
            original = "@~/.codex/AGENTS.md\nClaude-only preferences\n"
            claude_file.write_text(original, encoding="utf-8")
            result = self.run_installer(
                "--client", "claude", "--home", raw, "--apply"
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertIn("INHERITS_CODEX", result.stdout)
            self.assertEqual(original, claude_file.read_text(encoding="utf-8"))
            self.assertEqual([], list(claude_file.parent.glob("CLAUDE.md.bak.*")))

    def test_claude_import_of_a_codex_file_without_the_block_still_gets_the_block(self) -> None:
        # Claiming "inherited" while the imported file carries no block would leave
        # the Claude profile without any Flow instructions.
        for codex_file in (None, "Only owner rules here.\n"):
            with self.subTest(codex_file=codex_file), tempfile.TemporaryDirectory() as raw:
                home = Path(raw)
                if codex_file is not None:
                    (home / ".codex").mkdir()
                    (home / ".codex" / "AGENTS.md").write_text(codex_file, encoding="utf-8")
                claude_file = home / ".claude" / "CLAUDE.md"
                claude_file.parent.mkdir()
                original = "@~/.codex/AGENTS.md\nClaude-only preferences\n"
                claude_file.write_text(original, encoding="utf-8")
                result = self.run_installer("--client", "claude", "--home", raw, "--apply")
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertNotIn("INHERITS_CODEX", result.stdout)
                self.assertIn("has no nobrainer-tech-flow block", result.stdout)
                content = claude_file.read_text(encoding="utf-8")
                self.assertTrue(content.startswith(original))
                self.assertEqual(1, content.count(START))

    def test_only_a_real_claude_import_counts_as_inheriting_codex(self) -> None:
        cases = (
            ("Shared rules live in @~/.codex/AGENTS.md today.\n", True),
            ("@{codex}\n", True),
            ("Do not write `@~/.codex/AGENTS.md` here.\n", False),
            ("```\n@~/.codex/AGENTS.md\n```\n", False),
            ("Read ~/.codex/AGENTS.md first.\n", False),
            ("mail me at someone@~/.codex/AGENTS.md.example\n", False),
        )
        for text, inherits in cases:
            with self.subTest(text=text), tempfile.TemporaryDirectory() as raw:
                home = Path(raw)
                codex = self.run_installer("--client", "codex", "--home", raw, "--apply")
                self.assertEqual(0, codex.returncode, codex.stderr)
                claude_file = home / ".claude" / "CLAUDE.md"
                claude_file.parent.mkdir()
                claude_file.write_text(
                    text.format(codex=home / ".codex" / "AGENTS.md"), encoding="utf-8"
                )
                result = self.run_installer("--client", "claude", "--home", raw)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(inherits, "INHERITS_CODEX" in result.stdout)

    def test_config_dir_variables_apply_only_when_home_is_not_given(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            variables = {
                "CLAUDE_CONFIG_DIR": str(root / "claude-profile"),
                "CODEX_HOME": str(root / "codex-profile"),
                "XDG_CONFIG_HOME": str(root / "xdg"),
            }
            expectations = {
                "claude": root / "claude-profile" / "CLAUDE.md",
                "codex": root / "codex-profile" / "AGENTS.md",
                "opencode": root / "xdg" / "opencode" / "AGENTS.md",
                "copilot": home / ".copilot" / "copilot-instructions.md",
            }
            for client, target in expectations.items():
                with self.subTest(client=client):
                    result = self.run_installer_in(home, variables, "--client", client)
                    self.assertEqual(0, result.returncode, result.stderr)
                    self.assertIn(f"TARGET: {target}", result.stdout)
                    self.assertFalse(target.exists())

            # An explicit --home is a request for the documented default locations.
            explicit = self.run_installer_in(
                home, variables, "--client", "claude", "--home", str(root / "other")
            )
            self.assertIn(f"TARGET: {root / 'other' / '.claude' / 'CLAUDE.md'}", explicit.stdout)

            # Empty values count as unset, as the clients treat them.
            empty = self.run_installer_in(
                home, {name: "" for name in CONFIG_VARIABLES}, "--client", "claude"
            )
            self.assertIn(f"TARGET: {home / '.claude' / 'CLAUDE.md'}", empty.stdout)

    def test_codex_override_file_blocks_the_default_target_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw)
            codex_dir = home / ".codex"
            codex_dir.mkdir()
            override = codex_dir / "AGENTS.override.md"
            override.write_text("temporary rules\n", encoding="utf-8")

            blocked = self.run_installer("--client", "codex", "--home", raw, "--apply")
            self.assertEqual(3, blocked.returncode)
            self.assertIn("takes precedence", blocked.stderr)
            self.assertFalse((codex_dir / "AGENTS.md").exists())

            explicit = self.run_installer(
                "--client", "codex", "--path", str(codex_dir / "AGENTS.md")
            )
            self.assertEqual(0, explicit.returncode, explicit.stderr)

            override.write_text(" \n", encoding="utf-8")
            empty = self.run_installer("--client", "codex", "--home", raw)
            self.assertEqual(0, empty.returncode, empty.stderr)

    def test_keep_options_preserves_earlier_grants_and_only_adds_to_them(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "profile.md"
            wiki = root / "wiki"
            wiki.mkdir()
            (wiki / "WIKI.md").write_text("wiki instructions\n", encoding="utf-8")
            first = self.run_installer(
                "--client", "agents", "--path", str(target), "--auto-update",
                "--auto-session-restart", "--wiki-root", str(wiki),
                "--preferences", "Answer in Polish.", "--apply",
            )
            self.assertEqual(0, first.returncode, first.stderr)
            granted = target.read_text(encoding="utf-8")

            kept = self.run_installer(
                "--client", "agents", "--path", str(target), "--keep-options", "--apply"
            )
            self.assertEqual(0, kept.returncode, kept.stderr)
            self.assertIn("KEPT_OPTIONS: auto-update, session-restart, wiki-root", kept.stdout)
            self.assertIn("UNCHANGED", kept.stdout)
            self.assertEqual(granted, target.read_text(encoding="utf-8"))

            # Without the flag a re-run still resets the grants, as documented.
            reset = self.run_installer(
                "--client", "agents", "--path", str(target), "--apply"
            )
            self.assertIn("AUTO_UPDATE: CHECK_AND_NOTIFY", reset.stdout)
            self.assertNotIn("standing authorization", target.read_text(encoding="utf-8"))

    def test_keep_options_drops_a_wiki_that_no_longer_exists_and_accepts_new_grants(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            target = root / "profile.md"
            wiki = root / "wiki"
            wiki.mkdir()
            (wiki / "WIKI.md").write_text("wiki instructions\n", encoding="utf-8")
            first = self.run_installer(
                "--client", "agents", "--path", str(target), "--auto-update",
                "--wiki-root", str(wiki), "--apply",
            )
            self.assertEqual(0, first.returncode, first.stderr)
            (wiki / "WIKI.md").unlink()

            second = self.run_installer(
                "--client", "agents", "--path", str(target), "--keep-options",
                "--auto-session-restart", "--apply",
            )
            self.assertEqual(0, second.returncode, second.stderr)
            self.assertIn("no longer contains WIKI.md", second.stdout)
            self.assertIn("KEPT_OPTIONS: auto-update", second.stdout)
            content = target.read_text(encoding="utf-8")
            self.assertIn("grants standing authorization for session rotation", content)
            self.assertIn("standing authorization to apply", content)
            self.assertIn("discover whether a relevant wiki exists", content)

    def test_block_has_no_stray_blank_line_with_or_without_a_preference(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "profile.md"
            for extra in ((), ("--preferences", "Answer in Polish.")):
                with self.subTest(extra=extra):
                    result = self.run_installer(
                        "--client", "agents", "--path", str(target), *extra, "--apply"
                    )
                    self.assertEqual(0, result.returncode, result.stderr)
                    block = target.read_text(encoding="utf-8").split(START)[1].split(END)[0]
                    # Only the blank line under the heading separates paragraphs.
                    self.assertEqual(1, block.count("\n\n"))

    def test_symlink_is_rejected_without_following_or_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            foreign = root / "foreign.md"
            foreign.write_text("foreign\n", encoding="utf-8")
            target = root / "rules.md"
            target.symlink_to(foreign)
            result = self.run_installer(
                "--client", "codex", "--path", str(target), "--apply"
            )
            self.assertEqual(3, result.returncode)
            self.assertIn("regular non-symlink", result.stderr)
            self.assertTrue(target.is_symlink())
            self.assertEqual("foreign\n", foreign.read_text(encoding="utf-8"))

    def test_crlf_foreign_content_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "rules.md"
            original = "# Personal\r\ncustom\r\n"
            target.write_bytes(original.encode("utf-8"))
            result = self.run_installer(
                "--client", "codex", "--path", str(target), "--apply"
            )
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue(target.read_bytes().startswith(original.encode("utf-8")))


if __name__ == "__main__":
    unittest.main()
