from __future__ import annotations

import json
import os
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_MARKER = "NOBRAINER_BOOTSTRAP_V1"
CANONICAL_SKILLS = {
    "nobrainer-codex-context",
    "nobrainer-skill-doctor",
    "nobrainer-autoimprove",
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
    "nobrainer-ultra",
    "nobrainer-wiki",
}


class AdapterTests(unittest.TestCase):
    def test_shared_bootstrap_is_small_scoped_and_portable(self) -> None:
        path = ROOT / "adapters" / "bootstrap.md"
        text = path.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        self.assertIn(BOOTSTRAP_MARKER, text)
        self.assertIn("nobrainer-ultra", text)
        self.assertIn("correction", text.lower())
        self.assertIn("simple", text.lower())
        self.assertIn("owner gate", text.lower())
        for contract in (
            "literal failure, local evidence and smallest reproducer",
            "Query useful wiki decisions",
            "Use current internet research when the remedy depends",
            "RESEARCH_BLOCKED",
            "choose no remedy dependent",
            "one primary agent",
            "short Progress checklist",
            "detailed ledger only",
            "supersedes the old requirement",
            "invalidates affected TODO and evidence",
            "Failed review returns to Build",
            "invalidates stale proof",
            "No mode authorizes global instructions",
        ):
            self.assertIn(contract, normalized)
        self.assertLessEqual(len(text.split()), 190)
        self.assertNotIn("/" + "Users" + "/", text)
        self.assertNotIn("continue until done", text.lower())

    def test_all_problem_gate_entrypoints_calibrate_local_and_web_evidence(self) -> None:
        paths = (
            ROOT / "adapters" / "bootstrap.md",
            ROOT / "skills" / "nobrainer-ultra" / "references" / "setup.md",
            ROOT / ".github" / "copilot-instructions.md",
        )
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT)):
                normalized = " ".join(path.read_text(encoding="utf-8").split())
                self.assertIn("RESEARCH_BLOCKED", normalized)
                self.assertIn("choose no remedy", normalized)
                self.assertIn("internet research", normalized)
                self.assertIn("local", normalized.lower())

    def test_session_start_hook_emits_one_platform_specific_context(self) -> None:
        hook = ROOT / "hooks" / "session-start"
        claude_hook_path = ROOT / "hooks" / "claude-hooks.json"
        claude_hooks = json.loads(claude_hook_path.read_text())
        cursor_hooks = json.loads(
            (ROOT / "hooks" / "hooks-cursor.json").read_text()
        )
        claude_manifest = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text()
        )
        self.assertEqual("./hooks/claude-hooks.json", claude_manifest["hooks"])
        self.assertFalse((ROOT / "hooks" / "hooks.json").exists())
        claude_entry = claude_hooks["hooks"]["SessionStart"][0]
        cursor_entry = cursor_hooks["hooks"]["sessionStart"][0]
        self.assertEqual("startup|resume|clear|compact|fork", claude_entry["matcher"])
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", claude_entry["hooks"][0]["command"])
        self.assertEqual(
            '"${CURSOR_PLUGIN_ROOT}/hooks/run-hook.cmd" session-start',
            cursor_entry["command"],
        )
        cases = (
            ({"CLAUDE_PLUGIN_ROOT": str(ROOT)}, "hookSpecificOutput"),
            (
                {
                    "CLAUDE_PLUGIN_ROOT": str(ROOT),
                    "CURSOR_PLUGIN_ROOT": str(ROOT),
                },
                "additional_context",
            ),
        )
        for extra_env, expected_key in cases:
            with self.subTest(expected_key=expected_key):
                result = subprocess.run(
                    ["bash", str(hook)],
                    cwd=ROOT,
                    env={"PATH": os.environ.get("PATH", ""), **extra_env},
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(0, result.returncode, result.stderr)
                payload = json.loads(result.stdout)
                if expected_key == "hookSpecificOutput":
                    self.assertEqual({"hookSpecificOutput"}, set(payload))
                    context = payload[expected_key]["additionalContext"]
                    self.assertEqual(
                        "SessionStart", payload[expected_key]["hookEventName"]
                    )
                else:
                    self.assertEqual({expected_key}, set(payload))
                    context = payload[expected_key]
                self.assertIn(BOOTSTRAP_MARKER, context)
                self.assertIn("nobrainer-ultra", context)
                self.assertLess(len(context), 2_000)

    def test_opencode_registers_skills_and_injects_bootstrap_once(self) -> None:
        script = r"""
import plugin from './.opencode/plugins/nobrainer-tech-skills.js';
const instance = await plugin();
const config = {};
await instance.config(config);
await instance.config(config);
if (config.skills.paths.length !== 1 || !config.skills.paths[0].endsWith('/skills')) process.exit(2);
const output = {messages: [{info: {role: 'user'}, parts: [{id: 'part-1', type: 'text', text: 'hello'}]}]};
await instance['experimental.chat.messages.transform']({}, output);
await instance['experimental.chat.messages.transform']({}, output);
const parts = output.messages[0].parts;
const combined = parts.map(part => part.text || '').join('\n');
const count = combined.split('NOBRAINER_BOOTSTRAP_V1').length - 1;
if (parts.length !== 1 || parts[0].id !== 'part-1') process.exit(3);
if (count !== 1 || !combined.includes('nobrainer-ultra') || !combined.endsWith('\n\nhello')) process.exit(4);
"""
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_portable_gemini_and_kimi_manifests_bind_the_canonical_source(self) -> None:
        canonical_version = json.loads(
            (ROOT / "package.json").read_text(encoding="utf-8")
        )["version"]
        portable = json.loads((ROOT / "plugin.json").read_text())
        gemini = json.loads((ROOT / "gemini-extension.json").read_text())
        kimi = json.loads((ROOT / ".kimi-plugin" / "plugin.json").read_text())
        for manifest in (portable, gemini, kimi):
            self.assertEqual("nobrainer-tech-skills", manifest["name"])
            self.assertEqual(canonical_version, manifest["version"])
        self.assertEqual(
            "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
            portable["$schema"],
        )
        self.assertEqual("GEMINI.md", gemini["contextFileName"])
        self.assertEqual("./skills/", kimi["skills"])
        self.assertEqual("nobrainer-ultra", kimi["sessionStart"]["skill"])
        self.assertIn("visible sessions", kimi["skillInstructions"])
        self.assertNotIn("repository", kimi)
        self.assertNotIn("capabilities", kimi["interface"])
        self.assertEqual(
            CANONICAL_SKILLS,
            {path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")},
        )
        self.assertFalse((ROOT / ".devin-plugin" / "plugin.json").exists())
        self.assertFalse((ROOT / ".hermes-plugin" / "plugin.yaml").exists())
        self.assertEqual(
            "@./adapters/bootstrap.md\n",
            (ROOT / "GEMINI.md").read_text(encoding="utf-8"),
        )

    def test_pi_extension_registers_skills_and_reinjects_per_prompt(self) -> None:
        script = r"""
import plugin from './.pi/extensions/nobrainer-tech-skills.js';
const handlers = new Map();
plugin({on: (name, handler) => handlers.set(name, handler)});
for (const name of ['resources_discover', 'session_start', 'session_compact', 'context']) {
  if (!handlers.has(name)) process.exit(2);
}
const resources = await handlers.get('resources_discover')();
if (resources.skillPaths.length !== 1 || !resources.skillPaths[0].endsWith('/skills')) process.exit(3);
await handlers.get('session_start')();
let result = await handlers.get('context')({messages: [{role: 'user', content: 'hello'}]});
let text = result.messages.flatMap(m => Array.isArray(m.content) ? m.content.map(p => p.text || '') : [m.content || '']).join('\n');
if (!text.includes('NOBRAINER_BOOTSTRAP_V1')) process.exit(4);
const second = await handlers.get('context')({messages: result.messages});
if (second !== undefined) process.exit(5);
text = result.messages.flatMap(m => Array.isArray(m.content) ? m.content.map(p => p.text || '') : [m.content || '']).join('\n');
if (text.split('NOBRAINER_BOOTSTRAP_V1').length - 1 !== 1) process.exit(6);
result = await handlers.get('context')({messages: [{role: 'user', content: 'next prompt'}]});
text = result.messages.flatMap(m => Array.isArray(m.content) ? m.content.map(p => p.text || '') : [m.content || '']).join('\n');
if (!text.includes('NOBRAINER_BOOTSTRAP_V1')) process.exit(7);
if (text.split('NOBRAINER_BOOTSTRAP_V1').length - 1 !== 1) process.exit(8);
await handlers.get('session_compact')();
result = await handlers.get('context')({messages: [{role: 'compactionSummary', content: 'summary'}, {role: 'user', content: 'next'}]});
text = result.messages.flatMap(m => Array.isArray(m.content) ? m.content.map(p => p.text || '') : [m.content || '']).join('\n');
if (!text.includes('NOBRAINER_BOOTSTRAP_V1')) process.exit(7);
if (text.split('NOBRAINER_BOOTSTRAP_V1').length - 1 !== 1) process.exit(10);
"""
        result = subprocess.run(
            ["node", "--input-type=module", "-e", script],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

if __name__ == "__main__":
    unittest.main()
