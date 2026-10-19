from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD = ROOT / "skills" / "nobrainer-tech-flow" / "scripts" / "flow_guard.py"
PRIVATE_TMP = "/private/tmp"

# (command, asks). The guard reads command text, so a risky phrase in a string asks
# too: echo "git reset --hard" is the documented false positive.
COMMANDS = (
    ("rm -rf build", True),
    ("rm -r -f ./dist", True),
    ("rm -R ~/notes", True),
    ("rm --recursive /var/data", True),
    ("rm -rf /tmp/../etc", True),
    ("rm -rf /tmp", True),
    ('rm -rf "$HOME/project"', True),
    ("find . -name cache -exec rm -rf {} \\;", True),
    ("ls && rm -rf src", True),
    ("rm -rf /tmp/flow-build", False),
    (f"rm -rf {PRIVATE_TMP}/flow-build", False),
    ("rm -rf /var/folders/ab/T/flow", False),
    ('rm -rf "$TMPDIR/flow"', False),
    ("rm -rf ${TMPDIR}/flow", False),
    ("rm -f notes.txt", False),
    ("git rm -r old", False),
    ("/bin/rm -rf src", True),
    ("/usr/bin/rm -r build", True),
    ("/usr/bin/git rm -r old", False),
    ("git push --force", True),
    ("git push -f origin main", True),
    ("git push origin main --force-with-lease", True),
    ("git push -u origin main", False),
    ("git push origin --follow-tags", False),
    ("git -C dir push --force", True),
    ("git -c core.askPass=x push -f origin main", True),
    ("git push --force-with-lease=main:abc123", True),
    ("git push origin +main", True),
    ("git push origin feature+fix", False),
    ('git commit -m "push +1 retry"', False),
    ("git reset --hard HEAD~1", True),
    ("git -C repo reset --hard", True),
    ("git reset --soft HEAD~1", False),
    ('echo "git reset --hard"', True),
    ("git clean -fd", True),
    ("git clean -fdx", True),
    ("git clean -n", False),
    ("vercel --prod", True),
    ("vercel deploy --prod --yes", True),
    ("vercel deploy", False),
    ("npm publish", True),
    ("npm run publish-docs", False),
    ("npm --registry=https://registry.npmjs.org publish --dry-run", True),
    ("npm -w pkg publish", True),
    ("npm --workspace pkg publish --access public", True),
    ("npm run publish", False),
    ("npm install publish-it", False),
    ("terraform apply -auto-approve", True),
    ("terraform -chdir=infra destroy", True),
    ("terraform -chdir=infra apply", True),
    ("terraform plan", False),
    ("kubectl delete pod web-1", True),
    ("kubectl -n prod delete deployment web", True),
    ("kubectl --context staging delete pod web-1", True),
    ("kubectl get pods", False),
    ("gh release create v2.4.0", True),
    ("gh -R owner/repo release create v2.4.0", True),
    ("gh --repo owner/repo release create v2.4.0", True),
    ("gh release view v2.4.0", False),
    ("gh issue create --title release", False),
    ("git status; git log --oneline -3", False),
)


