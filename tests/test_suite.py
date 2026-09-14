from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import uuid
import zipfile
from unittest import mock
from pathlib import Path

from scripts import install_skills, validate_skills


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"

CANONICAL_ITEMS = (
    ("nobrainer-codex-context", "nb-codex-context"),
    ("nobrainer-skill-doctor", "nb-skill-doctor"),
    ("nobrainer-ultra", "nb-ultra"),
    ("nobrainer-team", "nb-team"),
    ("nobrainer-dispatcher", "nb-dispatcher"),
    ("nobrainer-research", "nb-research"),
    ("nobrainer-writing", "nb-write"),
    ("nobrainer-build", "nb-build"),
    ("nobrainer-security", "nb-security"),
    ("nobrainer-sessions", "nb-sessions"),
    ("nobrainer-spec-driven-development", "nb-sdd"),
    ("nobrainer-wiki", "nb-wiki"),
    ("nobrainer-browser", "nb-browser"),
    ("nobrainer-autoimprove", "nb-autoimprove"),
    ("nobrainer-decide", "nb-decide"),
    ("nobrainer-rca", "nb-rca"),
    ("nobrainer-review", "nb-review"),
)
CANONICAL = dict(CANONICAL_ITEMS)
CANONICAL_ORDER = tuple(name for name, _ in CANONICAL_ITEMS)
HISTORICAL_CANONICAL_ORDER = (
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
HISTORICAL_ACTIVE = set(HISTORICAL_CANONICAL_ORDER)

LEGACY = {
    "add-gitleaks",
    "agent-browser",
    "agents-restraint",
    "codex-in-claude-code",
    "code-autoresearch",
    "deep-audit",
    "deep-autoreview",
    "deep-autoresearch",
    "deep-bugs-finder",
    "deep-code-review",
    "deep-decide",
    "dispatching-parallel-agents",
    "deep-rca",
    "engineering-standards",
    "karpathy-auto-improver",
    "karpathy-llm-wiki",
    "llm-wiki",
    "nb-add",
    "nb-flow",
    "nb-dispatcher",
    "nb-get",
    "nb-multi",
    "nb-tidy",
    "nb-workflow",
    "nb-write",
    "nobrainer-autopilot",
    "nobrainer-capture-lesson",
    "nobrainer-continuous-improvement",
    "nobrainer-memory",
    "nobrainer-memory-memsearch",
    "nobrainer-npm-secure",
    "nobrainer-reddit",
    "nobrainer-starter",
    "nobrainer-skill-browser",
    "nobrainer-simplifier",
    "nobrainer-style",
    "nobrainer-human-like",
    "security-review",
    "session-handoff",
    "nobrainer-team-builder",
    "nobrainer-ultracode-workflow",
    "nobrainer-wiki-add",
    "nobrainer-wiki-get",
    "nobrainer-wiki-tidy",
    "playwright-cli",
    "wiki-add",
    "wiki-get",
    "wiki-tidy",
}

ACTIVE = set(CANONICAL)

VERSION_MANIFESTS = (
    "package.json",
    "plugin.json",
    ".claude-plugin/plugin.json",
    ".codex-plugin/plugin.json",
    ".cursor-plugin/plugin.json",
    ".kimi-plugin/plugin.json",
    "gemini-extension.json",
)


def markdown_heading_spans(text: str, heading: str) -> list[tuple[int, int]]:
    """Return exact unfenced headings; reject raw-HTML block candidates."""

    spans: list[tuple[int, int]] = []
    fence: tuple[str, int] | None = None
    offset = 0
    for raw_line in text.splitlines(keepends=True):
        line = raw_line.rstrip("\r\n")
        opener = re.match(r"^[ ]{0,3}(`{3,}|~{3,})(.*)$", line)
        if opener and opener.group(1).startswith("`") and "`" in opener.group(2):
            opener = None
        if fence is None and re.match(r"^[ ]{0,3}<", line):
            raise ValueError("raw HTML blocks are not supported in release notes")
        if fence is None and opener:
            marker = opener.group(1)
            fence = (marker[0], len(marker))
        elif fence is not None:
            marker, minimum = fence
            if re.fullmatch(rf"[ ]{{0,3}}{re.escape(marker)}{{{minimum},}}[ \t]*", line):
                fence = None
        elif line == heading:
            spans.append((offset, offset + len(line)))
        offset += len(raw_line)
    return spans


def parse_release_evidence(text: str) -> dict[str, str]:
    lines = text.splitlines()
    fence_pattern = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})(.*)$")
    fences = [
        (index, line)
        for index, line in enumerate(lines)
        if fence_pattern.fullmatch(line)
    ]
    if len(fences) != 2:
        raise AssertionError(f"expected exactly one fenced evidence block, got {len(fences)} delimiters")
    (start, opener), (end, closer) = fences
    if opener != "```text" or closer != "```" or start >= end:
        raise AssertionError("release evidence must use one exact closed ```text block")
    evidence: dict[str, str] = {}
    for line in lines[start + 1 : end]:
        if not line.strip():
            continue
        match = re.fullmatch(r"([A-Z][A-Z0-9_]+): (.+)", line)
        if match is None:
            raise AssertionError(f"malformed release evidence line: {line!r}")
        key, value = match.groups()
        if key in evidence:
            raise AssertionError(f"duplicate release evidence key: {key}")
        evidence[key] = value
    return evidence


def parse_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError(f"{path}: frontmatter must start on line 1")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise AssertionError(f"{path}: frontmatter is not closed") from exc

    values: dict[str, str] = {}
    key: str | None = None
    chunks: list[str] = []
    for line in lines[1:end]:
        match = re.match(r"^([a-zA-Z0-9_-]+):(?:\s*(.*))?$", line)
        if match:
            if key is not None:
                values[key] = " ".join(chunks).strip().strip('"')
            key = match.group(1)
            raw = (match.group(2) or "").strip()
            chunks = [] if raw in {"", ">", ">-", "|", "|-"} else [raw]
        elif key is not None and line.startswith("  "):
            chunks.append(line.strip())
        elif line.strip():
            raise AssertionError(f"{path}: unsupported frontmatter line: {line}")
    if key is not None:
        values[key] = " ".join(chunks).strip().strip('"')
    return values


