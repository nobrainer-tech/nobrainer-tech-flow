from __future__ import annotations

import datetime as dt
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/nobrainer-auto-fine-tune/scripts/benchmark_routing.py"
FIXTURE = ROOT / "tests/fixtures/routing-setup-openai-anthropic.f0.b0.json"
SPEC = importlib.util.spec_from_file_location("benchmark_routing", SCRIPT)
routing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routing)

KEY = "openai-anthropic.f0.b0"
NOW = dt.datetime(2026, 9, 30, 12, 0, tzinfo=dt.timezone.utc)
MANIFEST_URL = routing.BASE_URL + "manifest.json"
SETUP_URL = routing.BASE_URL + f"setups/{KEY}.json"


def manifest_for(setup_bytes: bytes, sha: str | None = None) -> bytes:
    return json.dumps({
        "schema": "nobrainer-routing-manifest/1",
        "version": "2026-09-29.1",
        "routeOrder": list(routing.ROUTE_ORDER),
        "review": {"reviewedAt": "2026-09-30T09:00:00Z", "reviewer": "reviewer", "verdict": "approve"},
        "setups": {KEY: sha or hashlib.sha256(setup_bytes).hexdigest()},
    }).encode()


class FakeServer:
    """Serves fixed bytes, honours If-None-Match, or fails like a dropped network."""

    def __init__(self, files: dict[str, bytes], offline: bool = False) -> None:
        self.files, self.offline, self.calls = files, offline, []

    def __call__(self, url: str, etag: str | None) -> tuple[int, bytes, str | None]:
        self.calls.append((url, etag))
        if self.offline or url not in self.files:
            raise routing.RoutingError("network error: URLError")
        tag = '"' + hashlib.sha256(self.files[url]).hexdigest()[:12] + '"'
        return (304, b"", etag) if etag == tag else (200, self.files[url], tag)