def run_guard(mode: str, stdin: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    environment.update(env or {})
    return subprocess.run(
        [sys.executable, str(GUARD), mode],
        input=stdin,
        text=True,
        capture_output=True,
        check=False,
        env=environment,
    )


def assistant(*blocks: dict) -> dict:
    return {"type": "assistant", "message": {"role": "assistant", "content": list(blocks)}}


def text(value: str) -> dict:
    return {"type": "text", "text": value}


def tool(name: str) -> dict:
    return {"type": "tool_use", "id": f"toolu_{name}", "name": name, "input": {}}


def prompt(value: str) -> dict:
    return {"type": "user", "message": {"role": "user", "content": value}}


def result() -> dict:
    return {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_x", "content": "ok"}]},
    }


class PreToolTests(unittest.TestCase):
    def decide(self, command: str, tool_name: str = "Bash") -> dict | None:
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": tool_name,
            "tool_input": {"command": command},
            "cwd": "/home/dev/project",
        }
        completed = run_guard("pre-tool", json.dumps(payload), {"TMPDIR": "/var/folders/zz/T/"})
        self.assertEqual(0, completed.returncode, completed.stderr)
        return json.loads(completed.stdout) if completed.stdout.strip() else None

    def test_command_table(self) -> None:
        for command, asks in COMMANDS:
            with self.subTest(command=command):
                output = self.decide(command)
                if not asks:
                    self.assertIsNone(output)
                    continue
                self.assertIsNotNone(output)
                decision = output["hookSpecificOutput"]
                self.assertEqual("PreToolUse", decision["hookEventName"])
                self.assertEqual("ask", decision["permissionDecision"])
                self.assertIn("Flow guard", decision["permissionDecisionReason"])

    def test_never_denies_and_ignores_other_tools(self) -> None:
        for command, _ in COMMANDS:
            output = self.decide(command)
            if output:
                self.assertNotEqual("deny", output["hookSpecificOutput"]["permissionDecision"])
        self.assertIsNone(self.decide("git reset --hard", tool_name="Write"))

    def test_relative_paths_inside_a_temporary_cwd_pass(self) -> None:
        payload = {"tool_name": "Bash", "tool_input": {"command": "rm -rf build"}, "cwd": "/tmp/work"}
        completed = run_guard("pre-tool", json.dumps(payload))
        self.assertEqual("", completed.stdout)

    def test_a_directory_change_before_rm_drops_the_temporary_cwd_exemption(self) -> None:
        for command, asks in (
            ("cd /home/dev/project && rm -rf src", True),
            ("pushd /home/dev; rm -rf src", True),
            ("(cd ../.. && rm -rf build)", True),
            ("cd /tmp/work/sub && rm -rf /tmp/work/sub/build", False),
            ("rm -rf build && cd /home/dev", False),
        ):
            with self.subTest(command=command):
                payload = {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": "/tmp/work"}
                completed = run_guard("pre-tool", json.dumps(payload))
                self.assertEqual(asks, bool(completed.stdout.strip()), completed.stdout)

    def test_unreadable_input_is_allowed_with_a_note(self) -> None:
        for stdin in ("not json", "[1, 2]", ""):
            with self.subTest(stdin=stdin):
                completed = run_guard("pre-tool", stdin)
                self.assertEqual(0, completed.returncode)
                self.assertEqual("", completed.stdout)
                self.assertIn("flow_guard:", completed.stderr)


class StopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)

    def transcript(self, *entries: dict, raw: str = "") -> str:
        path = Path(self.scratch.name) / "session.jsonl"
        path.write_text("".join(json.dumps(entry) + "\n" for entry in entries) + raw, encoding="utf-8")
        return str(path)

    def stop(self, payload: dict) -> subprocess.CompletedProcess[str]:
        completed = run_guard("stop", json.dumps(payload))
        self.assertEqual(0, completed.returncode, completed.stderr)
        return completed

    def payload(self, transcript: str, final: str | None, **extra: object) -> dict:
        payload: dict = {"hook_event_name": "Stop", "transcript_path": transcript, "stop_hook_active": False}
        if final is not None:
            payload["last_assistant_message"] = final
        payload.update(extra)
        return payload

    def edited(self, final: str) -> str:
        return self.transcript(
            prompt("fix the bug"), assistant(tool("Edit")), result(), assistant(tool("Bash")), result(), assistant(text(final))
        )

    def test_edit_turn_without_proof_is_blocked_once(self) -> None:
        final = "Fixed the parser."
        completed = self.stop(self.payload(self.edited(final), final))
        output = json.loads(completed.stdout)
        self.assertEqual("block", output["decision"])
        self.assertIn("Proof:", output["reason"])
        self.assertIn("UNVERIFIED", output["reason"])

    def test_proof_line_or_unverified_allows(self) -> None:
        for final in (
            "Fixed the parser.\nProof: python3 -m unittest tests.test_parser passed (12 tests).",
            "Done.\n- **Checked:** readback of config.json shows the new key.",
            "Done.\n**Proof**: python3 -m unittest passed.",
            "Done.\n1. Proof: the smoke run printed OK.",
            "Changed the parser. UNVERIFIED: no test covers this path.",
        ):
            with self.subTest(final=final):
                self.assertEqual("", self.stop(self.payload(self.edited(final), final)).stdout)

    def test_stop_hook_active_never_blocks_twice(self) -> None:
        final = "Fixed the parser."
        self.assertEqual("", self.stop(self.payload(self.edited(final), final, stop_hook_active=True)).stdout)

    def test_read_only_turn_is_allowed(self) -> None:
        # The earlier turn edited; only the last turn counts, and it only read.
        transcript = self.transcript(
            prompt("fix it"), assistant(tool("Write")), result(), assistant(text("Written.")),
            prompt("what does it do?"), assistant(tool("Read")), result(), assistant(text("It parses dates.")),
        )
        self.assertEqual("", self.stop(self.payload(transcript, "It parses dates.")).stdout)

    def test_final_text_falls_back_to_the_transcript(self) -> None:
        blocked = self.stop(self.payload(self.edited("Fixed."), None))
        self.assertEqual("block", json.loads(blocked.stdout)["decision"])
        allowed = self.stop(self.payload(self.edited("Fixed.\nProof: tests pass."), None))
        self.assertEqual("", allowed.stdout)

    def test_subagent_stop_reads_its_own_transcript(self) -> None:
        main = self.transcript(prompt("delegate"), assistant(text("Asked a worker.")))
        agent = Path(self.scratch.name) / "agent.jsonl"
        agent.write_text(
            "".join(json.dumps(entry) + "\n" for entry in (prompt("edit"), assistant(tool("Edit")), result(), assistant(text("Edited.")))),
            encoding="utf-8",
        )
        payload = self.payload(main, "Edited.", hook_event_name="SubagentStop", agent_transcript_path=str(agent))
        self.assertEqual("block", json.loads(self.stop(payload).stdout)["decision"])

    def test_malformed_input_or_transcript_is_allowed_with_a_note(self) -> None:
        cases = (
            "not json",
            json.dumps({"hook_event_name": "Stop"}),
            json.dumps(self.payload(str(Path(self.scratch.name) / "missing.jsonl"), "Fixed.")),
            json.dumps(self.payload(self.transcript(raw="{broken\n"), "Fixed.")),
        )
        for stdin in cases:
            with self.subTest(stdin=stdin[:40]):
                completed = run_guard("stop", stdin)
                self.assertEqual(0, completed.returncode)
                self.assertEqual("", completed.stdout)
                self.assertIn("flow_guard:", completed.stderr)

    def test_a_partial_last_line_does_not_hide_the_turn(self) -> None:
        transcript = self.transcript(prompt("fix"), assistant(tool("Edit")), result(), raw='{"type": "assist')
        self.assertEqual("block", json.loads(self.stop(self.payload(transcript, "Fixed.")).stdout)["decision"])


class UsageTests(unittest.TestCase):
    def test_an_unknown_mode_is_a_usage_error(self) -> None:
        completed = run_guard("deny", "{}")
        self.assertEqual(1, completed.returncode)
        self.assertIn("usage", completed.stderr)


if __name__ == "__main__":
    unittest.main()