class SuiteTests(unittest.TestCase):
    def test_curated_active_inventory(self) -> None:
        actual = {path.parent.name for path in SKILLS.glob("*/SKILL.md")}
        self.assertEqual(ACTIVE, actual)

    def test_repository_contains_only_the_curated_skill_tree(self) -> None:
        actual = {
            path.relative_to(ROOT)
            for path in ROOT.rglob("SKILL.md")
            if ".git" not in path.parts
        }
        expected = {Path("skills") / name / "SKILL.md" for name in ACTIVE}
        self.assertEqual(expected, actual)

    def test_all_active_frontmatter_is_portable(self) -> None:
        for skill in sorted(SKILLS.glob("*/SKILL.md")):
            with self.subTest(skill=skill.parent.name):
                frontmatter = parse_frontmatter(skill)
                self.assertEqual(
                    {"name", "description"},
                    set(frontmatter),
                    f"{skill}: active skills use only portable frontmatter",
                )
                self.assertLessEqual(
                    len(frontmatter["name"]),
                    validate_skills.MAX_NAME_LENGTH,
                )

    def test_validator_rejects_overlong_skill_name(self) -> None:
        name = "nobrainer-" + ("x" * 60)
        self.assertGreater(len(name), validate_skills.MAX_NAME_LENGTH)
        self.assertIsNotNone(validate_skills.NAME_RE.fullmatch(name))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / "skills" / name / "SKILL.md"
            skill.parent.mkdir(parents=True)
            skill.write_text(
                f'---\nname: {name}\ndescription: "Use when testing."\n---\n',
                encoding="utf-8",
            )
            with mock.patch.object(validate_skills, "ROOT", root), mock.patch.object(
                validate_skills, "SKILLS", root / "skills"
            ):
                errors = validate_skills.validate(False)
        self.assertTrue(
            any("invalid name length" in error for error in errors),
            errors,
        )

    def test_codex_installer_uses_official_shared_agents_path(self) -> None:
        self.assertEqual(
            Path.home() / ".agents" / "skills",
            install_skills.CLIENT_DESTINATIONS["codex"],
        )
        self.assertEqual(
            install_skills.CLIENT_DESTINATIONS["agents"],
            install_skills.CLIENT_DESTINATIONS["codex"],
        )

    def test_canonical_skills_and_aliases(self) -> None:
        for name, alias in CANONICAL.items():
            with self.subTest(name=name):
                skill = SKILLS / name / "SKILL.md"
                self.assertTrue(skill.is_file(), f"missing {skill}")
                frontmatter = parse_frontmatter(skill)
                self.assertEqual({"name", "description"}, set(frontmatter))
                self.assertEqual(name, frontmatter["name"])
                self.assertTrue(frontmatter["description"].startswith("Use when"))
                self.assertIn(alias, frontmatter["description"])
                self.assertLessEqual(len(frontmatter["description"]), 1024)

    def test_nb_flow_alias_routes_to_canonical_ultra_without_duplicate_skill(self) -> None:
        description = parse_frontmatter(
            SKILLS / "nobrainer-ultra" / "SKILL.md"
        )["description"]
        self.assertIn("nb-flow", description)
        self.assertIn(
            "nb-flow",
            validate_skills.REQUIRED_ALIASES["nobrainer-ultra"],
        )
        self.assertEqual(
            "nobrainer-ultra",
            install_skills.LEGACY_TO_CANONICAL["nb-flow"],
        )
        self.assertFalse((SKILLS / "nb-flow").exists())

    def test_ultra_contract(self) -> None:
        text = (SKILLS / "nobrainer-ultra" / "SKILL.md").read_text(encoding="utf-8")
        for term in (
            "DRIFT_CHECK",
            "BUDDY",
            "AUTOPILOT",
            "RECEIVE_AUDIT",
            "nobrainer-sessions",
            "nobrainer-dispatcher",
            "nobrainer-spec-driven-development",
            "nobrainer-team",
            "nobrainer-research",
            "nobrainer-writing",
            "nobrainer-build",
        ):
            self.assertIn(term, text)
        self.assertNotIn("continue until done", text.lower())
        self.assertIn("one focused requirements round", text.lower())
        self.assertIn("do not make them owner questions", text.lower())
        self.assertIn("without routine check-ins", text.lower())
        self.assertIn("quick path for small changes", text.lower())
        self.assertIn("one coherent, reversible edit", text.lower())
        self.assertIn("nearest deterministic check", text.lower())
        self.assertIn("escalate to the full ultra lifecycle", text.lower())
        self.assertIn("quick path never bypasses", text.lower())
        self.assertIn("PUBLIC_SURFACE", text)
        self.assertIn("affected README/docs/templates/assets/flow", text)
        self.assertIn("public contract, routing or workflow changes", text)
        self.assertIn("fresh SVG + README Mermaid readback", text)
        self.assertIn("fails closeout", text)
        routing_contract = " ".join(text.lower().split())
        self.assertIn("a routing-table line or remembered summary is insufficient", routing_contract)
        self.assertIn("loading method context is not task execution", routing_contract)
        self.assertIn("Progress", text)
        self.assertIn("- [x]", text)
        self.assertIn("- [>]", text)
        self.assertIn("- [ ]", text)
        self.assertIn("Next:", text)
        self.assertIn("ordinary single-session", text.lower())
        self.assertIn("detailed ledger", text.lower())
        self.assertIn("native subagents", text.lower())
        self.assertIn("visible conversations require explicit owner request", text.lower())
        normalized = " ".join(text.lower().split())
        self.assertIn("do not add a repetitive skill/mode preamble", normalized)
        self.assertIn("invent unseen", text.lower())
        self.assertIn("fits one coherent session does not pass this gate", text.lower())
        for field in (
            "Outcome",
            "Non-goals",
            "Expected files",
            "Proof",
            "Untouched",
            "Minimum solution",
            "Test decision",
            "Done clean",
        ):
            self.assertIn(field, text)
        problem_gate = " ".join(text.lower().split())
        self.assertIn("do not infer that a documented command produced the failure", problem_gate)
        self.assertIn("simulation-only request forbids execution, not naming that next diagnostic action", problem_gate)
        normalized = " ".join(text.split())
        self.assertIn("affected not-started `READY` rows to `STOPPED`", normalized)
        self.assertIn("one canonical todo owner", normalized.lower())
        self.assertIn("A stale summary never authorizes a successor", normalized)
        self.assertNotIn("Run this state machine on every non-trivial invocation", text)
        self.assertLessEqual(len(text.splitlines()), 220)
        self.assertLessEqual(len(text.split()), 1600)
        routing = (
            SKILLS / "nobrainer-ultra" / "references" / "routing.md"
        ).read_text(encoding="utf-8")
        for name in CANONICAL:
            self.assertIn(name, routing)

    def test_model_routing_contract_is_explicit(self) -> None:
        policy = (
            SKILLS / "nobrainer-ultra" / "references" / "model-routing.md"
        ).read_text(encoding="utf-8")
        normalized_policy = " ".join(policy.split()).lower()
        for term in (
            "MODEL_POLICY:",
            "STANDARD",
            "EXTENDED",
            "ROUTED",
            "MODEL:",
            "EFFORT:",
            "BUDGET:",
            "ESCALATION:",
            "MODEL_ESCALATION_PROPOSED",
            "do not silently substitute another model",
            "clean runtime readback",
        ):
            self.assertIn(term.lower(), normalized_policy)

        ultra = (SKILLS / "nobrainer-ultra" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("references/model-routing.md", ultra)
        dispatcher = (SKILLS / "nobrainer-dispatcher" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        sessions = (SKILLS / "nobrainer-sessions" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        protocol = (
            SKILLS / "nobrainer-sessions" / "references" / "protocol.md"
        ).read_text(encoding="utf-8")
        for text in (dispatcher, sessions):
            normalized = " ".join(text.split())
            self.assertIn("MODEL_POLICY", normalized)
        for text in (sessions, protocol):
            normalized = " ".join(text.split())
            self.assertIn("MODEL_REQUESTED", normalized)
        self.assertIn("MODEL_ACTUAL", protocol)
        self.assertIn("MODEL_READBACK", protocol)
        self.assertIn("without a silent substitution", dispatcher)
        self.assertIn("never silently substitute another model", sessions)
        self.assertIn("explicit owner request", sessions.lower() + protocol.lower())

    def test_ultra_binds_goal_dod_and_context_budget(self) -> None:
        text = (SKILLS / "nobrainer-ultra" / "SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(text.split()).lower()
        for contract in (
            "portable goal",
            "definition of done",
            "after scope is frozen",
            "explicitly requests",
            "host-native goal",
            "goal readback",
            "show every field above",
            "detailed-ledger decision",
            "structure first",
            "selected contracts in full",
            "large documents or data",
            "context budget",
            "unread required surface",
            "run tools without announcing the next command when the host permits",
            "shortest useful scope or evidence sentence",
            "never repeat the plan, unchanged state or already reported proof",
            "preserve exact commands, errors, numbers and negations",
            "persisted code, docs, commits and third-party messages",
        ):
            self.assertIn(contract, normalized)

        bootstrap = (ROOT / "adapters" / "bootstrap.md").read_text(encoding="utf-8")
        bootstrap_normalized = " ".join(bootstrap.split()).lower()
        for contract in (
            "brief and outcome-first",
            "when the host permits, run tools without announcing them",
            "shortest useful scope or evidence sentence",
            "never repeat the plan or unchanged state",
            "expand when brevity risks ambiguity",
            "human-facing artifacts use normal complete prose",
        ):
            self.assertIn(contract, bootstrap_normalized)

    def test_ultra_setup_upgrade_contract(self) -> None:
        skill = (SKILLS / "nobrainer-ultra" / "SKILL.md").read_text(encoding="utf-8")
        setup = (SKILLS / "nobrainer-ultra" / "references" / "setup.md").read_text(
            encoding="utf-8"
        )
        for term in ("set up", "upgrade", "references/setup.md"):
            self.assertIn(term, skill)
        for term in (
            "CURRENT",
            "DRIFTED",
            "OWNER_GATE",
            "nobrainer-team",
            "`ASK` prepares an exact diff",
            "`OFF` persists",
            "RUNTIME_CHECKS",
            "ROLLBACK",
        ):
            self.assertIn(term, setup)
        setup_normalized = " ".join(setup.lower().split())
        self.assertIn("explicit owner request", setup_normalized)
        self.assertIn("use native subagents or main", setup_normalized)
        self.assertNotIn("fix the result and record one reusable prevention rule", setup)

    def test_build_contract_is_anti_slop_and_calibrated(self) -> None:
        text = (SKILLS / "nobrainer-build" / "SKILL.md").read_text(encoding="utf-8")
        for term in (
            "KISS",
            "DRY",
            "SOLID",
            "YAGNI",
            "Anti-slop gate",
            "failing proof",
            "acceptance trace",
            "nobrainer-review",
        ):
            self.assertIn(term, text)
        self.assertIn("incidental similarity", text)
        self.assertIn("not a mandate for object-oriented ceremony", text)
        normalized = " ".join(text.lower().split())
        for contract in (
            "skip or delete",
            "existing code",
            "standard library",
            "native platform",
            "already-installed dependency",
            "minimum local implementation",
            "stop at the first complete option",
        ):
            self.assertIn(contract, normalized)

    def test_research_contract_is_bounded_and_current(self) -> None:
        text = (SKILLS / "nobrainer-research" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for term in (
            "MICRO",
            "STANDARD",
            "DEEP",
            "primary sources",
            "RESEARCH_BLOCKED",
            "FACT",
            "INFERENCE",
            "nobrainer-wiki",
        ):
            self.assertIn(term, text)
        self.assertIn("Stop when the decision-relevant uncertainty is resolved", text)

    def test_problem_gate_calibrates_local_evidence_and_current_research(self) -> None:
        research = (SKILLS / "nobrainer-research" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        ultra = (SKILLS / "nobrainer-ultra" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        setup = (
            SKILLS / "nobrainer-ultra" / "references" / "setup.md"
        ).read_text(encoding="utf-8")
        for text in (research, ultra, setup):
            self.assertIn("PROBLEM_GATE", text)
            self.assertIn("local", text.lower())
            self.assertIn("current", text.lower())
        self.assertIn("Wiki is context, not current-state proof", research)
        self.assertIn("stable local", research.lower())
        self.assertIn("does not require internet research", research.lower())
        self.assertNotIn("Run at least a `MICRO` internet research pass", research)

    def test_writing_contract_is_high_signal_without_detector_gaming(self) -> None:
        text = (SKILLS / "nobrainer-writing" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        research = (
            SKILLS / "nobrainer-writing" / "references" / "research.md"
        ).read_text(encoding="utf-8")
        for term in (
            "DRAFT",
            "COMPRESS",
            "REWRITE",
            "REVIEW",
            "BRIEF",
            "references/brief-artifacts.md",
            "meaning ledger",
            "VALUE_DENSITY",
            "CAVEATS_AND_CONDITIONS_PRESERVED",
            "nobrainer-research",
        ):
            self.assertIn(term, text)
        self.assertIn("Do not optimize for an AI detector", text)
        self.assertIn("Ten approaches reviewed", research)
        self.assertEqual(10, len(re.findall(r"^\| \d+ \|", research, re.M)))

    def test_writing_brief_artifacts_have_one_actionable_shape(self) -> None:
        reference = (
            SKILLS / "nobrainer-writing" / "references" / "brief-artifacts.md"
        ).read_text(encoding="utf-8")
        for term in (
            "COMMENT",
            "BUG",
            "ISSUE",
            "USER_STORY",
            "REQUEST",
            "ENV:",
            "Name",
            "URL",
            "User",
            "Steps to reproduce",
            "Current behavior",
            "Expected behavior",
            "API request (cURL)",
            "API response",
            "Database query (read-only)",
            "Database result",
            "UI screenshot or MP4 recording",
            "Evidence",
            "HAR",
            "Surface-proof sections remain separate",
            "complete redacted `curl` request",
            "headers and body",
            "separate fenced",
            "page-load/request chain matters",
            "return `INPUT_REQUIRED`",
            "prose description alone does not replace UI evidence",
            "Description",
            "Definition of Done (DoD)",
            "AC01",
            "AC02",
            "AC03",
            "Acceptance",
            "INPUT_REQUIRED",
            "NO_INVENTED_CAUSE_OR_CONTEXT",
            "when it started",
            "A concern is not proof",
            "invent a product policy",
        ):
            self.assertIn(term, reference)
        bug_reference = reference[
            reference.index("## BUG") : reference.index("## ISSUE")
        ]
        field_order = (
            "Description:",
            "ENV:",
            "Name:",
            "URL:",
            "User:",
            "Build/client:",
            "Steps to reproduce:",
            "Current behavior:",
            "Expected behavior:",
            "API request (cURL), when applicable:",
            "API response, when applicable:",
            "Database query (read-only), when applicable:",
            "Database result, when applicable:",
            "Evidence, for a UI screenshot or MP4 recording, when applicable:",
            "HAR, only when the page-load/request chain matters:",
            "Definition of Done (DoD):",
        )
        positions = [bug_reference.index(field) for field in field_order]
        self.assertEqual(sorted(positions), positions)
        self.assertNotIn("Impact:", bug_reference)
        self.assertNotIn("Environment:", bug_reference)
        self.assertNotIn("Summary:", bug_reference)
        self.assertNotIn("Done when:", bug_reference)
        self.assertNotIn("Unknown or workaround:", bug_reference)
        self.assertNotIn("Workaround:", bug_reference)
        self.assertNotIn("Root cause:", bug_reference)
        comment_reference = reference[
            reference.index("## COMMENT") : reference.index("## BUG")
        ]
        self.assertIn("ENV:", comment_reference)
        self.assertIn("Name", comment_reference)
        self.assertIn("URL", comment_reference)
        self.assertIn("User", comment_reference)
        for heading, next_heading in (
            ("## BUG", "## ISSUE"),
            ("## ISSUE", "## USER_STORY"),
            ("## USER_STORY", "## REQUEST"),
            ("## REQUEST", "## Human-feel and compression gate"),
        ):
            section = reference[reference.index(heading) : reference.index(next_heading)]
            self.assertGreaterEqual(section.count("Description:"), 2, heading)
            self.assertGreaterEqual(
                section.count("Definition of Done (DoD):"), 2, heading
            )
            self.assertLess(
                section.index("Description:"),
                section.index("Definition of Done (DoD):"),
                heading,
            )
            for match in re.finditer(r"^Acceptance:\s*$", section, re.M):
                end = section.index("Definition of Done (DoD):", match.end())
                acceptance = section[match.end() : end]
                criteria = re.findall(
                    r"^\s*-\s+(?:\[ \]\s+)?(AC\d{2}):\s+.+$",
                    acceptance,
                    re.M,
                )
                self.assertTrue(criteria, heading)
                self.assertEqual(
                    criteria,
                    [f"AC{index:02d}" for index in range(1, len(criteria) + 1)],
                    heading,
                )
        self.assertIn("Never add mistakes, random slang or fake personal experience", reference)
        issue_reference = reference[
            reference.index("## ISSUE") : reference.index("## USER_STORY")
        ]
        self.assertNotIn("Out of scope:", issue_reference)
        self.assertNotIn("Open question:", issue_reference)
        self.assertNotIn("AI detector", reference)

    def test_public_bug_template_matches_brief_diagnostic_contract(self) -> None:
        template = (
            ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md"
        ).read_text(encoding="utf-8")
        for term in (
            "## Description",
            "## ENV",
            "| Name |",
            "| URL |",
            "| User |",
            "## Steps to reproduce",
            "## Current behavior",
            "## Expected behavior",
            "## API request (cURL)",
            "## API response",
            "## Database query (read-only)",
            "## Database result",
            "## Evidence",
            "## HAR (only when the page-load/request chain matters)",
            "## Definition of Done (DoD)",
            "complete redacted curl command",
            "headers and body",
            "separate blocks",
            "screenshot or MP4",
            "write INPUT_REQUIRED",
            "missing artifact",
        ):
            self.assertIn(term, template)
        self.assertNotIn("## Impact", template)
        self.assertNotIn("## Environment", template)
        self.assertNotIn("## Env indicator", template)
        self.assertNotIn("## URL", template)
        self.assertNotIn("## UI screenshot or MP4 recording", template)
        fields = (
            "## Description",
            "## ENV",
            "## Steps to reproduce",
            "## Current behavior",
            "## Expected behavior",
            "## API request (cURL)",
            "## API response",
            "## Database query (read-only)",
            "## Database result",
            "## Evidence",
            "## HAR (only when the page-load/request chain matters)",
            "## Definition of Done (DoD)",
        )
        positions = [template.index(field) for field in fields]
        self.assertEqual(sorted(positions), positions)

    def test_public_feature_template_exposes_description_acceptance_and_dod(self) -> None:
        template = (
            ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.md"
        ).read_text(encoding="utf-8")
        for term in (
            "## Description",
            "## Who is affected",
            "## Desired outcome",
            "## Evidence",
            "## Acceptance criteria",
            "## Definition of Done (DoD)",
            "AC01",
            "AC02",
            "required checks and proof",
        ):
            self.assertIn(term, template)
        fields = (
            "## Description",
            "## Who is affected",
            "## Desired outcome",
            "## Evidence",
            "## Acceptance criteria",
            "## Definition of Done (DoD)",
        )
        positions = [template.index(field) for field in fields]
        self.assertEqual(sorted(positions), positions)
        acceptance = template[
            template.index("## Acceptance criteria") : template.index(
                "## Definition of Done (DoD)"
            )
        ]
        self.assertRegex(acceptance, r"(?m)^- \[ \] AC01:")
        self.assertRegex(acceptance, r"(?m)^- \[ \] AC02:")

    def test_v1_3_1_brief_eval_remains_historical(self) -> None:
        record = (
            ROOT / "docs" / "evals" / "v1.3.1-writing-brief-2026-09-02.md"
        ).read_text(encoding="utf-8")
        bindings = (
            ("SKILL_SHA256", "skills/nobrainer-writing/SKILL.md"),
            (
                "REFERENCE_SHA256",
                "skills/nobrainer-writing/references/brief-artifacts.md",
            ),
            (
                "HOLDOUT_PROMPT_SHA256",
                "docs/evals/artifacts/v1.3.1-writing-brief-holdout-prompt.md",
            ),
            (
                "HOLDOUT_OUTPUT_SHA256",
                "docs/evals/artifacts/v1.3.1-writing-brief-holdout-output.md",
            ),
            (
                "HOLDOUT_OUTPUT_RAW_B64_SHA256",
                "docs/evals/artifacts/v1.3.1-writing-brief-holdout-output.raw.b64",
            ),
            (
                "HOLDOUT_JUDGE_PROMPT_SHA256",
                "docs/evals/artifacts/v1.3.1-writing-brief-holdout-judge-prompt.md",
            ),
            (
                "HOLDOUT_JUDGE_OUTPUT_SHA256",
                "docs/evals/artifacts/v1.3.1-writing-brief-holdout-judge.md",
            ),
            (
                "HOLDOUT_JUDGE_OUTPUT_RAW_SHA256",
                "docs/evals/artifacts/v1.3.1-writing-brief-holdout-judge.raw.md",
            ),
        )
        historical_source_hashes = {
            "skills/nobrainer-writing/SKILL.md": (
                "a87b0db1383a10f1358b35522995ea6c13199ce4bc0b26cb0baeb98136ccaef3"
            ),
            "skills/nobrainer-writing/references/brief-artifacts.md": (
                "87c38550b380b2eadbdf7ed8cd2721e2867c65e63fd5f756773f550d472136d3"
            ),
        }
        for label, relative in bindings:
            declared = re.search(rf"^{label}: ([0-9a-f]{{64}})$", record, re.M)
            self.assertIsNotNone(declared, label)
            actual = historical_source_hashes.get(
                relative,
                hashlib.sha256((ROOT / relative).read_bytes()).hexdigest(),
            )
            self.assertEqual(actual, declared.group(1), label)

        binding = hashlib.sha256()
        for _, relative in bindings:
            binding.update(relative.encode("utf-8"))
            binding.update(b"\0")
            digest = (
                bytes.fromhex(historical_source_hashes[relative])
                if relative in historical_source_hashes
                else hashlib.sha256((ROOT / relative).read_bytes()).digest()
            )
            binding.update(digest)
        declared_set = re.search(
            r"^SOURCE_AND_ARTIFACT_SET_SHA256: ([0-9a-f]{64})$", record, re.M
        )
        self.assertIsNotNone(declared_set)
        self.assertEqual(binding.hexdigest(), declared_set.group(1))

        for label in (
            "CANDIDATE_HARNESS: codex-cli 0.149.1",
            "CANDIDATE_MODEL: gpt-5.6-luna",
            "CANDIDATE_REASONING: max",
            "CANDIDATE_SANDBOX: read-only",
            "CANDIDATE_EXIT: 0",
            "JUDGE_HARNESS: codex-cli 0.149.1",
            "JUDGE_MODEL: gpt-5.6-luna",
            "JUDGE_REASONING: max",
            "JUDGE_SANDBOX: read-only",
            "JUDGE_EXIT: 0",
            "HOLDOUT_RESULT: PASS 5/5",
            "INDEPENDENT_JUDGE: PASS",
        ):
            self.assertIn(label, record)
        self.assertRegex(record, r"CANDIDATE_SESSION: [0-9a-f-]{36}")
        self.assertRegex(record, r"JUDGE_SESSION: [0-9a-f-]{36}")
        raw_output = base64.b64decode(
            b"".join((ROOT / bindings[4][1]).read_bytes().split()),
            validate=True,
        )
        normalized_raw_output = b"\n".join(
            line.rstrip(b" \t") for line in raw_output.split(b"\n")
        )
        self.assertEqual(
            (ROOT / bindings[3][1]).read_bytes(), normalized_raw_output
        )
        self.assertIn(b"Environment: staging, release 1.3.1  \n", raw_output)
        self.assertEqual(
            (ROOT / bindings[6][1]).read_bytes(),
            (ROOT / bindings[7][1]).read_bytes(),
        )

    def test_security_contract_is_evidence_gated_and_read_only(self) -> None:
        text = (SKILLS / "nobrainer-security" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        for term in (
            "THREAT_MODEL",
            "SECURITY_REVIEW",
            "SUPPLY_CHAIN",
            "READ_ONLY",
            "trust boundary",
            "false-positive",
            "nobrainer-build",
            "nobrainer-research",
            "RESEARCH_BLOCKED",
        ):
            self.assertIn(term, text)
        self.assertIn("Do not test a live target", text)

    def test_team_contract_builds_minimum_capability_roster(self) -> None:
        text = (SKILLS / "nobrainer-team" / "SKILL.md").read_text(encoding="utf-8")
        reference = (
            SKILLS / "nobrainer-team" / "references" / "team-plan.md"
        ).read_text(encoding="utf-8")
        for term in (
            "CAPABILITY_GAP",
            "npx skills find",
            "npx skills use",
            "nobrainer-dispatcher",
            "nobrainer-sessions",
            "MAIN",
            "global cap of 15 subagents",
            "untrusted",
        ):
            self.assertIn(term, text)
        self.assertIn("METHOD", reference)
        self.assertIn("WRITE_SCOPE", reference)
        self.assertIn("ACCEPTANCE", reference)
        self.assertIn("canonical plan", text.lower())
        self.assertNotIn("execution map", text.lower())

    def test_dispatcher_contract_schedules_without_stealing_other_owners(self) -> None:
        text = (SKILLS / "nobrainer-dispatcher" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        agent = (
            SKILLS / "nobrainer-dispatcher" / "agents" / "openai.yaml"
        ).read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        for term in (
            "SCHEDULE",
            "DISPATCH",
            "RECONCILE",
            "RECOVER",
            "READY",
            "PENDING",
            "SENT",
            "PLAN_REF_AND_FINGERPRINT",
            "ATTENTION_BUDGET",
            "BLOCKER_FINGERPRINT",
            "PARALLEL_SAFETY",
            "nobrainer-team",
            "nobrainer-sessions",
            "RECEIVE_AUDIT",
            "NEXT_ACTION",
        ):
            self.assertIn(term, text)
        self.assertIn("A single coherent work unit stays in MAIN", text)
        self.assertIn("must not repair a vague plan", text)
        self.assertIn("worker cannot choose, dispatch or start a successor", text)
        self.assertIn("Unknown dependency state is `BLOCKED`", text)
        self.assertIn("one eligible `BLOCKED` task", text)
        self.assertIn("record `BLOCKED -> READY`", text)
        self.assertIn("plan fingerprint and task contract are still current", normalized)
        self.assertIn("transport identity may still be", text)
        self.assertIn("unknown transport state keeps the task `READY`", normalized)
        self.assertIn("Sessions alone performs the send", text)
        self.assertNotIn("execution map", text.lower())
        self.assertIn("approved plan", agent.lower())
        self.assertNotIn("execution map", agent.lower())
        self.assertIn(
            "rerun affected tests and any required failed review, then run a "
            "fresh `RECEIVE_AUDIT`",
            normalized,
        )
        self.assertIn("none substitutes for another", normalized)
        for field in (
            "CRITICAL_PATH:",
            "UNBLOCKS:",
            "INTEGRATION_OWNER:",
            "NEXT_PROOF:",
        ):
            self.assertIn(field, text)
        self.assertIn(
            "affected not-started `READY` rows to `STOPPED`", normalized
        )
        self.assertIn("new fingerprint", normalized)
        self.assertIn("RESULT: NOT_NEEDED", text)

    def test_team_dispatcher_sessions_transition_has_one_transport_owner(self) -> None:
        dispatcher = (SKILLS / "nobrainer-dispatcher" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        sessions = (SKILLS / "nobrainer-sessions" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        ultra = (SKILLS / "nobrainer-ultra" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        long_run = (
            SKILLS / "nobrainer-ultra" / "references" / "long-run-state.md"
        ).read_text(encoding="utf-8")
        routing = (
            SKILLS / "nobrainer-ultra" / "references" / "routing.md"
        ).read_text(encoding="utf-8")
        normalized_dispatcher = " ".join(dispatcher.split())
        normalized_sessions = " ".join(sessions.split())
        normalized_ultra = " ".join(ultra.split())
        normalized_long_run = " ".join(long_run.split())
        normalized_routing = " ".join(routing.split())
        sequence = (
            "Team -> Dispatcher SCHEDULE -> Sessions setup/delegate -> Dispatcher "
            "DISPATCH"
        )
        self.assertIn(sequence, dispatcher)
        self.assertIn(sequence, long_run)
        self.assertIn("references/long-run-state.md", ultra)
        self.assertIn("Sessions alone performs identity preflight and transport", normalized_long_run)
        self.assertIn("Sessions alone performs identity preflight and transport", normalized_routing)
        self.assertIn("it never invokes a second transport pass", normalized_dispatcher)
        self.assertIn("return `CORRECTION_REQUIRED`", sessions)
        self.assertIn(
            "do not choose, dispatch or execute the correction", normalized_sessions
        )
        self.assertIn(
            "after the repair and any required repeated review, run a fresh "
            "`receive_audit`",
            normalized_sessions.lower(),
        )
        self.assertIn("changed work invalidates old proof", normalized_ultra)
        self.assertIn("RECEIVE_AUDIT", normalized_long_run)
        hooks = (
            SKILLS
            / "nobrainer-ultra"
            / "references"
            / "correction-hooks.md"
        ).read_text(encoding="utf-8")
        normalized_hooks = " ".join(hooks.split())
        self.assertIn("mark it `STOPPED`", normalized_hooks)
        self.assertIn("keep its dependants `PENDING` or `BLOCKED`", normalized_hooks)
        self.assertIn("new plan fingerprint", normalized_hooks)
        self.assertIn("never infer that cancellation succeeded", normalized_hooks)
        self.assertIn(
            "after the repeated review, run a fresh `receive_audit`",
            normalized_hooks.lower(),
        )

    def test_dispatcher_eval_preserves_failed_history_and_current_holdout(self) -> None:
        record = (
            ROOT / "docs" / "evals" / "dispatcher-routing-v1.2.0-2026-08-28.md"
        ).read_text(encoding="utf-8")
        historical_run = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.2.0-routing-release-holdout-run.md"
        ).read_text(encoding="utf-8")
        historical_final_run = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.2.0-routing-final-verified-holdout-run.md"
        ).read_text(encoding="utf-8")
        current_probe_run = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.2.0-routing-current-release-holdout-run.md"
        ).read_text(encoding="utf-8")
        exact_run = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.2.0-routing-exact-release-holdout-run.md"
        ).read_text(encoding="utf-8")
        development_judge = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.2.0-dispatcher-development-probe-judge.md"
        ).read_text(encoding="utf-8")
        post_review_judge = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.2.0-dispatcher-post-review-holdout-judge.md"
        ).read_text(encoding="utf-8")
        post_review_prompt = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.2.0-dispatcher-post-review-holdout-prompt.md"
        ).read_text(encoding="utf-8")
        release_judge = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.2.0-routing-release-holdout-judge.md"
        ).read_text(encoding="utf-8")
        historical_final_judge = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.2.0-routing-final-verified-holdout-judge.md"
        ).read_text(encoding="utf-8")
        current_probe_judge = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.2.0-routing-current-release-holdout-judge.md"
        ).read_text(encoding="utf-8")
        exact_judge = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.2.0-routing-exact-release-holdout-judge.md"
        ).read_text(encoding="utf-8")
        self.assertIn("DEVELOPMENT_PROBE: FAIL 3/4", record)
        self.assertIn("PRE_REVIEW_HOLDOUT: PASS 5/5", record)
        self.assertIn("INDEPENDENT_DIFF_REVIEW: NO_GO", record)
        self.assertIn("POST_REVIEW_HOLDOUT: INVALIDATED", record)
        self.assertIn("undefined lease value `UNCLAIMED`", record)
        self.assertIn("FULL_PACKAGE_REVIEW: NO_GO", record)
        self.assertIn(
            "HISTORICAL_RELEASE_HOLDOUT: PASS 5/5; "
            "INVALIDATED_BY_LATER_CONTRACT_EDITS",
            record,
        )
        self.assertIn("FINAL_VERIFIED_HOLDOUT: FAIL 4/5", record)
        self.assertIn("FINAL_HOLDOUT_JUDGE_ERROR", record)
        self.assertIn(
            "FINAL_HOLDOUT_BINDING: historical after "
            "semantics-preserving bootstrap compression",
            record,
        )
        self.assertIn("CURRENT_RELEASE_HARNESS_PROBE: FAIL 4/5", record)
        self.assertIn(
            "CURRENT_RELEASE_HARNESS_FINDING: candidate excerpt omitted "
            "the explicit no-blind-retry rule",
            record,
        )
        self.assertIn("EXACT_RELEASE_HOLDOUT: PASS 5/5", record)
        self.assertIn(
            "EXACT_RELEASE_BINDING: historical after later trigger-scope "
            "contract edits",
            record,
        )
        self.assertIn("TRIGGER_SCOPE_PROBE: FAIL 3/5", record)
        self.assertIn("TRIGGER_FINAL_HOLDOUT: PASS 5/5", record)
        self.assertIn(
            "TRIGGER_FINAL_BINDING: historical Ultra, Team, Dispatcher and "
            "Sessions hashes verified at v1.2.0",
            record,
        )
        self.assertIn(
            "INDEPENDENT_FINAL_DIFF_REVIEW: CLEAN_SPLIT_COMPLETE",
            record,
        )
        self.assertIn("FINAL_REVIEW_COVERAGE:", record)
        self.assertIn("FINAL_CONTRACTS_REVIEW_RESULT: CLEAN", record)
        self.assertIn("FINAL_ARTIFACTS_REVIEW_RESULT: CLEAN", record)
        self.assertIn("FINAL_PROVENANCE_REREVIEW_RESULT: CLEAN", record)
        self.assertIn("FINAL_TEST_REREVIEW_RESULT: CLEAN", record)
        self.assertIn(
            "FULL_REVIEW_DIFF_SHA256: "
            "d2c989148341a379cf6a9eee3a81898dcc024f0a5ea474f4d746eb7eac64d45c",
            record,
        )
        self.assertIn(
            "FOCUSED_REREVIEW_PACKET_SHA256: "
            "845cbe47e7cce845a7a96b26989ac20ee6c815f5a7d918217a0111c039717fc4",
            record,
        )
        self.assertIn("FOCUSED_REREVIEW_RESULT: CLEAN", record)
        self.assertIn("VERDICT: FAIL", development_judge)
        self.assertIn("VERDICT: PASS", post_review_judge)
        self.assertIn("`UNCLAIMED`", post_review_prompt)
        self.assertIn("VERDICT: PASS — 5/5 cases", release_judge)
        historical_final_case_lines = [
            line
            for line in historical_final_judge.splitlines()
            if re.match(r"^[A-E]: (PASS|FAIL)\b", line)
        ]
        self.assertEqual(
            sum(": PASS" in line for line in historical_final_case_lines), 4
        )
        self.assertEqual(
            sum(": FAIL" in line for line in historical_final_case_lines), 1
        )
        self.assertIn("HARD_FAILURES: NONE", historical_final_judge)
        self.assertIn("VERDICT: FAIL — 1/5 cases", historical_final_judge)
        self.assertIn("RESULT: FAIL 4/5", historical_final_run)
        self.assertIn("RELEASE_EVIDENCE: NO", historical_final_run)

        current_probe_case_lines = [
            line
            for line in current_probe_judge.splitlines()
            if re.match(r"^[A-E]: (PASS|FAIL)\b", line)
        ]
        self.assertEqual(
            sum(": PASS" in line for line in current_probe_case_lines), 4
        )
        self.assertEqual(
            sum(": FAIL" in line for line in current_probe_case_lines), 1
        )
        self.assertIn("VERDICT: FAIL — 4/5 cases", current_probe_judge)
        self.assertIn("RESULT: FAIL 4/5", current_probe_run)
        self.assertIn("RELEASE_EVIDENCE: NO", current_probe_run)

        exact_case_lines = [
            line
            for line in exact_judge.splitlines()
            if re.match(r"^[A-E]: (PASS|FAIL)\b", line)
        ]
        self.assertEqual(sum(": PASS" in line for line in exact_case_lines), 5)
        self.assertEqual(sum(": FAIL" in line for line in exact_case_lines), 0)
        self.assertIn("HARD_FAILURES: NONE", exact_judge)
        self.assertIn("MATERIAL_FINDINGS: NONE", exact_judge)
        self.assertIn("VERDICT: PASS — 5/5 cases", exact_judge)
        self.assertIn("RESULT: PASS 5/5", exact_run)
        self.assertIn("RELEASE_EVIDENCE: YES", exact_run)
        self.assertIn("CLIENT_RUNTIME: NOT_VERIFIED", record)
        self.assertIn(
            "BASELINE_COMMIT: d6931a1006bf0180955d8437fd93174b6a512428",
            historical_run,
        )
        self.assertIn("COMPARATIVE_SCORE_CLAIM: NONE", exact_run)
        self.assertRegex(exact_run, r"CANDIDATE_SESSION: [0-9a-f-]{36}")
        self.assertRegex(exact_run, r"JUDGE_SESSION: [0-9a-f-]{36}")

        def sha256(relative: str) -> str:
            return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()

        declared_skill = re.search(r"^SKILL_SHA256: ([0-9a-f]{64})$", record, re.M)
        self.assertIsNotNone(declared_skill)
        self.assertEqual(
            "5be28a908cb5e467b230205f6e3bf5f35c508b4aa0e2bcaeaae0aa398badf89b",
            declared_skill.group(1),
        )
        self.assertNotEqual(
            sha256("skills/nobrainer-dispatcher/SKILL.md"),
            declared_skill.group(1),
        )
        historical_bootstrap = re.search(
            r"^HISTORICAL_CURRENT_BOOTSTRAP_SHA256: ([0-9a-f]{64})$", record, re.M
        )
        self.assertIsNotNone(historical_bootstrap)
        self.assertNotEqual(sha256("adapters/bootstrap.md"), historical_bootstrap.group(1))
        for label in (
            "ULTRA_SHA256",
            "CORRECTION_HOOKS_SHA256",
            "DISPATCHER_SHA256",
            "SESSIONS_SHA256",
            "BOOTSTRAP_SHA256",
        ):
            self.assertRegex(
                historical_final_run, rf"(?m)^{label}: [0-9a-f]{{64}}$"
            )
        frozen_bootstrap = re.search(
            r"^BOOTSTRAP_SHA256: ([0-9a-f]{64})$", historical_final_run, re.M
        )
        self.assertIsNotNone(frozen_bootstrap)
        self.assertNotEqual(historical_bootstrap.group(1), frozen_bootstrap.group(1))

        for run in (current_probe_run, exact_run):
            for label, relative in (
                ("ULTRA_SHA256", "skills/nobrainer-ultra/SKILL.md"),
                (
                    "CORRECTION_HOOKS_SHA256",
                    "skills/nobrainer-ultra/references/correction-hooks.md",
                ),
                ("DISPATCHER_SHA256", "skills/nobrainer-dispatcher/SKILL.md"),
                ("SESSIONS_SHA256", "skills/nobrainer-sessions/SKILL.md"),
                ("BOOTSTRAP_SHA256", "adapters/bootstrap.md"),
            ):
                declared = re.search(rf"^{label}: ([0-9a-f]{{64}})$", run, re.M)
                self.assertIsNotNone(declared)

        def assert_packet_integrity(run: str, stem: str) -> None:
            base = f"docs/evals/artifacts/{stem}"
            for label, suffix in (
                ("PROMPT_SHA256", "-prompt.md"),
                ("OUTPUT_SHA256", "-output.md"),
                ("JUDGE_RUBRIC_SHA256", "-judge-rubric.md"),
                ("JUDGE_PROMPT_SHA256", "-judge-prompt.md"),
                ("JUDGE_OUTPUT_SHA256", "-judge.md"),
            ):
                declared = re.search(rf"^{label}: ([0-9a-f]{{64}})$", run, re.M)
                self.assertIsNotNone(declared)
                self.assertEqual(sha256(base + suffix), declared.group(1))

            for label, raw_suffix, normalized_suffix in (
                ("RAW_OUTPUT_SHA256", "-output.raw.b64", "-output.md"),
                (
                    "RAW_JUDGE_OUTPUT_SHA256",
                    "-judge.raw.b64",
                    "-judge.md",
                ),
            ):
                raw = base64.b64decode(
                    (ROOT / (base + raw_suffix))
                    .read_text(encoding="ascii")
                    .strip(),
                    validate=True,
                )
                declared = re.search(rf"^{label}: ([0-9a-f]{{64}})$", run, re.M)
                self.assertIsNotNone(declared)
                self.assertEqual(hashlib.sha256(raw).hexdigest(), declared.group(1))
                self.assertEqual(
                    (ROOT / (base + normalized_suffix)).read_bytes(), raw + b"\n"
                )

        assert_packet_integrity(
            historical_final_run, "v1.2.0-routing-final-verified-holdout"
        )
        assert_packet_integrity(
            current_probe_run, "v1.2.0-routing-current-release-holdout"
        )
        assert_packet_integrity(
            exact_run, "v1.2.0-routing-exact-release-holdout"
        )

        exact_base = "docs/evals/artifacts/v1.2.0-routing-exact-release-holdout"
        exact_prompt = (ROOT / f"{exact_base}-prompt.md").read_text(
            encoding="utf-8"
        )
        exact_output = (ROOT / f"{exact_base}-output.md").read_bytes()
        exact_rubric = (ROOT / f"{exact_base}-judge-rubric.md").read_bytes()
        exact_judge_prompt = (ROOT / f"{exact_base}-judge-prompt.md").read_bytes()
        embedded_output = exact_judge_prompt.split(
            b"## Candidate output\n\n", 1
        )[1]
        self.assertEqual(exact_output, embedded_output)
        rubric_payload = b"Hard failures are:" + exact_rubric.split(
            b"Hard failures are:", 1
        )[1]
        embedded_rubric = (
            exact_judge_prompt.split(b"## Frozen rubric\n\n", 1)[1]
            .split(b"\n\n## Candidate output", 1)[0]
            + b"\n"
        )
        self.assertEqual(rubric_payload, embedded_rubric)

        routing_sources = (
            ("ULTRA_SHA256", "skills/nobrainer-ultra/SKILL.md"),
            (
                "CORRECTION_HOOKS_SHA256",
                "skills/nobrainer-ultra/references/correction-hooks.md",
            ),
            ("DISPATCHER_SHA256", "skills/nobrainer-dispatcher/SKILL.md"),
            ("SESSIONS_SHA256", "skills/nobrainer-sessions/SKILL.md"),
            ("BOOTSTRAP_SHA256", "adapters/bootstrap.md"),
        )
        for label, relative in routing_sources:
            prompt_declared = re.search(
                rf"^{label}: ([0-9a-f]{{64}})$", exact_prompt, re.M
            )
            run_declared = re.search(
                rf"^{label}: ([0-9a-f]{{64}})$", exact_run, re.M
            )
            self.assertIsNotNone(prompt_declared)
            self.assertIsNotNone(run_declared)
            self.assertEqual(prompt_declared.group(1), run_declared.group(1))

        routing_artifact_paths = (
            f"{exact_base}-prompt.md",
            f"{exact_base}-output.md",
            f"{exact_base}-output.raw.b64",
            f"{exact_base}-judge-rubric.md",
            f"{exact_base}-judge-prompt.md",
            f"{exact_base}-judge.md",
            f"{exact_base}-judge.raw.b64",
        )
        binding = hashlib.sha256()
        for label, relative in routing_sources:
            frozen = re.search(
                rf"^{label}: ([0-9a-f]{{64}})$", exact_run, re.M
            )
            self.assertIsNotNone(frozen)
            binding.update(relative.encode("utf-8"))
            binding.update(b"\0")
            binding.update(bytes.fromhex(frozen.group(1)))
        for relative in routing_artifact_paths:
            binding.update(relative.encode("utf-8"))
            binding.update(b"\0")
            binding.update(hashlib.sha256((ROOT / relative).read_bytes()).digest())
        declared_binding = re.search(
            r"^SOURCE_AND_ARTIFACT_SET_SHA256: ([0-9a-f]{64})$", exact_run, re.M
        )
        self.assertIsNotNone(declared_binding)
        self.assertEqual(binding.hexdigest(), declared_binding.group(1))

    def test_dispatcher_trigger_eval_preserves_failure_and_binds_final_holdout(
        self,
    ) -> None:
        base = ROOT / "docs" / "evals" / "artifacts"
        failed_stem = "v1.2.0-dispatcher-trigger-scope"
        final_stem = "v1.2.0-dispatcher-trigger-final-holdout"
        failed_run = (base / f"{failed_stem}-run.md").read_text(encoding="utf-8")
        failed_judge = (base / f"{failed_stem}-judge.md").read_text(
            encoding="utf-8"
        )
        final_run = (base / f"{final_stem}-run.md").read_text(encoding="utf-8")
        final_judge = (base / f"{final_stem}-judge.md").read_text(
            encoding="utf-8"
        )

        def parse_judge_block(text: str) -> tuple[list[str], list[str]]:
            lines = text.splitlines()
            self.assertEqual(8, len(lines), lines)
            statuses: list[str] = []
            for index, label in enumerate("ABCDE"):
                match = re.fullmatch(rf"{label}: (PASS|FAIL) — .+", lines[index])
                self.assertIsNotNone(match, lines[index])
                statuses.append(match.group(1))
            self.assertRegex(lines[5], r"^HARD_FAILURES: .+$")
            self.assertRegex(lines[6], r"^MATERIAL_FINDINGS: .+$")
            self.assertRegex(lines[7], r"^VERDICT: (PASS|FAIL) — [0-5]/5 cases$")
            return statuses, lines

        failed_statuses, failed_lines = parse_judge_block(failed_judge)
        self.assertEqual(["FAIL", "PASS", "PASS", "PASS", "FAIL"], failed_statuses)
        self.assertEqual("HARD_FAILURES: NONE", failed_lines[5])
        self.assertEqual("VERDICT: FAIL — 3/5 cases", failed_lines[7])

        final_statuses, final_lines = parse_judge_block(final_judge)
        self.assertEqual(["PASS"] * 5, final_statuses)
        self.assertEqual("HARD_FAILURES: NONE", final_lines[5])
        self.assertEqual("MATERIAL_FINDINGS: NONE", final_lines[6])
        self.assertEqual("VERDICT: PASS — 5/5 cases", final_lines[7])

        def parse_run_fields(text: str) -> dict[str, str]:
            for separator in ("\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"):
                self.assertNotIn(separator, text)
            fields: dict[str, str] = {}
            in_text_block = False
            text_blocks = 0
            for line in text.split("\n"):
                if line == "```text":
                    self.assertFalse(in_text_block)
                    in_text_block = True
                    text_blocks += 1
                    continue
                if in_text_block and line == "```":
                    in_text_block = False
                    continue
                if not in_text_block:
                    continue
                match = re.fullmatch(r"([A-Z][A-Z0-9_]*): (.+)", line)
                self.assertIsNotNone(match, line)
                label, value = match.groups()
                self.assertNotIn(label, fields, label)
                fields[label] = value
            self.assertFalse(in_text_block)
            self.assertEqual(3, text_blocks)
            return fields

        failed_order = (
            "RESULT",
            "HARD_FAILURES",
            "RELEASE_EVIDENCE",
            "FOLLOW_UP_REQUIRED",
            "DATE_UTC",
            "OS",
            "HARNESS",
            "CANDIDATE_MODEL",
            "CANDIDATE_REASONING",
            "CANDIDATE_SANDBOX",
            "CANDIDATE_SESSION",
            "CANDIDATE_WRAPPER_STARTED_UTC",
            "CANDIDATE_FINISHED_UTC",
            "CANDIDATE_EXIT",
            "CANDIDATE_TOKENS_REPORTED",
            "JUDGE_MODEL",
            "JUDGE_REASONING",
            "JUDGE_SANDBOX",
            "JUDGE_SESSION",
            "JUDGE_WRAPPER_STARTED_UTC",
            "JUDGE_FINISHED_UTC",
            "JUDGE_EXIT",
            "JUDGE_TOKENS_REPORTED",
            "ULTRA_SHA256",
            "TEAM_SHA256",
            "DISPATCHER_SHA256",
            "SESSIONS_SHA256",
            "PROMPT_SHA256",
            "OUTPUT_SHA256",
            "RAW_OUTPUT_SHA256",
            "JUDGE_RUBRIC_SHA256",
            "JUDGE_PROMPT_SHA256",
            "JUDGE_OUTPUT_SHA256",
            "RAW_JUDGE_OUTPUT_SHA256",
            "ARTIFACT_SET_SHA256",
            "RUN_CANONICALIZATION",
            "PROVENANCE_BOUNDARY",
            "CANDIDATE_NORMALIZATION",
            "JUDGE_NORMALIZATION",
        )
        final_order = (
            "BASELINE_RELEASE",
            "BASELINE_COMMIT",
            "COMPARATIVE_SCORE_CLAIM",
            "RESULT",
            "HARD_FAILURES",
            "MATERIAL_FINDINGS",
            "RELEASE_EVIDENCE",
            "DATE_UTC",
            "OS",
            "HARNESS",
            "CANDIDATE_MODEL",
            "CANDIDATE_REASONING",
            "CANDIDATE_SANDBOX",
            "CANDIDATE_SESSION",
            "CANDIDATE_FINISHED_UTC",
            "CANDIDATE_EXIT",
            "CANDIDATE_TOKENS_REPORTED",
            "JUDGE_MODEL",
            "JUDGE_REASONING",
            "JUDGE_SANDBOX",
            "JUDGE_SESSION",
            "JUDGE_FINISHED_UTC",
            "JUDGE_EXIT",
            "JUDGE_TOKENS_REPORTED",
            "ULTRA_SHA256",
            "TEAM_SHA256",
            "DISPATCHER_SHA256",
            "SESSIONS_SHA256",
            "PROMPT_SHA256",
            "OUTPUT_SHA256",
            "RAW_OUTPUT_SHA256",
            "JUDGE_RUBRIC_SHA256",
            "JUDGE_PROMPT_SHA256",
            "JUDGE_OUTPUT_SHA256",
            "RAW_JUDGE_OUTPUT_SHA256",
            "SOURCE_AND_ARTIFACT_SET_SHA256",
            "RUN_CANONICALIZATION",
            "PROVENANCE_BOUNDARY",
            "CANDIDATE_NORMALIZATION",
            "JUDGE_NORMALIZATION",
        )
        failed_fields = parse_run_fields(failed_run)
        final_fields = parse_run_fields(final_run)
        self.assertEqual(failed_order, tuple(failed_fields))
        self.assertEqual(final_order, tuple(final_fields))
        for fields in (failed_fields, final_fields):
            for label, value in fields.items():
                if label.endswith("SHA256"):
                    self.assertRegex(value, r"^[0-9a-f]{64}$", label)
        self.assertRegex(final_fields["BASELINE_COMMIT"], r"^[0-9a-f]{40}$")
        with self.assertRaises(AssertionError):
            parse_run_fields(
                "```text\nRESULT: PASS 5/5\nRESULT:garbage\n```\n"
            )
        with self.assertRaises(AssertionError):
            parse_run_fields("```text\nRESULT:\n```\n")
        with self.assertRaises(AssertionError):
            parse_run_fields("```text\nRESULT : forged\n```\n")

        self.assertEqual("FAIL 3/5", failed_fields["RESULT"])
        self.assertEqual("NONE", failed_fields["HARD_FAILURES"])
        self.assertEqual("NO", failed_fields["RELEASE_EVIDENCE"])
        self.assertEqual("PASS 5/5", final_fields["RESULT"])
        self.assertEqual("NONE", final_fields["HARD_FAILURES"])
        self.assertEqual("NONE", final_fields["MATERIAL_FINDINGS"])
        self.assertEqual("YES", final_fields["RELEASE_EVIDENCE"])
        for fields in (failed_fields, final_fields):
            self.assertEqual(
                "added one terminal LF for repository text convention",
                fields["CANDIDATE_NORMALIZATION"],
            )
            self.assertEqual(
                "added one terminal LF for repository text convention",
                fields["JUDGE_NORMALIZATION"],
            )

        def assert_canonical_uuid_field(fields: dict[str, str], label: str) -> None:
            value = fields[label]
            self.assertRegex(
                value,
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-"
                r"[0-9a-f]{4}-[0-9a-f]{12}$",
            )
            self.assertEqual(value, str(uuid.UUID(value)))

        for fields in (failed_fields, final_fields):
            assert_canonical_uuid_field(fields, "CANDIDATE_SESSION")
            assert_canonical_uuid_field(fields, "JUDGE_SESSION")

        dispatcher = (SKILLS / "nobrainer-dispatcher" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        team = (SKILLS / "nobrainer-team" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("Dispatcher owns that scheduler inspection", dispatcher)
        self.assertIn("MAIN remains\nthe owner of the work unit", dispatcher)
        self.assertIn("do not use to elicit requirements", team)
        self.assertIn("must not design roles from a vague goal", team)

        def digest(relative: str) -> str:
            return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()

        def assert_packet(stem: str, fields: dict[str, str]) -> None:
            prefix = f"docs/evals/artifacts/{stem}"
            for label, suffix in (
                ("PROMPT_SHA256", "-prompt.md"),
                ("OUTPUT_SHA256", "-output.md"),
                ("JUDGE_RUBRIC_SHA256", "-judge-rubric.md"),
                ("JUDGE_PROMPT_SHA256", "-judge-prompt.md"),
                ("JUDGE_OUTPUT_SHA256", "-judge.md"),
            ):
                self.assertRegex(fields[label], r"^[0-9a-f]{64}$")
                self.assertEqual(digest(prefix + suffix), fields[label])

            for label, raw_suffix, normalized_suffix in (
                ("RAW_OUTPUT_SHA256", "-output.raw.b64", "-output.md"),
                (
                    "RAW_JUDGE_OUTPUT_SHA256",
                    "-judge.raw.b64",
                    "-judge.md",
                ),
            ):
                raw = base64.b64decode(
                    (ROOT / (prefix + raw_suffix))
                    .read_text(encoding="ascii")
                    .strip(),
                    validate=True,
                )
                self.assertRegex(fields[label], r"^[0-9a-f]{64}$")
                self.assertEqual(hashlib.sha256(raw).hexdigest(), fields[label])
                self.assertEqual(
                    (ROOT / (prefix + normalized_suffix)).read_bytes(), raw + b"\n"
                )

        assert_packet(failed_stem, failed_fields)
        assert_packet(final_stem, final_fields)

        source_paths = (
            ("ULTRA_SHA256", "skills/nobrainer-ultra/SKILL.md"),
            ("TEAM_SHA256", "skills/nobrainer-team/SKILL.md"),
            ("DISPATCHER_SHA256", "skills/nobrainer-dispatcher/SKILL.md"),
            ("SESSIONS_SHA256", "skills/nobrainer-sessions/SKILL.md"),
        )
        for stem, fields in (
            (failed_stem, failed_fields),
            (final_stem, final_fields),
        ):
            prompt = (base / f"{stem}-prompt.md").read_text(encoding="utf-8")
            for label, _ in source_paths:
                declared = re.findall(
                    rf"^{label}: ([0-9a-f]{{64}})$", prompt, re.MULTILINE
                )
                self.assertEqual([fields[label]], declared)

        historical_current_matches = {
            label: failed_fields[label] == digest(relative)
            for label, relative in source_paths
        }
        self.assertEqual(
            {
                "ULTRA_SHA256": False,
                "TEAM_SHA256": False,
                "DISPATCHER_SHA256": False,
                "SESSIONS_SHA256": False,
            },
            historical_current_matches,
        )

        final_prompt = (base / f"{final_stem}-prompt.md").read_text(
            encoding="utf-8"
        )
        for label, relative in source_paths:
            prompt_declared = re.search(
                rf"^{label}: ([0-9a-f]{{64}})$", final_prompt, re.M
            )
            self.assertIsNotNone(prompt_declared)
            self.assertEqual(prompt_declared.group(1), final_fields[label])
            if relative in {
                "skills/nobrainer-ultra/SKILL.md",
                "skills/nobrainer-team/SKILL.md",
                "skills/nobrainer-dispatcher/SKILL.md",
                "skills/nobrainer-sessions/SKILL.md",
            }:
                self.assertNotEqual(digest(relative), prompt_declared.group(1))
            else:
                self.assertEqual(digest(relative), prompt_declared.group(1))

        final_output = (base / f"{final_stem}-output.md").read_bytes()
        final_rubric = (base / f"{final_stem}-judge-rubric.md").read_bytes()
        final_judge_prompt = (base / f"{final_stem}-judge-prompt.md").read_bytes()
        embedded = final_judge_prompt.split(b"## Frozen rubric\n\n", 1)[1]
        embedded_rubric, embedded_output = embedded.split(
            b"\n## Candidate output\n\n", 1
        )
        self.assertEqual(final_rubric, embedded_rubric)
        self.assertEqual(final_output, embedded_output)

        failed_binding_paths = (
            f"docs/evals/artifacts/{failed_stem}-prompt.md",
            f"docs/evals/artifacts/{failed_stem}-output.md",
            f"docs/evals/artifacts/{failed_stem}-output.raw.b64",
            f"docs/evals/artifacts/{failed_stem}-judge-rubric.md",
            f"docs/evals/artifacts/{failed_stem}-judge-prompt.md",
            f"docs/evals/artifacts/{failed_stem}-judge.md",
            f"docs/evals/artifacts/{failed_stem}-judge.raw.b64",
            f"docs/evals/artifacts/{failed_stem}-run.md",
        )
        final_binding_paths = tuple(relative for _, relative in source_paths) + (
            f"docs/evals/artifacts/{final_stem}-prompt.md",
            f"docs/evals/artifacts/{final_stem}-output.md",
            f"docs/evals/artifacts/{final_stem}-output.raw.b64",
            f"docs/evals/artifacts/{final_stem}-judge-rubric.md",
            f"docs/evals/artifacts/{final_stem}-judge-prompt.md",
            f"docs/evals/artifacts/{final_stem}-judge.md",
            f"docs/evals/artifacts/{final_stem}-judge.raw.b64",
            f"docs/evals/artifacts/{final_stem}-run.md",
        )

        def binding_digest(
            paths: tuple[str, ...],
            field: str,
            frozen_source_digests: dict[str, bytes] | None = None,
        ) -> str:
            binding = hashlib.sha256()
            for relative in paths:
                source_digest = (frozen_source_digests or {}).get(relative)
                if source_digest is not None:
                    digest = source_digest
                else:
                    data = (ROOT / relative).read_bytes()
                    if relative == paths[-1]:
                        decoded = data.decode("utf-8")
                        for separator in (
                            "\r",
                            "\v",
                            "\f",
                            "\x1c",
                            "\x1d",
                            "\x1e",
                            "\x85",
                            "\u2028",
                            "\u2029",
                        ):
                            self.assertNotIn(separator, decoded)
                        self.assertTrue(data.endswith(b"\n"))
                        self.assertFalse(data.endswith(b"\n\n"))
                        pattern = rf"(?m)^{field}: [0-9a-f]{{64}}$".encode("ascii")
                        replacement = f"{field}: <SELF>".encode("ascii")
                        data, count = re.subn(pattern, replacement, data)
                        self.assertEqual(1, count)
                    digest = hashlib.sha256(data).digest()
                binding.update(relative.encode("utf-8"))
                binding.update(b"\0")
                binding.update(digest)
            return binding.hexdigest()

        failed_digest = failed_fields["ARTIFACT_SET_SHA256"]
        final_digest = final_fields["SOURCE_AND_ARTIFACT_SET_SHA256"]
        self.assertRegex(failed_digest, r"^[0-9a-f]{64}$")
        self.assertRegex(final_digest, r"^[0-9a-f]{64}$")
        provenance = (
            "authenticity requires the reviewed Git commit; this digest proves "
            "packet consistency"
        )
        self.assertEqual(provenance, failed_fields["PROVENANCE_BOUNDARY"])
        self.assertEqual(provenance, final_fields["PROVENANCE_BOUNDARY"])
        self.assertEqual(
            "for repo-relative path docs/evals/artifacts/"
            f"{failed_stem}-run.md, read its reviewed Git-blob bytes; require valid "
            "UTF-8, LF-only line endings and exactly one terminal LF; replace exactly "
            "once only the 64-lowercase-hex value of ARTIFACT_SET_SHA256 with <SELF>; "
            "hash every other byte unchanged",
            failed_fields["RUN_CANONICALIZATION"],
        )
        self.assertEqual(
            "for repo-relative path docs/evals/artifacts/"
            f"{final_stem}-run.md, read its reviewed Git-blob bytes; require valid "
            "UTF-8, LF-only line endings and exactly one terminal LF; replace exactly "
            "once only the 64-lowercase-hex value of "
            "SOURCE_AND_ARTIFACT_SET_SHA256 with <SELF>; hash every other byte unchanged",
            final_fields["RUN_CANONICALIZATION"],
        )
        self.assertEqual(
            binding_digest(failed_binding_paths, "ARTIFACT_SET_SHA256"),
            failed_digest,
        )
        frozen_final_sources = {
            relative: bytes.fromhex(final_fields[label])
            for label, relative in source_paths
        }
        self.assertEqual(
            binding_digest(
                final_binding_paths,
                "SOURCE_AND_ARTIFACT_SET_SHA256",
                frozen_final_sources,
            ),
            final_digest,
        )
        # This packet intentionally remains historical: its source list points
        # to the pre-GOAL_LOOP Ultra bytes. The current contract is bound by the
        # portfolio evaluation rather than by rewriting old evidence.
        self.assertNotEqual(
            binding_digest(
                final_binding_paths, "SOURCE_AND_ARTIFACT_SET_SHA256"
            ),
            final_digest,
        )

    def test_writing_eval_freezes_research_behavior_and_release_evidence(self) -> None:
        record = (
            ROOT / "docs" / "evals" / "writing-density-v1.2.0-2026-08-28.md"
        ).read_text(encoding="utf-8")
        run = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.2.0-writing-release-holdout-run.md"
        ).read_text(encoding="utf-8")
        release_judge = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.2.0-writing-release-holdout-judge.md"
        ).read_text(encoding="utf-8")
        for status in (
            "BASELINE_CAPABILITY: ABSENT",
            "COMPARATIVE_SCORE_CLAIM: NONE",
            "DEVELOPMENT_PROBE: PASS 5/5",
            "FIRST_FINAL_HOLDOUT: PASS 5/5",
            "INDEPENDENT_DIFF_REVIEW: NO_GO",
            "RELEASE_HOLDOUT: PASS 5/5",
            "CLIENT_RUNTIME: NOT_VERIFIED",
        ):
            self.assertIn(status, record)
        self.assertIn("VERDICT: PASS — 5/5 cases", release_judge)
        self.assertIn("BASELINE_COMMIT: d6931a1006bf0180955d8437fd93174b6a512428", run)
        self.assertRegex(run, r"CANDIDATE_SESSION: [0-9a-f-]{36}")
        self.assertRegex(run, r"JUDGE_SESSION: [0-9a-f-]{36}")

        def sha256(relative: str) -> str:
            return hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()

        # The v1.2.0 writing packet is historical. Keep its source hash as
        # evidence for that packet instead of silently rebinding it to the
        # current writing skill after a later candidate change.
        historical_skill_sha256 = (
            "a756274e8a55cf32c7f2f15e2502801bcd7b31f30682d787646c81adee46dcda"
        )

        for label, relative in (
            ("SKILL_SHA256", "skills/nobrainer-writing/SKILL.md"),
            (
                "PROMPT_SHA256",
                "docs/evals/artifacts/v1.2.0-writing-release-holdout-prompt.md",
            ),
            (
                "OUTPUT_SHA256",
                "docs/evals/artifacts/v1.2.0-writing-release-holdout-output.md",
            ),
            (
                "JUDGE_PROMPT_SHA256",
                "docs/evals/artifacts/v1.2.0-writing-release-holdout-judge-prompt.md",
            ),
            (
                "JUDGE_OUTPUT_SHA256",
                "docs/evals/artifacts/v1.2.0-writing-release-holdout-judge.md",
            ),
        ):
            declared = re.search(rf"^{label}: ([0-9a-f]{{64}})$", run, re.M)
            self.assertIsNotNone(declared)
            if relative == "skills/nobrainer-writing/SKILL.md":
                self.assertEqual(historical_skill_sha256, declared.group(1))
            else:
                self.assertEqual(sha256(relative), declared.group(1))

        for label, raw_relative, normalized_relative in (
            (
                "RAW_OUTPUT_SHA256",
                "docs/evals/artifacts/v1.2.0-writing-release-holdout-output.raw.b64",
                "docs/evals/artifacts/v1.2.0-writing-release-holdout-output.md",
            ),
            (
                "RAW_JUDGE_OUTPUT_SHA256",
                "docs/evals/artifacts/v1.2.0-writing-release-holdout-judge.raw.b64",
                "docs/evals/artifacts/v1.2.0-writing-release-holdout-judge.md",
            ),
        ):
            raw = base64.b64decode(
                (ROOT / raw_relative).read_text(encoding="ascii").strip(),
                validate=True,
            )
            declared = re.search(rf"^{label}: ([0-9a-f]{{64}})$", run, re.M)
            self.assertIsNotNone(declared)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), declared.group(1))
            self.assertEqual((ROOT / normalized_relative).read_bytes(), raw + b"\n")

        writing_binding_paths = (
            "skills/nobrainer-writing/SKILL.md",
            "docs/evals/artifacts/v1.2.0-writing-release-holdout-prompt.md",
            "docs/evals/artifacts/v1.2.0-writing-release-holdout-output.md",
            "docs/evals/artifacts/v1.2.0-writing-release-holdout-output.raw.b64",
            "docs/evals/artifacts/v1.2.0-writing-release-holdout-judge-prompt.md",
            "docs/evals/artifacts/v1.2.0-writing-release-holdout-judge.md",
            "docs/evals/artifacts/v1.2.0-writing-release-holdout-judge.raw.b64",
        )
        binding = hashlib.sha256()
        for relative in writing_binding_paths:
            binding.update(relative.encode("utf-8"))
            binding.update(b"\0")
            if relative == "skills/nobrainer-writing/SKILL.md":
                digest = bytes.fromhex(historical_skill_sha256)
            else:
                digest = hashlib.sha256((ROOT / relative).read_bytes()).digest()
            binding.update(digest)
        declared_binding = re.search(
            r"^SOURCE_AND_ARTIFACT_SET_SHA256: ([0-9a-f]{64})$", run, re.M
        )
        self.assertIsNotNone(declared_binding)
        self.assertEqual(binding.hexdigest(), declared_binding.group(1))

        judge_prompt = (
            ROOT
            / "docs/evals/artifacts/v1.2.0-writing-release-holdout-judge-prompt.md"
        ).read_text(encoding="utf-8")
        for relative in writing_binding_paths[:3]:
            self.assertIn(f"`{relative}`", judge_prompt)

        historical = (
            (
                "DEVELOPMENT_RAW_OUTPUT_SHA256",
                "docs/evals/artifacts/v1.2.0-writing-development-probe-output.raw.b64",
            ),
            (
                "DEVELOPMENT_RAW_JUDGE_OUTPUT_SHA256",
                "docs/evals/artifacts/v1.2.0-writing-development-probe-judge.raw.b64",
            ),
            (
                "FIRST_FINAL_RAW_OUTPUT_SHA256",
                "docs/evals/artifacts/v1.2.0-writing-final-holdout-output.raw.b64",
            ),
            (
                "FIRST_FINAL_RAW_JUDGE_OUTPUT_SHA256",
                "docs/evals/artifacts/v1.2.0-writing-final-holdout-judge.raw.b64",
            ),
        )
        for label, relative in historical:
            raw = base64.b64decode(
                (ROOT / relative).read_text(encoding="ascii").strip(), validate=True
            )
            declared = re.search(rf"^{label}: ([0-9a-f]{{64}})$", record, re.M)
            self.assertIsNotNone(declared)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), declared.group(1))

    def test_active_product_has_no_external_workflow_branding(self) -> None:
        checked = [
            ROOT / "README.md",
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "CONTRIBUTING.md",
            ROOT / "RELEASE-NOTES.md",
            ROOT / "docs" / "INSTALL.md",
            ROOT / "docs" / "SKILL_CURATION.md",
            *[path for name in CANONICAL for path in (SKILLS / name).rglob("*.md")],
        ]
        for path in checked:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8").lower()
                for brand in validate_skills.EXTERNAL_WORKFLOW_BRANDS:
                    self.assertNotIn(brand, text)

    def test_review_attribution_does_not_disable_operational_or_public_value_gates(self) -> None:
        review = ROOT / "docs" / "reviews" / "v1.6.0-review.md"
        adapter = ROOT / "adapters" / "bootstrap.md"
        original_read = Path.read_text
        brand = validate_skills.EXTERNAL_WORKFLOW_BRANDS[-1]
        for path, payload, expected_error in (
            (review, brand, None),
            (review.with_suffix(".py"), brand, "external workflow branding"),
            (review.with_suffix(".json"), brand, "external workflow branding"),
            (review.parent / "nested" / "review.md", brand, "external workflow branding"),
            (adapter, brand, "external workflow branding"),
            (review, validate_skills.PUBLIC_FORBIDDEN[0], "forbidden public value"),
        ):
            with self.subTest(path=path, expected=expected_error):
                def read(candidate, *args, **kwargs):
                    return payload if candidate == path else original_read(candidate, *args, **kwargs)
                with mock.patch.object(validate_skills, "public_text_files", return_value=[path]), mock.patch.object(Path, "read_text", read):
                    errors = validate_skills.validate(suite_only=True)
                if expected_error:
                    self.assertTrue(any(expected_error in error for error in errors), errors)
                else:
                    self.assertEqual([], errors)

    def test_sessions_fail_closed_contract(self) -> None:
        text = (SKILLS / "nobrainer-sessions" / "SKILL.md").read_text(encoding="utf-8")
        for term in (
            "<repo> | MAIN",
            "THREAD_ID",
            "HOST_ID",
            "CHECKOUT",
            "LEASE",
            "FENCING_EPOCH",
            "RECEIVE_AUDIT",
        ):
            self.assertIn(term, text)
        protocol = (
            SKILLS / "nobrainer-sessions" / "references" / "protocol.md"
        ).read_text(encoding="utf-8")
        for term in (
            "METHOD:",
            "acquire LEASE",
            "before the first write",
            "CONTEXT_SOURCE_REF:",
            "CONTEXT_SHA256:",
            "CONTEXT_READBACK:",
            "MESSAGE_ID:",
            "PAYLOAD_SHA256:",
            "IDEMPOTENCY_KEY:",
            "DELIVERY_RECEIPT:",
            "ACK_STATUS:",
        ):
            self.assertIn(term, protocol)
        normalized = " ".join(text.lower().split())
        self.assertIn("propagation is not assumed", normalized)
        self.assertIn("minimum context", normalized)
        self.assertIn("whole parent transcript", normalized)
        self.assertIn("stale context or evidence", normalized)
        self.assertIn("including a blocked or stale one", normalized)
        for contract in (
            "copy the caller's schema before filling values",
            "do not rename fields or change nesting",
            "raw evidence",
            "canonical verdict",
        ):
            self.assertIn(contract, normalized)
        self.assertIn("stale context or evidence", protocol.lower())
        self.assertIn("native subagents", protocol.lower())
        self.assertIn("visible conversation", protocol.lower())
        self.assertIn("explicit owner request", protocol.lower())
        self.assertIn("workers never create successor", protocol.lower())
        team_plan = (
            SKILLS / "nobrainer-team" / "references" / "team-plan.md"
        ).read_text(encoding="utf-8")
        self.assertIn("SESSION_MODE: MAIN | MULTI_SESSION", team_plan)

    def test_sdd_is_spec_driven_not_subagent_driven(self) -> None:
        text = (SKILLS / "nobrainer-spec-driven-development" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("spec-driven development", text.lower())
        self.assertIn("not subagent-driven development", text.lower())
        self.assertIn("ACCEPTANCE", text)
        self.assertIn("ROLLBACK", text)

    def test_karpathy_attribution(self) -> None:
        for name in ("nobrainer-autoimprove", "nobrainer-wiki"):
            with self.subTest(name=name):
                text = (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn("Andrej Karpathy", text)
                self.assertRegex(text, r"https://(gist\.)?github\.com/karpathy/")

    def test_autoimprove_protects_evaluator_integrity(self) -> None:
        autoimprove = (
            SKILLS / "nobrainer-autoimprove" / "SKILL.md"
        ).read_text(encoding="utf-8")
        normalized = " ".join(autoimprove.split()).lower()

        for field in (
            "EVAL_INTEGRITY:",
            "NOISE_POLICY:",
            "EVALUATOR_STATUS:",
            "SCORE_RECEIPT:",
            "NOISE_RESULT:",
        ):
            self.assertIn(field, autoimprove)
        for contract in (
            "known-good",
            "known-bad",
            "tailored deceptive",
            "candidate write scope excludes",
            "outside the candidate workspace",
            "prompt-only prohibition",
            "append-only immutable receipt",
            "experiment and round id",
            "candidate id and target hash",
            "call order",
            "input/data snapshot",
            "repetition id",
            "resulting decision",
            "aggregation formula",
            "post-hoc edits",
            "non-comparable",
            "re-baseline",
            "at least three paired repetitions",
            "forbid cherry-picking and favorable retries",
            "never retry to change a result",
            "finite variants, rounds, repetitions, retries",
            "production deployment",
            "security or system changes",
            "durable policy",
            "lessons or wiki writes",
            "record the owner, decision and evidence reference",
            "failed evidence or safety anomaly",
            "an initial plan comes from a completed experiment contract",
            "never omit a hard gate",
            "observable access boundary",
            "ordinary positive, known-bad and tailored deceptive controls",
            "exact paired run count",
            "blind or shuffled presentation",
            "dispersion",
            "opened once, never reused for iteration",
            "measurable primary delta",
            "uncertainty rule",
            "protected usefulness, safety or regression guardrails",
            "every supplied ceiling or an explicit stricter one",
            "a ceiling needs a concrete quantity and unit",
            "promise to predeclare",
            "an experiment win grants no live",
            "status: ready_for_owner_review | blocked",
            "execution: not_started",
            "never imply that calibration, trials or approval ran",
            "`strict_cap` makes the owner's word limit a hard gate",
            "budget the draft to `min(limit - 40, 140)` words",
            "at most six nonblank lines",
            "compress until the owner limit passes",
            "without one, target `min(limit - 50, 130)`",
            "never claim an exact count",
            "print no heading, blank line, internal form, rollback explanation",
            "invent no optional mechanism",
            "within the cap rather than omitting them",
            "run `cap_audit`",
            "disjoint one-time holdout and open-once semantics",
            "exact receipt field list with no additions",
            "retain `immediately` when stops are immediate",
            "append no canonical status or execution field",
            "no later duty may contradict a role's `only` boundary",
            "closed value domain retains its literal `only` or `no other` qualifier",
            "the owner-facing plan need not mirror internal labels",
            "unless the owner supplies another terminal",
            "owner-defined exact terminal values",
            "suppress canonical status and execution",
            "pending future gates normally mean ready for review",
            "lower bound is also a hard gate",
            "overrides the compact budget",
            "count the final draft with",
            "available whitespace counter",
            "tally whitespace-delimited words before sending",
            "never exceed a stated maximum",
            "scope and timing qualifiers, closed field sets and terminal value domains",
            "reuse their literal wording",
            "repeat it for each",
            "collective shorthand is not equivalent",
            "count exact final text",
            "scripts/count_words.py --escaped-newlines",
            "a raw `%s` count is invalid evidence",
            "trace every rubric requirement to the frozen request",
            "hidden judge-only requirement invalidates the evaluator",
            "these stops do not close a still-open owner outcome",
            "smallest high-leverage change",
            "new holdout, new baseline and new experiment record",
            "apply pareto discipline",
            "close only when dod passes",
        ):
            self.assertIn(contract, normalized)

        ultra = (SKILLS / "nobrainer-ultra" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("calibrated evaluator", ultra)
        self.assertIn("candidate write scope", ultra)
        self.assertIn("CANDIDATE_REJECTED", ultra)
        self.assertIn("fresh holdout", ultra)

    def test_autoimprove_word_counter_handles_serialized_newlines(self) -> None:
        counter = (
            SKILLS
            / "nobrainer-autoimprove"
            / "scripts"
            / "count_words.py"
        )
        raw = subprocess.run(
            ["python3", str(counter)],
            input="one two\nthree",
            text=True,
            capture_output=True,
            check=True,
        )
        escaped = subprocess.run(
            ["python3", str(counter), "--escaped-newlines"],
            input=r"one two\nthree",
            text=True,
            capture_output=True,
            check=True,
        )
        serialized_without_flag = subprocess.run(
            ["python3", str(counter)],
            input=r"one two\nthree",
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(raw.stdout.strip(), "3")
        self.assertEqual(escaped.stdout.strip(), "3")
        self.assertEqual(serialized_without_flag.stdout.strip(), "2")

    def test_lightweight_learning_contract(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        ultra = (SKILLS / "nobrainer-ultra" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        autoimprove = (SKILLS / "nobrainer-autoimprove" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        wiki = (SKILLS / "nobrainer-wiki" / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("bounded corrective attempts", readme)
        self.assertIn("A quick answer stays a quick answer", readme)
        self.assertIn("Lightweight learning loop", agents)
        self.assertIn("Correction hooks", ultra)
        self.assertIn("OWNER_DECISION_CHANGED", ultra)
        self.assertIn("AGENT_ERROR_CORRECTED", ultra)
        self.assertIn("REVIEW_FAILED", ultra)
        self.assertIn("invalidate", ultra.lower())
        self.assertIn("regression scenario", autoimprove)
        self.assertIn("`AUTO_SCOPED`", autoimprove)
        self.assertIn("`ASK`", autoimprove)
        self.assertIn("`OFF`", autoimprove)
        self.assertIn("do not create a durable diff", " ".join(autoimprove.split()))
        self.assertIn("PROMOTION: PROMOTED | NO_CHANGE | REVERTED | BLOCKED", autoimprove)
        self.assertIn("HOLDOUT_RESULT: PASS | FAIL | NOT_RUN", autoimprove)
        self.assertIn("Durable personalization without hidden memory", wiki)
        self.assertIn("source, date, scope", wiki)

        hooks = (
            SKILLS / "nobrainer-ultra" / "references" / "correction-hooks.md"
        ).read_text(encoding="utf-8")
        for term in (
            "SUPERSEDE",
            "tasks/lessons.md",
            "AGENTS.md",
            "nobrainer-wiki",
            "secret",
            "REPLAN_REQUIRED",
            "LEARNING_WRITE_POLICY",
            "AUTO_SCOPED",
        ):
            self.assertIn(term, hooks)
        self.assertIn("one canonical owner", hooks)
        self.assertIn("under `ASK`, prepare the exact single-store diff", hooks)
        self.assertIn("under `OFF`, keep the prevention candidate", hooks)
        self.assertIn("do not\n     create or modify `tasks/lessons.md`", hooks)

        self.assertIn("`AUTO_SCOPED` may persist", readme)
        self.assertIn("`ASK` prepares one exact diff", readme)
        self.assertIn("`OFF` keeps it\n  task-local without a durable diff", readme)
        for term in (
            "Minimum sufficient change",
            "NON_GOALS",
            "UNTOUCHED",
            "MINIMUM_SOLUTION",
            "TEST_DECISION",
            "least complex capable method",
        ):
            self.assertIn(term, agents)
        self.assertEqual(
            (ROOT / "AGENTS.md").read_bytes(), (ROOT / "CLAUDE.md").read_bytes()
        )

    def test_always_loaded_instructions_are_concise(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertEqual(agents, claude)
        self.assertLessEqual(len(agents.splitlines()), 200)
        self.assertLessEqual(len(agents.split()), 1550)
        for term in (
            "Expected files",
            "Done clean",
            "one primary agent",
            "Visible conversations",
            "Use subagents",
            "fetch remote refs",
            "Never commit directly to `main`",
        ):
            self.assertIn(term, agents)

    def test_legacy_skills_are_not_discoverable(self) -> None:
        for name in LEGACY:
            with self.subTest(name=name):
                self.assertFalse((SKILLS / name / "SKILL.md").exists())

    def test_retiable_private_invocations_route_without_alias_directories(self) -> None:
        expected = {
            "nobrainer-ultra": ("nb-flow", "nb-workflow"),
            "nobrainer-team": ("nobrainer-skill-browser",),
            "nobrainer-dispatcher": ("nb-dispatcher",),
            "nobrainer-build": ("engineering-standards", "nobrainer-simplifier"),
            "nobrainer-writing": (
                "nobrainer-style",
                "nobrainer-human-like",
                "nb-brief",
            ),
            "nobrainer-security": ("security-review",),
            "nobrainer-sessions": ("nb-multi", "session-handoff", "session-restart", "nb-session-restart"),
            "nobrainer-wiki": ("nb-add", "nb-get", "nb-tidy"),
            "nobrainer-autoimprove": (
                "deep-autoresearch",
                "code-autoresearch",
                "nobrainer-capture-lesson",
            ),
            "nobrainer-decide": ("deep-decide",),
            "nobrainer-rca": ("deep-rca",),
            "nobrainer-review": ("deep-audit", "deep-code-review"),
        }
        for name, triggers in expected.items():
            description = parse_frontmatter(SKILLS / name / "SKILL.md")[
                "description"
            ]
            for trigger in triggers:
                self.assertIn(trigger, description, f"{name}: missing {trigger}")

    def test_installer_migrates_every_retired_name(self) -> None:
        self.assertEqual(ACTIVE, set(install_skills.CURATED_SKILLS))
        self.assertLessEqual(
            validate_skills.LEGACY,
            set(install_skills.LEGACY_TO_CANONICAL),
        )
        self.assertLessEqual(
            set(install_skills.LEGACY_TO_CANONICAL.values()),
            ACTIVE,
        )

    def test_unknown_private_audit_skill_has_no_unsafe_migration(self) -> None:
        name = "nobrainer-fast-audit"
        curation = (ROOT / "docs" / "SKILL_CURATION.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn(name, install_skills.LEGACY_TO_CANONICAL)
        self.assertIn(name, install_skills.UNMAPPED_LEGACY)
        self.assertIn(f"`{name}` is currently `UNKNOWN`", curation)
        self.assertIn("clean-session parity check", curation)

    def test_public_clean_suite(self) -> None:
        forbidden = (
            "/Users/",
            "/opt/homebrew/",
            "/private/tmp/",
            "nobrainer-tech@",
            "--dangerously-skip-permissions",
            "CLAUDE-CODE-FABLE",
        )
        for name in CANONICAL:
            for path in (SKILLS / name).rglob("*"):
                if not path.is_file() or path.suffix not in {".md", ".yaml", ".yml", ".json"}:
                    continue
                text = path.read_text(encoding="utf-8")
                for value in forbidden:
                    self.assertNotIn(value, text, f"{path}: forbidden public value")

    def test_multi_harness_adapters(self) -> None:
        required = (
            "adapters/bootstrap.md",
            ".claude-plugin/plugin.json",
            ".codex-plugin/plugin.json",
            ".cursor-plugin/plugin.json",
            ".kimi-plugin/plugin.json",
            ".pi/extensions/nobrainer-tech-skills.js",
            "GEMINI.md",
            "gemini-extension.json",
            "hooks/claude-hooks.json",
            "hooks/hooks-cursor.json",
            "hooks/run-hook.cmd",
            "hooks/session-start",
            ".opencode/INSTALL.md",
            ".github/copilot-instructions.md",
            "docs/INSTALL.md",
        )
        for relative in required:
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file(), f"missing {relative}")

        manifests = (
            "plugin.json",
            ".claude-plugin/plugin.json",
            ".claude-plugin/marketplace.json",
            ".codex-plugin/plugin.json",
            ".agents/plugins/marketplace.json",
            ".cursor-plugin/plugin.json",
            ".kimi-plugin/plugin.json",
            "gemini-extension.json",
            "package.json",
        )
        for relative in manifests:
            with self.subTest(manifest=relative):
                json.loads((ROOT / relative).read_text(encoding="utf-8"))

        self.assertFalse((ROOT / ".devin-plugin" / "plugin.json").exists())
        self.assertFalse((ROOT / ".hermes-plugin" / "plugin.yaml").exists())

        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                (
                    "import('./.opencode/plugins/nobrainer-tech-skills.js')"
                    ".then(async m => { const p = await m.default(); const c = {}; "
                    "await p.config(c); if (!c.skills?.paths?.some(x => "
                    "x.endsWith('/skills'))) process.exit(2); })"
                ),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_compatibility_separates_repository_client_and_runtime_proof(self) -> None:
        text = (ROOT / "docs" / "COMPATIBILITY.md").read_text(encoding="utf-8")
        pull_request_template = (
            ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md"
        ).read_text(encoding="utf-8")
        for level in (
            "SOURCE_VALIDATED",
            "REPOSITORY_CHECKED",
            "CLIENT_LOADED",
            "RUNTIME_VERIFIED",
            "DISTRIBUTED",
        ):
            self.assertIn(level, text)
            self.assertIn(level, pull_request_template)
        for surface in (text, pull_request_template):
            self.assertNotIn("ADAPTER_VALIDATED", surface)
        self.assertIn("RUNTIME_VERIFIED_EXPLICIT", text)
        self.assertIn(
            "under explicit invocation; this does not prove discovery", text
        )

    def test_release_heading_parser_requires_one_unfenced_exact_line(self) -> None:
        heading = "## v1.1.0 — 2026-08-28"
        sample = (
            f"inline {heading}\n"
            "## v1.1.0-rc\n"
            f"```md\n{heading}\n```\n"
            f"~~~text\n{heading}\n~~~~\n"
            f"{heading}\n"
        )
        spans = markdown_heading_spans(sample, heading)
        self.assertEqual(1, len(spans))
        start, end = spans[0]
        self.assertEqual(heading, sample[start:end])
        self.assertEqual(
            [], markdown_heading_spans(f"```md\n{heading}\n```\n", heading)
        )
        self.assertEqual(
            1,
            len(markdown_heading_spans(f"``` `\n{heading}\n", heading)),
        )
        with self.assertRaisesRegex(ValueError, "raw HTML"):
            markdown_heading_spans(f"<div>\n{heading}\n</div>\n", heading)

    def test_release_evidence_parser_requires_one_exact_closed_block(self) -> None:
        valid = "# Evidence\n\n```text\nVERSION: 1.2.1\nSTATUS: PASS\n```\n"
        self.assertEqual(
            {"VERSION": "1.2.1", "STATUS": "PASS"},
            parse_release_evidence(valid),
        )
        invalid_documents = (
            "```text\nVERSION: 1.2.1\n",
            "```\n```text\nVERSION: 1.2.1\n```\n",
            valid + "```text\n",
            "```text\nVERSION: 1.2.1\n```text\n```\n",
            "```text\nVERSION: 1.2.1\n```\n~~~\n",
            "```text\nmalformed\n```\n",
        )
        for document in invalid_documents:
            with self.subTest(document=document):
                with self.assertRaises(AssertionError):
                    parse_release_evidence(document)

    def test_v1_0_release_readback_remains_explicit(self) -> None:
        release_notes = (ROOT / "RELEASE-NOTES.md").read_text(encoding="utf-8")
        normalized_notes = " ".join(release_notes.split())
        compatibility = (ROOT / "docs" / "COMPATIBILITY.md").read_text(
            encoding="utf-8"
        )
        release_evidence = (
            ROOT / "docs" / "releases" / "v1.0.0.md"
        ).read_text(encoding="utf-8")
        version = "1.0.0"
        release_sha = "55c49f40d7dc4ebe900f139711cd46617c706233"
        self.assertIn(release_sha, release_notes)
        self.assertIn(f"## v{version}", release_notes)
        self.assertIn(
            "This version is published as a tagged GitHub source release",
            normalized_notes,
        )
        self.assertIn("docs/releases/v1.0.0.md", release_notes)
        self.assertIn("`DISTRIBUTED` for `v1.5.0`", compatibility)
        self.assertIn("publication evidence", compatibility)
        self.assertNotIn("does not claim publication", release_notes)
        self.assertIn(
            "This is not a claim of publication in npm or any client marketplace",
            normalized_notes,
        )
        evidence_pairs = re.findall(
            r"^([A-Z][A-Z0-9_]+): (.+)$", release_evidence, re.MULTILINE
        )
        evidence = dict(evidence_pairs)
        self.assertEqual(len(evidence_pairs), len(evidence))
        self.assertEqual(f"v{version}", evidence["TAG"])
        self.assertEqual(version, evidence["VERSION"])
        self.assertEqual(release_sha, evidence["COMMIT_SHA"])
        tag_readback = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/tags/v{version}^{{commit}}"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if tag_readback.returncode == 0:
            tag_tree_readback = subprocess.run(
                [
                    "git",
                    "rev-parse",
                    "--verify",
                    f"{tag_readback.stdout.strip()}^{{tree}}",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, tag_tree_readback.returncode, tag_tree_readback.stderr)
            self.assertEqual(evidence["TREE_SHA"], tag_tree_readback.stdout.strip())
        self.assertRegex(evidence["COMMIT_SHA"], r"^[0-9a-f]{40}$")
        self.assertRegex(evidence["TREE_SHA"], r"^[0-9a-f]{40}$")
        self.assertRegex(evidence["TARBALL_SHA256"], r"^[0-9a-f]{64}$")
        self.assertTrue(evidence["RELEASE_URL"].endswith(f"/tag/{evidence['TAG']}"))
        self.assertTrue(evidence["TARBALL_URL"].endswith(f"/{evidence['TAG']}"))
        self.assertEqual(f"{evidence['TAG']}.tar.gz", evidence["TARBALL_FILENAME"])
        self.assertEqual("false", evidence["GITHUB_RELEASE_IMMUTABLE"])
        self.assertEqual("PASS", evidence["ARCHIVE_FILE_MATCH"])
        self.assertEqual("9", evidence["ARCHIVE_SKILL_COUNT"])
        self.assertEqual("57/57 PASS", evidence["ARCHIVE_TESTS"])
        self.assertEqual("codex", evidence["INSTALL_CLIENT"])
        self.assertEqual("PASS", evidence["INSTALL_READBACK"])

    def test_v1_1_release_readback_remains_explicit(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        release_notes = (ROOT / "RELEASE-NOTES.md").read_text(encoding="utf-8")
        normalized_notes = " ".join(release_notes.split())
        release_evidence = (
            ROOT / "docs" / "releases" / "v1.1.0.md"
        ).read_text(encoding="utf-8")
        v1_1_spans = markdown_heading_spans(
            release_notes, "## v1.1.0 — 2026-08-28"
        )
        v1_0_spans = markdown_heading_spans(
            release_notes, "## v1.0.0 — 2026-08-28"
        )
        self.assertEqual(1, len(v1_1_spans))
        self.assertEqual(1, len(v1_0_spans))
        _, v1_1_end = v1_1_spans[0]
        v1_0_start, _ = v1_0_spans[0]
        self.assertLess(v1_1_end, v1_0_start)
        section = release_notes[v1_1_end:v1_0_start]
        released_skills = re.findall(
            r"^- `(nobrainer-[a-z0-9-]+)`$", section, re.MULTILINE
        )
        release_sha = "711be31d654835a04ef8c70674c3e493aeb2da8a"
        expected_skills = [
            name
            for name in HISTORICAL_CANONICAL_ORDER
            if name not in {"nobrainer-dispatcher", "nobrainer-writing"}
        ]
        self.assertEqual(expected_skills, released_skills)
        self.assertNotIn("release candidate", section.lower())
        self.assertIn(
            "This version is published as a tagged GitHub source release",
            normalized_notes,
        )
        self.assertIn(release_sha, readme)
        self.assertIn(release_sha, release_notes)
        self.assertIn("docs/releases/v1.1.0.md", readme)
        rollback_paragraphs = [
            paragraph
            for paragraph in readme.split("\n\n")
            if "[`v1.1.0`](docs/releases/v1.1.0.md)" in paragraph
        ]
        self.assertEqual(1, len(rollback_paragraphs))
        self.assertIn(f"commit `{release_sha}`", rollback_paragraphs[0])

        evidence_pairs = re.findall(
            r"^([A-Z][A-Z0-9_]+): (.+)$", release_evidence, re.MULTILINE
        )
        evidence = dict(evidence_pairs)
        self.assertEqual(len(evidence_pairs), len(evidence))
        self.assertEqual("1.1.0", evidence["VERSION"])
        self.assertEqual("v1.1.0", evidence["TAG"])
        self.assertEqual(release_sha, evidence["COMMIT_SHA"])
        tag_readback = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/tags/v1.1.0^{commit}"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if tag_readback.returncode == 0:
            tag_tree_readback = subprocess.run(
                [
                    "git",
                    "rev-parse",
                    "--verify",
                    f"{tag_readback.stdout.strip()}^{{tree}}",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, tag_tree_readback.returncode, tag_tree_readback.stderr)
            self.assertEqual(evidence["TREE_SHA"], tag_tree_readback.stdout.strip())
        self.assertEqual("false", evidence["GITHUB_RELEASE_IMMUTABLE"])
        self.assertEqual("PASS", evidence["ARCHIVE_FILE_MATCH"])
        self.assertEqual("13", evidence["ARCHIVE_SKILL_COUNT"])
        self.assertEqual("70/70 PASS", evidence["ARCHIVE_TESTS"])
        self.assertEqual("13/13 PASS", evidence["ARCHIVE_QUICK_VALIDATE"])
        self.assertEqual("PASS", evidence["ARCHIVE_SECRET_SCAN"])
        self.assertEqual("agents", evidence["INSTALL_CLIENT"])
        self.assertEqual("copy", evidence["INSTALL_MODE"])
        self.assertEqual("PASS", evidence["INSTALL_READBACK"])

    def test_v1_2_0_readback_records_archive_acceptance_failure(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        release_notes = (ROOT / "RELEASE-NOTES.md").read_text(encoding="utf-8")
        release_evidence = (
            ROOT / "docs" / "releases" / "v1.2.0.md"
        ).read_text(encoding="utf-8")
        v1_2_0_spans = markdown_heading_spans(
            release_notes, "## v1.2.0 — 2026-08-28"
        )
        v1_1_spans = markdown_heading_spans(
            release_notes, "## v1.1.0 — 2026-08-28"
        )
        self.assertEqual(1, len(v1_2_0_spans))
        self.assertEqual(1, len(v1_1_spans))
        _, v1_2_0_end = v1_2_0_spans[0]
        v1_1_start, _ = v1_1_spans[0]
        self.assertLess(v1_2_0_end, v1_1_start)
        section = release_notes[v1_2_0_end:v1_1_start]
        released_skills = re.findall(
            r"^- `(nobrainer-[a-z0-9-]+)`$", section, re.MULTILINE
        )
        self.assertEqual(list(HISTORICAL_CANONICAL_ORDER), released_skills)
        self.assertIn("published but not fully accepted", section)
        self.assertIn("docs/releases/v1.2.0.md", readme)

        evidence = parse_release_evidence(release_evidence)
        self.assertEqual(
            {
                "VERSION",
                "TAG",
                "COMMIT_SHA",
                "TREE_SHA",
                "RELEASE_URL",
                "TARBALL_URL",
                "TARBALL_FILENAME",
                "TARBALL_SHA256",
                "PR_CI_RUN",
                "MAIN_CI_RUN",
                "GITHUB_RELEASE_IMMUTABLE",
                "TAG_PROTECTION_STATUS",
                "ARCHIVE_FILE_MATCH",
                "ARCHIVE_SKILL_COUNT",
                "REPOSITORY_TESTS_PASSED",
                "REPOSITORY_TESTS_FAILED",
                "REPOSITORY_TESTS_TOTAL",
                "REPOSITORY_TESTS_STATUS",
                "ARCHIVE_TESTS_PASSED",
                "ARCHIVE_TESTS_FAILED",
                "ARCHIVE_TESTS_TOTAL",
                "ARCHIVE_TESTS_STATUS",
                "ARCHIVE_TEST_FAILURE",
                "ARCHIVE_QUICK_VALIDATE",
                "ARCHIVE_SOURCE_SECRET_SCAN",
                "INSTALL_READBACK",
                "ACCEPTANCE",
                "PLANNED_REMEDIATION",
                "PLANNED_REMEDIATION_STATUS_AT_READBACK",
                "SUPERSEDED_BY",
                "SUPERSEDING_RELEASE_ACCEPTANCE",
                "ROLLBACK_COMMIT_SHA",
                "ROLLBACK_TARBALL_SHA256",
            },
            set(evidence),
        )
        self.assertEqual("1.2.0", evidence["VERSION"])
        self.assertEqual("v1.2.0", evidence["TAG"])
        self.assertEqual(
            "46feb1e95567db6967ea718cb75051c507ada02f",
            evidence["COMMIT_SHA"],
        )
        tag_readback = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/tags/v1.2.0^{commit}"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if tag_readback.returncode == 0:
            tag_tree_readback = subprocess.run(
                [
                    "git",
                    "rev-parse",
                    "--verify",
                    f"{tag_readback.stdout.strip()}^{{tree}}",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, tag_tree_readback.returncode, tag_tree_readback.stderr)
            self.assertEqual(evidence["TREE_SHA"], tag_tree_readback.stdout.strip())
        self.assertEqual("PASS", evidence["ARCHIVE_FILE_MATCH"])
        self.assertEqual("15", evidence["ARCHIVE_SKILL_COUNT"])
        self.assertEqual("86", evidence["REPOSITORY_TESTS_PASSED"])
        self.assertEqual("0", evidence["REPOSITORY_TESTS_FAILED"])
        self.assertEqual("86", evidence["REPOSITORY_TESTS_TOTAL"])
        self.assertEqual("PASS", evidence["REPOSITORY_TESTS_STATUS"])
        self.assertEqual("85", evidence["ARCHIVE_TESTS_PASSED"])
        self.assertEqual("1", evidence["ARCHIVE_TESTS_FAILED"])
        self.assertEqual("86", evidence["ARCHIVE_TESTS_TOTAL"])
        self.assertEqual("FAIL", evidence["ARCHIVE_TESTS_STATUS"])
        self.assertEqual("PASS", evidence["ARCHIVE_SOURCE_SECRET_SCAN"])
        self.assertEqual("FAIL", evidence["ACCEPTANCE"])
        self.assertEqual("v1.2.1", evidence["PLANNED_REMEDIATION"])
        self.assertEqual(
            "UNVERIFIED_RELEASE_CANDIDATE",
            evidence["PLANNED_REMEDIATION_STATUS_AT_READBACK"],
        )
        self.assertEqual("v1.2.1", evidence["SUPERSEDED_BY"])
        self.assertEqual("PASS", evidence["SUPERSEDING_RELEASE_ACCEPTANCE"])
        self.assertEqual("NOT_VERIFIED", evidence["TAG_PROTECTION_STATUS"])
        self.assertEqual(
            "711be31d654835a04ef8c70674c3e493aeb2da8a",
            evidence["ROLLBACK_COMMIT_SHA"],
        )
        expected_rollback_tarball = (
            "1a05186234487df1fa2381a291b53141a5fad6347d24f1638fc86b961abb7f5e"
        )
        self.assertEqual(
            expected_rollback_tarball,
            evidence["ROLLBACK_TARBALL_SHA256"],
        )
        rollback_text = (
            ROOT / "docs" / "releases" / "v1.1.0.md"
        ).read_text(encoding="utf-8")
        rollback_pairs = re.findall(
            r"^([A-Z][A-Z0-9_]+): (.+)$", rollback_text, re.MULTILINE
        )
        rollback_evidence = dict(rollback_pairs)
        self.assertEqual(len(rollback_pairs), len(rollback_evidence))
        self.assertEqual(
            evidence["ROLLBACK_COMMIT_SHA"],
            rollback_evidence["COMMIT_SHA"],
        )
        self.assertEqual(
            evidence["ROLLBACK_TARBALL_SHA256"],
            rollback_evidence["TARBALL_SHA256"],
        )

    def test_v1_2_1_release_readback_remains_explicit(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        release_notes = (ROOT / "RELEASE-NOTES.md").read_text(encoding="utf-8")
        release_evidence = (
            ROOT / "docs" / "releases" / "v1.2.1.md"
        ).read_text(encoding="utf-8")
        historical = "1.2.1"
        current_spans = markdown_heading_spans(
            release_notes,
            f"## v{historical} — 2026-08-28",
        )
        v1_2_0_spans = markdown_heading_spans(
            release_notes, "## v1.2.0 — 2026-08-28"
        )
        self.assertEqual(1, len(current_spans))
        self.assertEqual(1, len(v1_2_0_spans))
        _, current_end = current_spans[0]
        v1_2_0_start, _ = v1_2_0_spans[0]
        self.assertLess(current_end, v1_2_0_start)
        section = release_notes[current_end:v1_2_0_start]
        released_skills = re.findall(
            r"^- `(nobrainer-[a-z0-9-]+)`$", section, re.MULTILINE
        )
        self.assertEqual(list(HISTORICAL_CANONICAL_ORDER), released_skills)
        self.assertEqual(HISTORICAL_ACTIVE, set(released_skills))
        normalized_section = " ".join(re.findall(r"[a-z0-9]+", section.lower()))
        self.assertNotIn("release candidate", normalized_section)
        self.assertNotIn("not a publication claim", normalized_section)
        self.assertIn(
            "This version is published as a tagged GitHub source release",
            section,
        )
        self.assertIn(
            "0010140d19a7ff847dff776569772ef04d82c314",
            readme,
        )
        self.assertIn("docs/releases/v1.2.1.md", readme)

        evidence = parse_release_evidence(release_evidence)
        self.assertEqual(
            {
                "VERSION",
                "TAG",
                "COMMIT_SHA",
                "TREE_SHA",
                "RELEASE_URL",
                "TARBALL_URL",
                "TARBALL_FILENAME",
                "TARBALL_SHA256",
                "PR_CI_RUN",
                "MAIN_CI_RUN",
                "GITHUB_RELEASE_IMMUTABLE",
                "TAG_PROTECTION_STATUS",
                "ARCHIVE_FILE_MATCH",
                "ARCHIVE_SKILL_COUNT",
                "ARCHIVE_TESTS_PASSED",
                "ARCHIVE_TESTS_FAILED",
                "ARCHIVE_TESTS_TOTAL",
                "ARCHIVE_TESTS_STATUS",
                "ARCHIVE_QUICK_VALIDATE",
                "ARCHIVE_SECRET_SCAN",
                "INSTALL_CLIENT",
                "INSTALL_MODE",
                "INSTALL_SKILL_COUNT",
                "INSTALL_FILE_MATCH",
                "INSTALL_QUICK_VALIDATE",
                "INSTALL_READBACK",
                "ACCEPTANCE",
            },
            set(evidence),
        )
        self.assertEqual("1.2.1", evidence["VERSION"])
        self.assertEqual("v1.2.1", evidence["TAG"])
        self.assertEqual(
            "0010140d19a7ff847dff776569772ef04d82c314",
            evidence["COMMIT_SHA"],
        )
        tag_readback = subprocess.run(
            ["git", "rev-parse", "--verify", "refs/tags/v1.2.1^{commit}"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if tag_readback.returncode == 0:
            tag_tree_readback = subprocess.run(
                [
                    "git",
                    "rev-parse",
                    "--verify",
                    f"{tag_readback.stdout.strip()}^{{tree}}",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, tag_tree_readback.returncode, tag_tree_readback.stderr)
            self.assertEqual(evidence["TREE_SHA"], tag_tree_readback.stdout.strip())
        self.assertEqual("PASS", evidence["ARCHIVE_FILE_MATCH"])
        self.assertEqual("15", evidence["ARCHIVE_SKILL_COUNT"])
        self.assertEqual("88", evidence["ARCHIVE_TESTS_PASSED"])
        self.assertEqual("0", evidence["ARCHIVE_TESTS_FAILED"])
        self.assertEqual("88", evidence["ARCHIVE_TESTS_TOTAL"])
        self.assertEqual("PASS", evidence["ARCHIVE_TESTS_STATUS"])
        self.assertEqual("PASS", evidence["ARCHIVE_SECRET_SCAN"])
        self.assertEqual("agents", evidence["INSTALL_CLIENT"])
        self.assertEqual("copy", evidence["INSTALL_MODE"])
        self.assertEqual("15", evidence["INSTALL_SKILL_COUNT"])
        self.assertEqual("PASS", evidence["INSTALL_FILE_MATCH"])
        self.assertEqual("PASS", evidence["INSTALL_READBACK"])
        self.assertEqual("PASS", evidence["ACCEPTANCE"])

    def test_v1_3_candidate_and_publication_readbacks_are_explicit(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        release_notes = (ROOT / "RELEASE-NOTES.md").read_text(encoding="utf-8")
        release_evidence = (
            ROOT / "docs" / "releases" / "v1.3.0.md"
        ).read_text(encoding="utf-8")
        publication_readback = (
            ROOT / "docs" / "releases" / "v1.3.0-publication-readback.md"
        ).read_text(encoding="utf-8")
        evaluation = (
            ROOT
            / "docs"
            / "evals"
            / "v1.3.0-autoimprove-integrity-2026-09-01.md"
        ).read_text(encoding="utf-8")
        receipt = (
            ROOT
            / "docs"
            / "evals"
            / "artifacts"
            / "v1.3.0-autoimprove-integrity-final5-receipt.md"
        ).read_text(encoding="utf-8")

        current_spans = markdown_heading_spans(
            release_notes, "## v1.3.0 — 2026-09-01"
        )
        accepted_spans = markdown_heading_spans(
            release_notes, "## v1.2.1 — 2026-08-28"
        )
        self.assertEqual(1, len(current_spans))
        self.assertEqual(1, len(accepted_spans))
        _, current_end = current_spans[0]
        accepted_start, _ = accepted_spans[0]
        self.assertLess(current_end, accepted_start)
        section = release_notes[current_end:accepted_start]
        self.assertEqual(
            list(HISTORICAL_CANONICAL_ORDER),
            re.findall(
                r"^- `(nobrainer-[a-z0-9-]+)`$", section, re.MULTILINE
            ),
        )
        self.assertNotIn("not a merged, tagged, distributed", section.lower())
        self.assertIn(
            "The source release is merged in PR #31 at commit\n"
            "`8ae4a26548ce908fc5f98b22663f52e163541f56`, tagged as `v1.3.0` and published on\n"
            "GitHub.",
            section,
        )

        evidence = parse_release_evidence(release_evidence)
        self.assertEqual("1.3.0", evidence["VERSION"])
        self.assertEqual("RELEASE_CANDIDATE", evidence["STATUS"])
        self.assertEqual("15", evidence["SKILL_COUNT"])
        self.assertEqual("PROMOTED_FINAL5", evidence["AUTOIMPROVE_RESULT"])
        self.assertEqual("CALIBRATED", evidence["AUTOIMPROVE_EVALUATOR"])
        self.assertEqual("PASS", evidence["AUTOIMPROVE_HOLDOUT"])
        self.assertEqual("PASS", evidence["DETERMINISTIC_TESTS_STATUS"])
        self.assertEqual("PASS", evidence["SECRET_SCAN"])
        self.assertEqual("FETCH_ONLY", evidence["PUBLIC_SYNC"])
        self.assertEqual("BLOCKED", evidence["AUTOMATED_PUBLIC_COMMIT_PUSH"])
        self.assertEqual("NOT_PERFORMED", evidence["MERGE"])
        self.assertEqual("NOT_CREATED", evidence["TAG"])
        self.assertEqual("NOT_PUBLISHED", evidence["DISTRIBUTION"])
        self.assertEqual("PASS_LOCAL_PR_CANDIDATE", evidence["ACCEPTANCE"])

        publication = parse_release_evidence(publication_readback)
        self.assertEqual("1.3.0", publication["VERSION"])
        self.assertEqual("PUBLISHED", publication["STATUS"])
        self.assertEqual("15", publication["SKILL_COUNT"])
        self.assertEqual("PROMOTED_FINAL5", publication["AUTOIMPROVE_RESULT"])
        self.assertEqual("CALIBRATED", publication["AUTOIMPROVE_EVALUATOR"])
        self.assertEqual("PASS", publication["AUTOIMPROVE_HOLDOUT"])
        self.assertEqual("PASS", publication["DETERMINISTIC_TESTS_STATUS"])
        self.assertEqual("PASS", publication["SECRET_SCAN"])
        self.assertEqual("FETCH_ONLY", publication["PUBLIC_SYNC"])
        self.assertEqual("31", publication["MERGE_PR"])
        self.assertEqual("MERGED", publication["MERGE"])
        self.assertEqual(
            "8ae4a26548ce908fc5f98b22663f52e163541f56",
            publication["COMMIT_SHA"],
        )
        self.assertEqual(
            "726162390429c18db8c504833a502aeb0db09d41",
            publication["TREE_SHA"],
        )
        self.assertEqual("v1.3.0", publication["TAG"])
        self.assertEqual(
            "e7a76dd85cc3b2c101f7d1619f08022b903758bd",
            publication["TAG_OBJECT_SHA"],
        )
        self.assertEqual(publication["COMMIT_SHA"], publication["TAG_COMMIT_SHA"])
        self.assertEqual("main", publication["TARGET_COMMITISH"])
        self.assertEqual("33558906561", publication["CI_UBUNTU_RUN"])
        self.assertEqual("33558906561", publication["CI_MACOS_RUN"])
        self.assertEqual("false", publication["GITHUB_RELEASE_IMMUTABLE"])
        self.assertEqual("NOT_VERIFIED", publication["TAG_PROTECTION_STATUS"])
        self.assertEqual("false", publication["RELEASE_DRAFT"])
        self.assertEqual("false", publication["RELEASE_PRERELEASE"])
        self.assertEqual(
            "https://github.com/nobrainer-tech/nobrainer-tech-skills/releases/tag/v1.3.0",
            publication["RELEASE_URL"],
        )
        self.assertEqual(
            "https://github.com/nobrainer-tech/nobrainer-tech-skills/archive/refs/tags/v1.3.0.tar.gz",
            publication["SOURCE_ARCHIVE_URL"],
        )
        self.assertEqual("v1.3.0.tar.gz", publication["SOURCE_ARCHIVE_FILENAME"])
        self.assertEqual(
            "cb6e270c261585ef133e0bbb419605e63abe562b46d12df88015c8861d25317a",
            publication["SOURCE_ARCHIVE_SHA256"],
        )
        self.assertEqual("PASS", publication["SOURCE_ARCHIVE_TREE_MATCH"])
        self.assertEqual("0", publication["SOURCE_ARCHIVE_PYCACHE_COUNT"])
        self.assertEqual("15", publication["SOURCE_ARCHIVE_SKILL_COUNT"])
        self.assertEqual("PASS", publication["SOURCE_ARCHIVE_VALIDATOR"])
        self.assertEqual("102/102 PASS", publication["SOURCE_ARCHIVE_TESTS"])
        self.assertEqual("PASS", publication["SOURCE_ARCHIVE_SECRET_SCAN"])
        self.assertEqual("codex", publication["INSTALL_CLIENT"])
        self.assertEqual("copy", publication["INSTALL_MODE"])
        self.assertEqual("15", publication["INSTALL_SKILL_COUNT"])
        self.assertEqual("PASS", publication["INSTALL_FILE_MATCH"])
        self.assertEqual("PASS", publication["INSTALL_READBACK"])
        self.assertEqual("PUBLISHED", publication["DISTRIBUTION"])
        self.assertEqual("PASS_RELEASE", publication["ACCEPTANCE"])

        if (ROOT / ".git").exists():
            tag_object_readback = subprocess.run(
                ["git", "rev-parse", "--verify", "refs/tags/v1.3.0"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            if tag_object_readback.returncode == 0:
                self.assertEqual(
                    publication["TAG_OBJECT_SHA"],
                    tag_object_readback.stdout.strip(),
                )
                tag_readback = subprocess.run(
                    ["git", "rev-parse", "--verify", "refs/tags/v1.3.0^{commit}"],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, tag_readback.returncode, tag_readback.stderr)
                self.assertEqual(publication["COMMIT_SHA"], tag_readback.stdout.strip())
                tag_tree_readback = subprocess.run(
                    [
                        "git",
                        "rev-parse",
                        "--verify",
                        f"{tag_readback.stdout.strip()}^{{tree}}",
                    ],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, tag_tree_readback.returncode, tag_tree_readback.stderr)
                self.assertEqual(publication["TREE_SHA"], tag_tree_readback.stdout.strip())
            else:
                if os.environ.get("NOBRAINER_REQUIRE_RELEASE_TAG") == "1":
                    self.fail(
                        "v1.3.0 tag is required for release readback in the "
                        "release-validation checkout: "
                        + tag_object_readback.stderr.strip()
                    )
                self.skipTest(
                    "v1.3.0 tag is unavailable in this checkout; release tag "
                    "identity is unverified (set NOBRAINER_REQUIRE_RELEASE_TAG=1 "
                    "for a strict release gate)"
                )

        evaluation_candidate = re.search(
            r"^CANDIDATE_SHA256: `?([0-9a-f]{64})`?$",
            evaluation,
            re.MULTILINE,
        )
        receipt_candidate = re.search(
            r"^CANDIDATE_SHA256: `?([0-9a-f]{64})`?$",
            receipt,
            re.MULTILINE,
        )
        evaluation_counter = re.search(
            r"^COUNTER_SHA256: `?([0-9a-f]{64})`?$",
            evaluation,
            re.MULTILINE,
        )
        receipt_counter = re.search(
            r"^COUNTER_SHA256: `?([0-9a-f]{64})`?$",
            receipt,
            re.MULTILINE,
        )
        for match in (
            evaluation_candidate,
            receipt_candidate,
            evaluation_counter,
            receipt_counter,
        ):
            self.assertIsNotNone(match)
        self.assertEqual(evaluation_candidate.group(1), receipt_candidate.group(1))
        self.assertEqual(evaluation_counter.group(1), receipt_counter.group(1))
        self.assertIn("PROMOTION: PROMOTED", evaluation)
        self.assertIn("HOLDOUT_RESULT: PASS", evaluation)
        self.assertIn("EVALUATOR_STATUS: CALIBRATED", evaluation)
        self.assertIn("NOISE_RESULT: 3 paired repetitions", evaluation)
        self.assertIn("PARETO_DECISION: promoted after closing the largest", evaluation)
        self.assertIn("SCORE_RECEIPT: artifacts/v1.3.0-autoimprove-integrity-final5-receipt.md", evaluation)
        self.assertIn("CANDIDATE_SHA256:", receipt)
        self.assertIn("HOLDOUT_SHA256:", receipt)
        self.assertIn("CALIBRATION: PASS", receipt)
        self.assertIn("TERRA: candidate 3/3", receipt)
        self.assertIn("SOL: candidate 3/3", receipt)
        for document in (evaluation, receipt, publication_readback):
            for private_root in ("/" + "Users/", "/" + "Volumes/", "/" + "tmp/"):
                self.assertNotIn(private_root, document)

        self.assertIn("v1.3.0", readme)
        self.assertIn("previous accepted source release", readme)
        self.assertIn(
            "8ae4a26548ce908fc5f98b22663f52e163541f56",
            readme,
        )
        self.assertIn("docs/releases/v1.3.0-publication-readback.md", readme)

    def test_v1_3_1_publication_readback_is_explicit(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        release_notes = (ROOT / "RELEASE-NOTES.md").read_text(encoding="utf-8")
        compatibility = (ROOT / "docs" / "COMPATIBILITY.md").read_text(
            encoding="utf-8"
        )
        publication = (
            ROOT / "docs" / "releases" / "v1.3.1-publication-readback.md"
        ).read_text(encoding="utf-8")
        evaluation = (
            ROOT
            / "docs"
            / "evals"
            / "v1.3.1-writing-brief-2026-09-02.md"
        ).read_text(encoding="utf-8")

        current_spans = markdown_heading_spans(
            release_notes, "## v1.3.1 — 2026-09-02"
        )
        prior_spans = markdown_heading_spans(
            release_notes, "## v1.3.0 — 2026-09-01"
        )
        self.assertEqual(1, len(current_spans))
        self.assertEqual(1, len(prior_spans))
        _, current_end = current_spans[0]
        prior_start, _ = prior_spans[0]
        self.assertLess(current_end, prior_start)
        release_section = release_notes[current_end:prior_start]
        self.assertEqual(
            list(HISTORICAL_CANONICAL_ORDER),
            re.findall(
                r"^- `(nobrainer-[a-z0-9-]+)`$",
                release_section,
                re.MULTILINE,
            ),
        )
        self.assertNotIn("release candidate", release_section.lower())
        self.assertIn(
            "The source release is merged in PR #33 at commit\n"
            "`d1e0ea761d4bf439973727668ee871e2b367797e`, tagged as `v1.3.1`",
            release_section,
        )
        self.assertIn("docs/releases/v1.3.1-publication-readback.md", readme)
        self.assertIn("previous accepted source release", readme)
        self.assertIn("v1.3.1", compatibility)
        self.assertIn("HOLDOUT_RESULT: PASS 5/5", evaluation)

        evidence = parse_release_evidence(publication)
        expected_keys = {
            "VERSION",
            "STATUS",
            "RELEASE_DATE",
            "SKILL_COUNT",
            "PORTFOLIO",
            "WRITING_BRIEF_RESULT",
            "WRITING_BRIEF_HOLDOUT",
            "WRITING_BRIEF_EVALUATION",
            "INDEPENDENT_REVIEW",
            "INDEPENDENT_REVIEW_SESSION",
            "DETERMINISTIC_TESTS_TOTAL",
            "DETERMINISTIC_TESTS_STATUS",
            "SECRET_SCAN",
            "PUBLIC_SYNC",
            "AUTOMATED_PUBLIC_COMMIT_PUSH",
            "MERGE_PR",
            "MERGE",
            "COMMIT_SHA",
            "TREE_SHA",
            "TAG",
            "TAG_OBJECT_SHA",
            "TAG_COMMIT_SHA",
            "TARGET_COMMITISH",
            "CI_PR_RUN",
            "CI_MAIN_RUN",
            "GITHUB_RELEASE_IMMUTABLE",
            "TAG_PROTECTION_STATUS",
            "RELEASE_DRAFT",
            "RELEASE_PRERELEASE",
            "RELEASE_PUBLISHED_AT",
            "RELEASE_URL",
            "SOURCE_ARCHIVE_URL",
            "SOURCE_ARCHIVE_FILENAME",
            "SOURCE_ARCHIVE_SHA256",
            "SOURCE_ARCHIVE_DOWNLOADED_AT",
            "SOURCE_ARCHIVE_TREE_MATCH",
            "SOURCE_ARCHIVE_FILE_COUNT",
            "SOURCE_ARCHIVE_PYCACHE_COUNT",
            "SOURCE_ARCHIVE_SKILL_COUNT",
            "SOURCE_ARCHIVE_VALIDATOR",
            "SOURCE_ARCHIVE_SUITE_VALIDATOR",
            "SOURCE_ARCHIVE_TESTS",
            "SOURCE_ARCHIVE_PYTHON_SYNTAX",
            "SOURCE_ARCHIVE_SHELL_SYNTAX",
            "SOURCE_ARCHIVE_SECRET_SCAN",
            "INSTALL_CLIENT",
            "INSTALL_MODE",
            "INSTALL_SKILL_COUNT",
            "INSTALL_FILE_MATCH",
            "INSTALL_READBACK",
            "DISTRIBUTION",
            "ACCEPTANCE",
        }
        self.assertEqual(expected_keys, set(evidence))
        self.assertEqual("1.3.1", evidence["VERSION"])
        self.assertEqual("PUBLISHED", evidence["STATUS"])
        self.assertEqual("15", evidence["SKILL_COUNT"])
        self.assertEqual("EXACT_FIFTEEN_CANONICAL_NOBRAINER_SKILLS", evidence["PORTFOLIO"])
        self.assertEqual("PASS", evidence["WRITING_BRIEF_RESULT"])
        self.assertEqual("PASS 5/5", evidence["WRITING_BRIEF_HOLDOUT"])
        self.assertEqual("CLEAN", evidence["INDEPENDENT_REVIEW"])
        self.assertEqual("105", evidence["DETERMINISTIC_TESTS_TOTAL"])
        self.assertEqual("PASS", evidence["DETERMINISTIC_TESTS_STATUS"])
        self.assertEqual("PASS", evidence["SECRET_SCAN"])
        self.assertEqual("FETCH_ONLY", evidence["PUBLIC_SYNC"])
        self.assertEqual("BLOCKED", evidence["AUTOMATED_PUBLIC_COMMIT_PUSH"])
        self.assertEqual("33", evidence["MERGE_PR"])
        self.assertEqual("MERGED", evidence["MERGE"])
        self.assertEqual(
            "d1e0ea761d4bf439973727668ee871e2b367797e",
            evidence["COMMIT_SHA"],
        )
        self.assertEqual(
            "1c5c34fd2560f0a4e39e0c05085d350eb404997e",
            evidence["TREE_SHA"],
        )
        self.assertEqual("v1.3.1", evidence["TAG"])
        self.assertEqual(evidence["COMMIT_SHA"], evidence["TAG_COMMIT_SHA"])
        self.assertEqual("main", evidence["TARGET_COMMITISH"])
        self.assertEqual("33617119505", evidence["CI_PR_RUN"])
        self.assertEqual("33617181865", evidence["CI_MAIN_RUN"])
        self.assertEqual("false", evidence["GITHUB_RELEASE_IMMUTABLE"])
        self.assertEqual("NOT_VERIFIED", evidence["TAG_PROTECTION_STATUS"])
        self.assertEqual("false", evidence["RELEASE_DRAFT"])
        self.assertEqual("false", evidence["RELEASE_PRERELEASE"])
        self.assertEqual("v1.3.1.tar.gz", evidence["SOURCE_ARCHIVE_FILENAME"])
        self.assertEqual("79fd101206aa8b1cc6bb3d219f8e984c1a3a34102f01382d687ccec5640d2bc6", evidence["SOURCE_ARCHIVE_SHA256"])
        self.assertEqual("PASS", evidence["SOURCE_ARCHIVE_TREE_MATCH"])
        self.assertEqual("241", evidence["SOURCE_ARCHIVE_FILE_COUNT"])
        self.assertEqual("0", evidence["SOURCE_ARCHIVE_PYCACHE_COUNT"])
        self.assertEqual("15", evidence["SOURCE_ARCHIVE_SKILL_COUNT"])
        self.assertEqual("PASS", evidence["SOURCE_ARCHIVE_VALIDATOR"])
        self.assertEqual("PASS", evidence["SOURCE_ARCHIVE_SUITE_VALIDATOR"])
        self.assertEqual("105/105 PASS", evidence["SOURCE_ARCHIVE_TESTS"])
        self.assertEqual("PASS", evidence["SOURCE_ARCHIVE_PYTHON_SYNTAX"])
        self.assertEqual("PASS", evidence["SOURCE_ARCHIVE_SHELL_SYNTAX"])
        self.assertEqual("PASS", evidence["SOURCE_ARCHIVE_SECRET_SCAN"])
        self.assertEqual("agents", evidence["INSTALL_CLIENT"])
        self.assertEqual("copy", evidence["INSTALL_MODE"])
        self.assertEqual("15", evidence["INSTALL_SKILL_COUNT"])
        self.assertEqual("PASS", evidence["INSTALL_FILE_MATCH"])
        self.assertEqual("PASS", evidence["INSTALL_READBACK"])
        self.assertEqual("PUBLISHED", evidence["DISTRIBUTION"])
        self.assertEqual("PASS_RELEASE", evidence["ACCEPTANCE"])

        if (ROOT / ".git").exists():
            tag_object_readback = subprocess.run(
                ["git", "rev-parse", "--verify", "refs/tags/v1.3.1"],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            if tag_object_readback.returncode == 0:
                self.assertEqual(
                    evidence["TAG_OBJECT_SHA"],
                    tag_object_readback.stdout.strip(),
                )
                tag_readback = subprocess.run(
                    ["git", "rev-parse", "--verify", "refs/tags/v1.3.1^{commit}"],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, tag_readback.returncode, tag_readback.stderr)
                self.assertEqual(evidence["COMMIT_SHA"], tag_readback.stdout.strip())
                tag_tree_readback = subprocess.run(
                    [
                        "git",
                        "rev-parse",
                        "--verify",
                        f"{tag_readback.stdout.strip()}^{{tree}}",
                    ],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, tag_tree_readback.returncode, tag_tree_readback.stderr)
                self.assertEqual(evidence["TREE_SHA"], tag_tree_readback.stdout.strip())
            elif os.environ.get("NOBRAINER_REQUIRE_RELEASE_TAG") == "1":
                self.fail(
                    "v1.3.1 tag is required for release readback in the "
                    "release-validation checkout: "
                    + tag_object_readback.stderr.strip()
                )

        for document in (publication, evaluation, readme, compatibility):
            for private_root in ("/" + "Users/", "/" + "Volumes/", "/" + "tmp/"):
                self.assertNotIn(private_root, document)

    def test_v1_6_behavior_evidence_matches_frozen_source(self) -> None:
        artifacts = ROOT / "docs" / "evals" / "artifacts" / "v1.6.0"
        bindings = json.loads((artifacts / "candidate-source-hashes.json").read_text())
        self.assertIn("skills/nobrainer-ultra/SKILL.md", bindings)
        self.assertIn("adapters/bootstrap.md", bindings)
        with zipfile.ZipFile(artifacts / "source-snapshot.zip") as frozen:
            self.assertCountEqual(bindings, frozen.namelist())
            for relative, digest in bindings.items():
                with self.subTest(source=relative):
                    path = (ROOT / relative).resolve()
                    self.assertTrue(path.is_relative_to(ROOT.resolve()))
                    self.assertEqual(hashlib.sha256(frozen.read(relative)).hexdigest(), digest)
        receipts = json.loads((artifacts / "smoke-receipts.json").read_text())
        self.assertEqual(
            hashlib.sha256((artifacts / "cases.txt").read_bytes()).hexdigest(),
            receipts["case_sha256"],
        )
        for trial in receipts["trials"]:
            self.assertEqual(
                hashlib.sha256((artifacts / trial["output"]).read_bytes()).hexdigest(),
                trial["output_sha256"],
            )

    def test_v1_6_1_evidence_integrity_and_score_arithmetic(self) -> None:
        artifacts = ROOT / "docs/evals/artifacts/v1.6.1"
        bindings = json.loads((artifacts / "artifact-hashes.json").read_text())
        actual = {str(path.relative_to(artifacts)) for path in artifacts.rglob("*")
                  if path.is_file() and path.name != "artifact-hashes.json"}
        self.assertEqual(set(bindings), actual)
        for relative, digest in bindings.items():
            path = (artifacts / relative).resolve()
            self.assertTrue(path.is_relative_to(artifacts.resolve()))
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        verdict = json.loads((artifacts / "semantic-verdict.json").read_text())
        for variant in ("baseline", "candidate"):
            development = verdict["development"][variant]
            self.assertEqual(development["points"], sum(
                sum(run["case_points"].values()) for run in development["runs"]))
            self.assertEqual(development["hard_gate_clean_runs"], sum(
                run["hard_gates"] == "PASS" for run in development["runs"]))
            for run in development["runs"]:
                output = artifacts / (run["id"] + ".output.json")
                self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(),
                                 run["output_sha256"])
            holdout = verdict["holdout"][variant]
            self.assertEqual(holdout["points"], sum(holdout["case_points"].values()))
            output = artifacts / (variant + "-holdout.output.json")
            self.assertEqual(hashlib.sha256(output.read_bytes()).hexdigest(),
                             holdout["output_sha256"])

    def test_v1_5_publication_readback_is_explicit(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        compatibility = (ROOT / "docs" / "COMPATIBILITY.md").read_text(
            encoding="utf-8"
        )
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        pr_template = (ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md").read_text(
            encoding="utf-8"
        )
        release_notes = (ROOT / "RELEASE-NOTES.md").read_text(encoding="utf-8")
        candidate = (ROOT / "docs" / "releases" / "v1.5.0.md").read_text(
            encoding="utf-8"
        )
        publication = (
            ROOT / "docs" / "releases" / "v1.5.0-publication-readback.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Astra Ready Flow", readme)
        self.assertIn("model-neutral", readme)
        self.assertIn("WORKFLOW_READY", compatibility)
        self.assertIn("GPT-6 Astra", compatibility)
        self.assertIn("model policy", candidate.lower())
        self.assertIn(
            "Version [`v1.5.0`](docs/releases/v1.5.0-publication-readback.md) remains an",
            readme,
        )
        self.assertIn("pre-publication", readme)
        self.assertIn("`DISTRIBUTED` for `v1.5.0`", compatibility)
        self.assertIn("## v1.5.0 — 2026-09-02", release_notes)
        evidence = parse_release_evidence(publication)
        self.assertEqual("1.5.0", evidence["VERSION"])
        self.assertEqual("PUBLISHED_WITH_POST_RELEASE_METADATA_UPDATE", evidence["STATUS"])
        self.assertEqual("15", evidence["SKILL_COUNT"])
        self.assertEqual("WORKFLOW_READY_ONLY", evidence["MODEL_POSITIONING"])
        self.assertEqual("NOT_VERIFIED", evidence["MODEL_RUNTIME_PROOF"])
        self.assertEqual("109", evidence["DETERMINISTIC_TESTS_TOTAL"])
        self.assertEqual("PASS", evidence["DETERMINISTIC_TESTS_STATUS"])
        self.assertEqual("36", evidence["MERGE_PR"])
        self.assertEqual("MERGED", evidence["MERGE"])
        self.assertEqual(
            "1bd73efc68a8bd4f6b616456f6c308cc9938dd57",
            evidence["COMMIT_SHA"],
        )
        self.assertEqual("v1.5.0", evidence["TAG"])
        self.assertEqual(evidence["COMMIT_SHA"], evidence["TAG_COMMIT_SHA"])
        self.assertEqual("false", evidence["RELEASE_DRAFT"])
        self.assertEqual("false", evidence["RELEASE_PRERELEASE"])
        self.assertEqual("247", evidence["SOURCE_ARCHIVE_FILE_COUNT"])
        self.assertEqual("0", evidence["SOURCE_ARCHIVE_PYCACHE_COUNT"])
        self.assertEqual("15", evidence["SOURCE_ARCHIVE_SKILL_COUNT"])
        self.assertEqual("109/109 PASS", evidence["SOURCE_ARCHIVE_TESTS"])
        self.assertEqual("agents", evidence["INSTALL_CLIENT"])
        self.assertEqual("copy", evidence["INSTALL_MODE"])
        self.assertEqual("15", evidence["INSTALL_SKILL_COUNT"])
        self.assertEqual("PASS", evidence["INSTALL_FILE_MATCH"])
        self.assertEqual("PUBLISHED", evidence["DISTRIBUTION"])
        self.assertEqual(
            "PUBLISHED_WITH_POST_RELEASE_METADATA_UPDATE",
            evidence["ACCEPTANCE"],
        )
        for document in (publication, readme, compatibility, release_notes):
            for private_root in ("/" + "Users/", "/" + "Volumes/", "/" + "tmp/"):
                self.assertNotIn(private_root, document)
        for review_surface in (contributing, pr_template):
            self.assertIn("PUBLIC_SURFACE", review_surface)
            self.assertIn("README/docs/templates/assets/flow", review_surface)
            self.assertIn("workflow SVG and README Mermaid", review_surface)
        for term in (
            "COHERENCE_GATE: PASS",
            "README_COHERENCE_READBACK: PASS",
            "MERMAID_FLOW_READBACK: PASS",
            "SVG_FLOW_READBACK: PASS",
            "PUBLIC_SYNC: FETCH_ONLY",
            "MERGE: NOT_PERFORMED",
            "TAG: NOT_CREATED",
        ):
            self.assertIn(term, candidate)

    def test_v1_3_spec_self_authenticates(self) -> None:
        spec = (
            ROOT / "docs" / "specs" / "v1.3.0-harness-clarity.spec.md"
        ).read_bytes()
        declared = re.search(rb"^SPEC_HASH: ([0-9a-f]{64})$", spec, re.MULTILINE)
        approved = re.search(rb"^- APPROVED_HASH: ([0-9a-f]{64})$", spec, re.MULTILINE)
        self.assertIsNotNone(declared)
        self.assertIsNotNone(approved)

        canonical, spec_replacements = re.subn(
            rb"^SPEC_HASH: [^\r\n]+$",
            b"SPEC_HASH: NONE",
            spec,
            count=1,
            flags=re.MULTILINE,
        )
        canonical, approval_replacements = re.subn(
            rb"^- APPROVED_HASH: [^\r\n]+$",
            b"- APPROVED_HASH: NONE",
            canonical,
            count=1,
            flags=re.MULTILINE,
        )
        self.assertEqual(1, spec_replacements)
        self.assertEqual(1, approval_replacements)
        calculated = hashlib.sha256(canonical).hexdigest().encode("ascii")
        self.assertEqual(declared.group(1), approved.group(1))
        self.assertEqual(declared.group(1), calculated)

    def test_readme_branding_and_links(self) -> None:
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("nobrainer-tech-flow", text)
        self.assertIn("From task to done.", text)
        self.assertIn("https://github.com/nobrainer-tech/nobrainer-tech-flow", text)
        self.assertIn("https://nobrainer.tech/flow/", text)
        self.assertIn("docs/MIGRATION_TO_FLOW.md", text)
        self.assertIn("docs/NAMING.md", text)
        self.assertIn("nobrainer-tech-skills", text)
        self.assertIn("assets/nobrainer-tech-logo.svg", text)
        self.assertIn("https://nobrainer.tech", text)
        self.assertIn("https://nobrainertech.gumroad.com", text)
        self.assertIn("agentic workflows", text.lower())
        self.assertIn("assets/nobrainer-workflow.svg", text)
        self.assertNotIn("nobrainer-skills-coverage-v2.png", text)
        self.assertIn("docs/COMPATIBILITY.md", text)
        self.assertIn("docs/TESTING.md", text)

    def test_public_naming_map_separates_brand_aliases_and_technical_ids(self) -> None:
        naming = (ROOT / "docs" / "NAMING.md").read_text(encoding="utf-8")
        self.assertIn("nobrainer-tech-flow", naming)
        self.assertIn("nobrainer-tech-flow", naming)
        self.assertIn("nobrainer-ultra", naming)
        self.assertIn("Assistant conversation label", naming)
        self.assertIn("Workflow skills", naming)
        self.assertIn("`nobrainer-build`", naming)
        self.assertIn("Do not open with a ritual entry announcement", naming)
        self.assertIn("#NoBrainerTechFlow", naming)
        self.assertIn("A hyphen ends an X hashtag", naming)
        for alias in ("nb-ultra", "nb-flow", "nb-workflow"):
            self.assertIn(alias, naming)
        maintained_public = (
            ROOT / "README.md",
            ROOT / "AGENTS.md",
            ROOT / "CLAUDE.md",
            ROOT / "CONTRIBUTING.md",
            ROOT / "docs" / "INSTALL.md",
            ROOT / "docs" / "COMPATIBILITY.md",
            ROOT / "docs" / "MIGRATION_TO_FLOW.md",
            ROOT / "docs" / "TRY_IT.md",
            ROOT / "adapters" / "bootstrap.md",
        )
        for path in maintained_public:
            with self.subTest(path=path.relative_to(ROOT)):
                content = path.read_text(encoding="utf-8")
                self.assertNotIn("NoBrainer Tech Flow", content)
                self.assertNotIn("NoBrainer Ultra", content)
        codex = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertTrue(codex["interface"]["defaultPrompt"][0].startswith("Use `nobrainer-tech-flow`"))
        self.assertIn("$nobrainer-ultra", codex["interface"]["defaultPrompt"][0])
        self.assertIn("Do not announce workflow entry", codex["interface"]["defaultPrompt"][0])
        manifest_paths = (
            ROOT / "package.json",
            ROOT / "plugin.json",
            ROOT / "gemini-extension.json",
            ROOT / ".claude-plugin" / "plugin.json",
            ROOT / ".cursor-plugin" / "plugin.json",
            ROOT / ".kimi-plugin" / "plugin.json",
        )
        for path in manifest_paths:
            with self.subTest(manifest=path.relative_to(ROOT)):
                manifest = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("nobrainer-tech-flow", manifest["description"])
                self.assertNotIn("NoBrainer Tech Flow", manifest["description"])

    def test_install_snippets_require_one_literal_reviewed_commit(self) -> None:
        documents = (
            (ROOT / "README.md", "## Install safely"),
            (ROOT / "docs" / "INSTALL.md", "## Safe default"),
        )
        for path, heading in documents:
            with self.subTest(path=path.relative_to(ROOT)):
                section = path.read_text(encoding="utf-8").split(heading, 1)[1]
                match = re.search(r"```bash\n(.*?)```", section, re.DOTALL)
                self.assertIsNotNone(match)
                snippet = match.group(1)
                self.assertIn("NB_REVIEWED_COMMIT", snippet)
                self.assertNotIn("NB_REVIEWED_REF", snippet)
                self.assertIn('${#NB_REVIEWED_COMMIT}', snippet)
                self.assertIn('*[!0-9a-f]*', snippet)
                self.assertIn(
                    'test "$(git rev-parse HEAD)" = "$NB_REVIEWED_COMMIT"',
                    snippet,
                )
                self.assertIn("git clone --no-checkout", snippet)
                self.assertGreaterEqual(snippet.count("|| exit"), 8)

                for value in (None, "v1.2.0", "g" * 40, "a" * 39):
                    with self.subTest(value=value):
                        environment = dict(os.environ)
                        if value is None:
                            environment.pop("NB_REVIEWED_COMMIT", None)
                        else:
                            environment["NB_REVIEWED_COMMIT"] = value
                        with tempfile.TemporaryDirectory() as temp:
                            result = subprocess.run(
                                ["bash", "-c", snippet],
                                cwd=temp,
                                env=environment,
                                text=True,
                                capture_output=True,
                                check=False,
                            )
                            self.assertNotEqual(0, result.returncode)
                            self.assertFalse(
                                (Path(temp) / "nobrainer-tech-flow").exists()
                            )

    def test_coverage_graphic_is_readme_ready(self) -> None:
        path = ROOT / "assets" / "nobrainer-workflow.svg"
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.startswith("<svg"))
        self.assertIn('viewBox="0 0 1600 900"', text)
        self.assertIn("BUDDY", text)
        self.assertIn("QUICK PATH", text)
        self.assertIn("Small + reversible", text)
        self.assertIn("RISK → OWNER GATE", text)
        self.assertIn("model policy", text.lower())
        self.assertIn("SCOPE + PLAN", text)
        self.assertIn("BUILD", text)
        self.assertIn("REVIEW", text)
        self.assertIn("LEARN", text)
        self.assertIn("review-fix-loop", text)
        self.assertLessEqual(len(text.encode("utf-8")), 200_000)
        self.assertFalse((ROOT / "assets" / "nobrainer-skills-coverage-v2.png").exists())
        self.assertFalse((ROOT / "assets" / "nobrainer-skills-coverage.webp").exists())

    def test_product_repository_surface(self) -> None:
        required = (
            ".gitattributes",
            "CONTRIBUTING.md",
            "RELEASE-NOTES.md",
            "SECURITY.md",
            "docs/COMPATIBILITY.md",
            "docs/releases/v1.0.0.md",
            "docs/releases/v1.1.0.md",
            "docs/releases/v1.3.0.md",
            "docs/releases/v1.3.1.md",
            "docs/releases/v1.3.1-publication-readback.md",
            "docs/releases/v1.4.0-publication-readback.md",
            "docs/releases/v1.5.0.md",
            "docs/releases/v1.5.0-publication-readback.md",
            "skills/nobrainer-ultra/references/model-routing.md",
            "docs/evals/v1.3.1-writing-brief-2026-09-02.md",
            "docs/evals/artifacts/v1.3.1-writing-brief-holdout-prompt.md",
            "docs/evals/artifacts/v1.3.1-writing-brief-holdout-output.md",
            "docs/evals/artifacts/v1.3.1-writing-brief-holdout-output.raw.b64",
            "docs/evals/artifacts/v1.3.1-writing-brief-holdout-judge-prompt.md",
            "docs/evals/artifacts/v1.3.1-writing-brief-holdout-judge.md",
            "docs/evals/artifacts/v1.3.1-writing-brief-holdout-judge.raw.md",
            "docs/TESTING.md",
            "docs/SKILL_CURATION.md",
            "docs/evals/core-routing-v1.1.0-2026-08-28.md",
            "docs/evals/dispatcher-routing-v1.2.0-2026-08-28.md",
            "docs/evals/writing-density-v1.2.0-2026-08-28.md",
            "docs/evals/v1.3.0-harness-clarity-2026-08-30.md",
            "docs/specs/v1.3.0-harness-clarity.spec.md",
            "assets/nobrainer-workflow.svg",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/ISSUE_TEMPLATE/bug_report.md",
            ".github/ISSUE_TEMPLATE/feature_request.md",
            ".github/ISSUE_TEMPLATE/config.yml",
            ".github/dependabot.yml",
            ".github/workflows/validate.yml",
        )
        for relative in required:
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file())

        workflow = (ROOT / ".github" / "workflows" / "validate.yml").read_text(
            encoding="utf-8"
        )
        for term in (
            "scripts/validate_skills.py --suite",
            "unittest discover",
            "py_compile",
            "GITLEAKS_VERSION: 8.30.1",
            "GITLEAKS_SHA256:",
            "--config .gitleaks.toml --redact --no-banner --ignore-gitleaks-allow",
            "timeout-minutes:",
            "persist-credentials: false",
        ):
            self.assertIn(term, workflow)
        uses_lines = [
            line for line in workflow.splitlines() if line.lstrip().startswith("uses:")
        ]
        self.assertGreater(len(uses_lines), 0)
        for line in uses_lines:
            self.assertRegex(
                line,
                r"^\s*uses:\s+[^\s@]+@[0-9a-f]{40}(?:\s+#.*)?$",
                line,
            )
        self.assertIn("echo \"$RUNNER_TEMP\" >> \"$GITHUB_PATH\"", workflow)
        self.assertIn("bash -n hooks/session-start\n          bash -n hooks/run-hook.cmd", workflow)
        self.assertIn("cmp -s AGENTS.md CLAUDE.md", workflow)

    def test_readme_has_github_rendered_workflow_chart(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("```mermaid", readme)
        self.assertIn("flowchart TD", readme)
        for term in (
            "Material ambiguity?",
            "BUDDY: one focused question round",
            "Direct answer or edit; check the result",
            "SCOPE + PLAN: outcome, authority, proof; concise TODO",
            "AUTOPILOT: execute the authorized scope",
            "Verify; independent REVIEW when useful",
            "attempt budget remains",
            "Audit delegated artifacts and stop owned workers",
            "Markdown goal for resume",
            "Fresh session: same task + started DD-MM",
            "Bounded native subagents",
            "Deliver evidence and stop",
        ):
            self.assertIn(term, readme)

    def test_session_restart_titles_are_human_labels_not_identity(self) -> None:
        restart = (
            ROOT / "skills/nobrainer-sessions/references/session-restart.md"
        ).read_text(encoding="utf-8")
        protocol = (
            ROOT / "skills/nobrainer-sessions/references/protocol.md"
        ).read_text(encoding="utf-8")
        public_doc = (ROOT / "docs/SESSION_RESTART.md").read_text(encoding="utf-8")
        for text in (restart, protocol, public_doc):
            self.assertIn("started DD-MM", text)
            self.assertIn("timezone", text.lower())
        restart_words = " ".join(restart.split())
        protocol_words = " ".join(protocol.split())
        public_words = " ".join(public_doc.split())
        self.assertIn("title can collide and is never identity evidence", restart_words)
        self.assertIn("never use a title to establish identity", protocol_words)
        self.assertIn("Session IDs, goal identity and checkpoint digest remain authoritative", public_words)
        self.assertIn("Strip an existing ` | started DD-MM` suffix", restart)
        self.assertIn("TITLE_STATUS: VERIFIED | UNAVAILABLE | UNSUPPORTED | UNKNOWN", protocol)

    def test_manifest_versions_are_consistent(self) -> None:
        versions = {
            relative: json.loads(
                (ROOT / relative).read_text(encoding="utf-8")
            )["version"]
            for relative in VERSION_MANIFESTS
        }
        marketplace = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        versions[".claude-plugin/marketplace.json"] = marketplace["plugins"][0][
            "version"
        ]
        unique = set(versions.values())
        self.assertEqual(1, len(unique), versions)
        self.assertRegex(
            next(iter(unique)),
            r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?$",
        )

        codex = json.loads(
            (ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertNotIn("hooks", codex)
        self.assertFalse((ROOT / "hooks" / "hooks.json").exists())
        self.assertEqual("./skills/", codex["skills"])
        claude = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual("./hooks/claude-hooks.json", claude["hooks"])
        interface = codex["interface"]
        self.assertIn("concise progress", interface["longDescription"])
        self.assertNotIn("execution map", interface["longDescription"].lower())
        self.assertTrue(interface["defaultPrompt"][0].startswith("Use `nobrainer-tech-flow`"))
        self.assertIn("$nobrainer-ultra", interface["defaultPrompt"][0])
        self.assertIn("Do not announce workflow entry", interface["defaultPrompt"][0])
        self.assertNotIn("Use nb-ultra", interface["defaultPrompt"])
        self.assertEqual("./assets/nobrainer-tech-logo.svg", interface["composerIcon"])
        self.assertEqual(
            "https://nobrainer.tech/privacy", interface["privacyPolicyURL"]
        )
        self.assertEqual(
            "https://nobrainer.tech/terms", interface["termsOfServiceURL"]
        )

    def test_review_has_one_evidence_gated_owner(self) -> None:
        directory = SKILLS / "nobrainer-review"
        text = (directory / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual({"SKILL.md"}, {path.name for path in directory.iterdir()})
        for term in (
            "CLOSEOUT",
            "BUG_HUNT",
            "RELEASE_GATE",
            "Finding gate",
            "reachable input/state/sequence",
            "PARTIAL",
            "Pre-read predictions",
            "NAME_PATH_AUDIT",
            "HIT",
            "MISS",
            "UNTESTED",
        ):
            self.assertIn(term, text)
        self.assertIn("filter out speculative AI noise", text)
        self.assertIn("nobrainer-build", text)
        self.assertNotIn("asks for a code or change review", text)
        self.assertNotIn("continue until dry", text.lower())
        self.assertIn("green test does not replace", text)

    def test_opencode_guide_has_no_stale_package_pin(self) -> None:
        text = (ROOT / ".opencode" / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("NB_REVIEWED_COMMIT_SHA", text)
        self.assertNotIn(
            "881bcafad8d1a7c2708b80186ef33400ac67f343",
            text,
        )

    def test_wiki_modes_have_one_owner(self) -> None:
        text = (SKILLS / "nobrainer-wiki" / "SKILL.md").read_text(encoding="utf-8")
        setup = (
            SKILLS / "nobrainer-wiki" / "references" / "setup.md"
        ).read_text(encoding="utf-8")
        for mode in ("SETUP", "GET", "ADD", "TIDY_AUDIT", "TIDY_APPLY"):
            self.assertIn(mode, text)
        self.assertIn("One skill owns all wiki behavior", text)
        self.assertIn("TIDY_AUDIT", setup)
        for retired in (
            "nobrainer-wiki-add",
            "nobrainer-wiki-get",
            "nobrainer-wiki-tidy",
        ):
            self.assertFalse((SKILLS / retired / "SKILL.md").exists())

    def test_repository_validator(self) -> None:
        result = subprocess.run(
            ["python3", "scripts/validate_skills.py", "--suite"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    @unittest.skipIf(
        os.environ.get("NOBRAINER_ARCHIVE_ACCEPTANCE_CHILD") == "1",
        "avoid recursively spawning the archive acceptance suite",
    )
    def test_full_acceptance_suite_passes_without_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "source"
            shutil.copytree(
                ROOT,
                archive,
                symlinks=True,
                ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
            )
            self.assertFalse((archive / ".git").exists())
            environment = os.environ.copy()
            environment["NOBRAINER_ARCHIVE_ACCEPTANCE_CHILD"] = "1"
            validator = subprocess.run(
                ["python3", "scripts/validate_skills.py", "--suite"],
                cwd=archive,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                0,
                validator.returncode,
                validator.stdout + validator.stderr,
            )
            suite = subprocess.run(
                ["python3", "-m", "unittest", "discover", "-s", "tests", "-q"],
                cwd=archive,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(0, suite.returncode, suite.stdout + suite.stderr)

    def test_frozen_eval_payloads_do_not_impersonate_repository_links(self) -> None:
        artifact_dir = ROOT / "docs" / "evals" / "artifacts"
        prompt = artifact_dir / "v1.2.0-routing-final-verified-holdout-prompt.md"
        run = artifact_dir / "v1.2.0-routing-final-verified-holdout-run.md"
        record = ROOT / "docs" / "evals" / "dispatcher-routing-v1.2.0-2026-08-28.md"
        self.assertFalse(validate_skills.should_validate_relative_links(prompt))
        self.assertTrue(validate_skills.should_validate_relative_links(run))
        self.assertTrue(validate_skills.should_validate_relative_links(record))
        self.assertTrue(
            validate_skills.relative_link_errors(prompt, "[literal](missing.md)")
        )

        attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        self.assertNotIn("docs/evals/artifacts/** -whitespace", attributes)
        for line in attributes.splitlines():
            if line.startswith("docs/evals/artifacts/"):
                self.assertTrue(line.endswith("-text -whitespace"), line)
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            prompt_probe = prompt.relative_to(ROOT)
            run_probe = run.relative_to(ROOT)
            for relative in (prompt_probe, run_probe):
                destination = repo / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((ROOT / relative).read_bytes())
            copied_attributes = 0
            for source in ROOT.rglob(".gitattributes"):
                relative = source.relative_to(ROOT)
                if ".git" in relative.parts:
                    continue
                destination = repo / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
                copied_attributes += 1
            self.assertGreaterEqual(copied_attributes, 1)
            self.assertEqual(attributes, (repo / ".gitattributes").read_text())
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            checked = subprocess.run(
                [
                    "git",
                    "check-attr",
                    "text",
                    "whitespace",
                    "--",
                    str(prompt_probe),
                    str(run_probe),
                ],
                cwd=repo,
                text=True,
                capture_output=True,
                check=True,
            ).stdout
        self.assertIn(f"{prompt_probe}: text: unset", checked)
        self.assertIn(f"{prompt_probe}: whitespace: unset", checked)
        self.assertIn(f"{run_probe}: text: unspecified", checked)
        self.assertIn(f"{run_probe}: whitespace: unspecified", checked)

    def test_frozen_eval_payloads_are_byte_stable_under_autocrlf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            payloads = {
                "docs/evals/artifacts/example-prompt.md": (
                    b"prompt CRLF with spaces  \r\nprompt LF\nprompt CRLF\r\n"
                ),
                "docs/evals/artifacts/example-output.md": (
                    b"output LF with spaces  \noutput CRLF\r\noutput LF\n"
                ),
                "docs/evals/artifacts/example-judge.md": (
                    b"judge CRLF\r\njudge LF with spaces  \njudge CRLF\r\n"
                ),
                "docs/evals/artifacts/example-judge-rubric.md": (
                    b"rubric LF\nrubric CRLF with spaces  \r\nrubric LF\n"
                ),
                "docs/evals/artifacts/example.raw.b64": (
                    b"cHJvbXB0DQo=\r\nb3V0cHV0Cg==\n"
                ),
            }
            for relative, original in payloads.items():
                payload = repo / relative
                payload.parent.mkdir(parents=True, exist_ok=True)
                payload.write_bytes(original)
            (repo / ".gitattributes").write_bytes(
                (ROOT / ".gitattributes").read_bytes()
            )
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                [
                    "git",
                    "-c",
                    "core.autocrlf=true",
                    "add",
                    ".gitattributes",
                    *payloads,
                ],
                cwd=repo,
                check=True,
            )
            for relative, original in payloads.items():
                with self.subTest(relative=relative, phase="index"):
                    stored = subprocess.run(
                        ["git", "show", f":{relative}"],
                        cwd=repo,
                        capture_output=True,
                        check=True,
                    ).stdout
                    self.assertEqual(original, stored)
                    (repo / relative).unlink()
            subprocess.run(
                [
                    "git",
                    "-c",
                    "core.autocrlf=true",
                    "-c",
                    "core.eol=crlf",
                    "checkout",
                    "--",
                    *payloads,
                ],
                cwd=repo,
                check=True,
            )
            for relative, original in payloads.items():
                with self.subTest(relative=relative, phase="checkout"):
                    self.assertEqual(original, (repo / relative).read_bytes())

    def test_openai_codex_inspirations_keep_portable_boundaries(self) -> None:
        sessions = (SKILLS / "nobrainer-sessions/references/session-restart.md").read_text()
        review = (SKILLS / "nobrainer-review/SKILL.md").read_text()
        build = (SKILLS / "nobrainer-build/SKILL.md").read_text()
        writing = (SKILLS / "nobrainer-writing/SKILL.md").read_text()
        source_map = (ROOT / "docs/reviews/2026-09-05-openai-codex-skills.md").read_text()

        for required in ("finite bound", "stable order and byte form", "remain `UNKNOWN`"):
            self.assertIn(required, sessions)
        for required in (
            "exact PR head SHA",
            "pending draft reviews are not published feedback",
            "finite recorded budget",
            "not\nmerge authorization",
            "Do not automatically run every",
        ):
            self.assertIn(required, review)
        self.assertIn("evidence from a replaced head is\n   stale", build)
        self.assertIn("lead with why", writing)
        self.assertIn("net\n  change against the actual PR base", writing)
        self.assertIn("5d358057152d5e2950f20a25cb6cf050ed5b5d85", source_map)
        self.assertIn("does not\nadd a watcher daemon, require GitHub", source_map)

    def test_public_text_scan_ignores_unknown_extensionless_binary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / ".DS_Store"
            binary.write_bytes(b"\x00\xff\x00\xff")
            self.assertFalse(validate_skills.is_public_text_file(binary))

        for helper in validate_skills.PUBLIC_EXTENSIONLESS_FILES:
            with self.subTest(helper=helper):
                self.assertTrue(validate_skills.is_public_text_file(helper))


if __name__ == "__main__":
    unittest.main()