class Base(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.state = Path(self.temp.name) / ".nobrainer"
        self.setup_bytes = FIXTURE.read_bytes()
        self.setup = json.loads(self.setup_bytes)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def server(self, setup_bytes: bytes | None = None, manifest: bytes | None = None, **kw) -> FakeServer:
        body = setup_bytes or self.setup_bytes
        return FakeServer({MANIFEST_URL: manifest or manifest_for(body), SETUP_URL: body}, **kw)

    def fetch(self, server: FakeServer, now: dt.datetime = NOW, **kw) -> dict:
        return routing.fetch_setup(KEY, self.state, now=now, fetcher=server, **kw)


class KeyTests(unittest.TestCase):
    def test_key_uses_fixed_route_order_and_flags(self) -> None:
        self.assertEqual(routing.build_key(["zen", "openai", "anthropic"], True, False), "openai-anthropic-zen.f1.b0")
        self.assertEqual(routing.build_key(["copilot"], False, True), "copilot.f0.b1")
        for bad in ([], ["openrouter"]):
            with self.assertRaises(routing.RoutingError):
                routing.build_key(bad, False, False)

    def test_fixture_is_a_valid_setup(self) -> None:
        routing.validate_setup(json.loads(FIXTURE.read_text()), KEY)


class FetchTests(Base):
    def test_fetch_verifies_sha_caches_and_stays_quiet_for_the_day(self) -> None:
        server = self.server()
        result = self.fetch(server)
        self.assertEqual((result["routing"], result["status"], result["integrity"]),
                         ("AVAILABLE", "UPDATED", "VERIFIED"))
        self.assertFalse(result["stale"])
        self.assertEqual((self.state / "routing-cache" / f"{KEY}.json").read_bytes(), self.setup_bytes)
        again = self.fetch(server, now=NOW + dt.timedelta(hours=1))
        self.assertEqual(again["status"], "CACHED_TODAY")
        self.assertEqual(len(server.calls), 2)

    def test_next_day_or_request_sends_etag_and_accepts_not_modified(self) -> None:
        server = self.server()
        self.fetch(server)
        result = self.fetch(server, now=NOW + dt.timedelta(days=1))
        self.assertEqual(result["status"], "NOT_MODIFIED")
        self.assertIsNotNone(server.calls[-1][1])
        self.assertEqual(self.fetch(server, force=True)["status"], "NOT_MODIFIED")

    def test_expired_setup_is_usable_but_stale(self) -> None:
        expired = dict(self.setup, expiresAt="2026-09-01T10:00:00Z")
        result = self.fetch(self.server(json.dumps(expired).encode()))
        self.assertEqual(result["routing"], "AVAILABLE")
        self.assertTrue(result["stale"])
        self.assertTrue(result["refreshDue"])

    def test_sha_mismatch_is_refused_and_never_cached(self) -> None:
        bad = self.server(manifest=manifest_for(b"", sha="0" * 64))
        result = self.fetch(bad)
        self.assertEqual(result["routing"], "UNKNOWN")
        self.assertIn("SHA_MISMATCH", result["reason"])
        self.assertFalse((self.state / "routing-cache" / f"{KEY}.json").exists())

    def test_sha_mismatch_keeps_the_last_good_copy(self) -> None:
        self.fetch(self.server())
        newer = json.dumps(dict(self.setup, version="2026-10-06.1")).encode()
        result = self.fetch(self.server(newer, manifest_for(b"", sha="0" * 64)), force=True)
        self.assertEqual((result["status"], result["version"]), ("CACHED_AFTER_ERROR", "2026-09-29.1"))
        self.assertIn("SHA_MISMATCH", result["reason"])

    def test_offline_with_cache_uses_it_without_network(self) -> None:
        self.fetch(self.server())
        offline = self.server(offline=True)
        self.assertEqual(self.fetch(offline, offline=True)["status"], "CACHED_OFFLINE")
        self.assertEqual(offline.calls, [])
        dropped = self.fetch(offline, now=NOW + dt.timedelta(days=1))
        self.assertEqual((dropped["routing"], dropped["status"]), ("AVAILABLE", "CACHED_AFTER_ERROR"))

    def test_offline_without_cache_reports_unknown_and_invents_nothing(self) -> None:
        for kw in ({"offline": True}, {}):
            result = self.fetch(self.server(offline=True), **kw)
            self.assertEqual(result["routing"], "UNKNOWN")
            self.assertIn("keep the current routing", result["action"])
        self.assertFalse((self.state / "routing-cache" / f"{KEY}.json").exists())

    def test_without_manifest_setup_is_accepted_as_unverified(self) -> None:
        server = FakeServer({SETUP_URL: self.setup_bytes})
        result = self.fetch(server)
        self.assertEqual((result["routing"], result["integrity"]), ("AVAILABLE", "UNVERIFIED"))

    def test_setup_for_another_key_is_refused(self) -> None:
        other = json.dumps(dict(self.setup, key="openai.f0.b0")).encode()
        self.assertEqual(self.fetch(self.server(other))["routing"], "UNKNOWN")

    def test_cli_offline_without_cache_exits_unknown(self) -> None:
        run = subprocess.run([sys.executable, str(SCRIPT), "--state-dir", str(self.state), "fetch",
                              "--routes", "anthropic,openai", "--offline"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 3)
        self.assertEqual(json.loads(run.stdout)["routing"], "UNKNOWN")


class LedgerPolicyTests(Base):
    def record(self, job: str, model: str, route: str, outcome: str, times: int = 1, **kw) -> None:
        for _ in range(times):
            routing.record(self.state, job=job, model=model, route=route, outcome=outcome, now=NOW, **kw)

    def order(self, job: str = "coding", **kw) -> list[str]:
        rows, _ = routing.read_ledger(self.state)
        policy = routing.compute_policy(self.setup, rows, kw.pop("excluded", []), kw.pop("min_samples", 5), NOW)
        return [c["id"] for c in policy["jobs"][job]["candidates"]]

    def test_ledger_rows_are_content_free(self) -> None:
        self.record("coding", "openai/alpha-2", "openai", "pass", duration=12.345, quota_error=True)
        row = json.loads((self.state / "routing-ledger.jsonl").read_text())
        self.assertEqual(set(row), {"ts", "job", "model", "route", "outcome", "durationS", "quotaError"})
        self.assertEqual(row["durationS"], 12.3)
        for model in ("fix the login bug in app.py", "openai/alpha 2", "x" * 200):
            with self.assertRaises(routing.RoutingError):
                self.record("coding", model, "openai", "pass")
        with self.assertRaises(routing.RoutingError):
            self.record("writing", "openai/alpha-2", "openai", "pass")

    def test_benchmark_order_holds_below_the_minimum_sample_count(self) -> None:
        benchmark = ["openai/alpha-2", "anthropic/beta-5", "openai/gamma-mini", "anthropic/delta-small"]
        self.assertEqual(self.order(), benchmark)
        self.record("coding", "openai/alpha-2", "openai", "fail", times=4)
        self.assertEqual(self.order(), benchmark)
        self.record("coding", "openai/alpha-2", "openai", "fail")
        self.assertEqual(self.order()[-1], "openai/alpha-2")

    def test_reorder_stays_inside_candidates(self) -> None:
        self.record("coding", "openai/omega-9", "openai", "pass", times=50)
        self.record("coding", "delta-small", "anthropic", "pass", times=8)
        order = self.order()
        self.assertEqual(order[0], "anthropic/delta-small")
        self.assertEqual(set(order), {p["id"] for p in self.setup["candidates"]["coding"]})
        self.assertEqual(len(order), len(set(order)))
        self.assertEqual(self.order("planning"), ["anthropic/beta-5", "openai/alpha-2"])

    def test_quota_and_unknown_outcomes_do_not_count_as_failures(self) -> None:
        self.record("coding", "openai/alpha-2", "openai", "unknown", times=6, quota_error=True)
        self.assertEqual(self.order()[0], "openai/alpha-2")

    def test_excluded_models_never_return_and_main_is_preserved(self) -> None:
        self.record("coding", "anthropic/beta-5", "anthropic", "pass", times=20)
        rows, _ = routing.read_ledger(self.state)
        policy = routing.compute_policy(self.setup, rows, ["Beta 5", "alpha-1"], 5, NOW)
        text = json.dumps(policy)
        self.assertNotIn("anthropic/beta-5", text)
        self.assertNotIn("openai/alpha-1", text)
        self.assertEqual(policy["main"], "PRESERVED")
        self.assertEqual([p["id"] for p in policy["fallbackChain"]], ["openai/alpha-2"])

    def test_cli_policy_persists_exclusions_and_needs_a_cached_setup(self) -> None:
        base = [sys.executable, str(SCRIPT), "--state-dir", str(self.state), "policy", "--routes", "openai,anthropic"]
        self.assertEqual(subprocess.run(base, capture_output=True).returncode, 3)
        self.assertFalse((self.state / "routing-policy.json").exists())
        self.fetch(self.server())
        self.assertEqual(subprocess.run(base + ["--exclude", "Gamma Mini"], capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run(base, capture_output=True).returncode, 0)
        policy = json.loads((self.state / "routing-policy.json").read_text())
        self.assertEqual(policy["excluded"], ["gamma mini"])
        self.assertIsNone(policy["bulk"])


class BlockTests(Base):
    def target(self, text: str) -> Path:
        path = Path(self.temp.name) / "AGENTS.md"
        path.write_text(text, encoding="utf-8")
        return path

    def apply_twice(self, path: Path) -> dict:
        preview = routing.apply_block(path, self.setup, "router")
        self.assertEqual(preview["change"], "PENDING_CONFIRMATION")
        with self.assertRaises(routing.RoutingError):
            routing.apply_block(path, self.setup, "router", write=True, confirm="wrong")
        written = routing.apply_block(path, self.setup, "router", write=True, confirm=preview["previewId"])
        self.assertEqual((written["change"], written["readback"]), ("WRITTEN", "OK"))
        self.assertTrue(Path(written["backup"]).is_file())
        self.assertEqual(routing.apply_block(path, self.setup, "router")["change"], "NO_CHANGE")
        return written

    def test_block_is_appended_once_and_replacement_is_idempotent(self) -> None:
        path = self.target("# Rules\n\n- Keep it small.")
        self.apply_twice(path)
        text = path.read_text()
        self.assertTrue(text.startswith("# Rules\n\n- Keep it small.\n\n" + routing.START))
        self.assertEqual(text.count(routing.START), 1)
        self.assertEqual(text.count("## Model routing for NoBrainer.Tech Flow"), 1)
        plain = routing.apply_block(path, self.setup, "plain")
        self.assertIn("-1. Alpha 2, reasoning xhigh (openai/alpha-2)", plain["diff"])
        self.assertIn("MARKERS", plain["region"])

    def test_unmarked_routing_section_is_replaced_once(self) -> None:
        legacy = (
            "# Flow\n\nIntro.\n\n## Model routing for NoBrainer.Tech Flow\n\nGenerated long ago.\n\n"
            "### Subagents\n1. Old Model (old/model-1)\n\n## Knowledge\n\n- Keep the wiki.\n"
        )
        path = self.target(legacy)
        self.assertEqual(routing.apply_block(path, self.setup, "router")["region"], "SECTION lines 5-10")
        self.apply_twice(path)
        text = path.read_text()
        self.assertNotIn("Old Model", text)
        self.assertEqual(text.count("## Model routing for NoBrainer.Tech Flow"), 1)
        self.assertTrue(text.startswith("# Flow\n\nIntro.\n\n" + routing.START))
        self.assertTrue(text.endswith(routing.END + "\n\n## Knowledge\n\n- Keep the wiki.\n"))

    def test_ambiguous_or_broken_regions_are_refused(self) -> None:
        both = self.setup["blocks"]["router"] + "\n\n## Model routing for NoBrainer.Tech Flow\n\nOld.\n"
        for text in (both, routing.START + "\nhalf a block\n", "text\n" + routing.END + "\n"):
            with self.assertRaises(routing.RoutingError):
                routing.apply_block(self.target(text), self.setup, "router")

    def test_other_model_lines_are_reported_not_changed(self) -> None:
        path = self.target(
            "- Choose subagent models from the list below.\n- Use openai/alpha-2 for reviews.\n- Keep tests.\n"
        )
        preview = routing.apply_block(path, self.setup, "router")
        self.assertEqual(len(preview["otherRoutingLines"]), 2)
        self.assertIn("line 2: - Use openai/alpha-2 for reviews.", preview["otherRoutingLines"])

    def test_bare_block_needs_a_single_native_route_key(self) -> None:
        with self.assertRaises(routing.RoutingError):
            routing.apply_block(self.target(""), self.setup, "bare")

    def test_crlf_files_keep_their_line_endings(self) -> None:
        path = Path(self.temp.name) / "CLAUDE.md"
        path.write_bytes(b"# Rules\r\n")
        preview = routing.apply_block(path, self.setup, "router")
        routing.apply_block(path, self.setup, "router", write=True, confirm=preview["previewId"])
        self.assertNotIn(b"\n", path.read_bytes().replace(b"\r\n", b""))
        self.assertEqual(routing.apply_block(path, self.setup, "router")["change"], "NO_CHANGE")

    def test_cli_dry_run_changes_nothing(self) -> None:
        self.fetch(self.server())
        path = self.target("# Rules\n")
        run = subprocess.run([sys.executable, str(SCRIPT), "--state-dir", str(self.state), "apply", "--routes",
                              "openai,anthropic", "--file", str(path), "--block", "router"],
                             capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("CHANGE: PENDING_CONFIRMATION", run.stdout)
        self.assertIn("+" + routing.START, run.stdout)
        self.assertEqual(path.read_text(), "# Rules\n")


if __name__ == "__main__":
    unittest.main()
