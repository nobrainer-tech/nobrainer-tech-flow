from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import http.client
import io
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/nobrainer-auto-fine-tune/scripts/benchmark_routing.py"
FIXTURE = ROOT / "tests/fixtures/routing-setup-openai-anthropic.f0.b0.json"
EMPTY_FIXTURE = ROOT / "tests/fixtures/routing-setup-empty.json"
SPEC = importlib.util.spec_from_file_location("benchmark_routing", SCRIPT)
routing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routing)

KEY = "openai-anthropic.f0.b0"
NOW = dt.datetime(2026, 9, 30, 12, 0, tzinfo=dt.timezone.utc)
MANIFEST_URL = routing.BASE_URL + "manifest.json"
SETUP_URL = routing.BASE_URL + f"setups/{KEY}.json"


def empty_setup(setup: dict) -> dict:
    """What the producer publishes when nothing reachable fits the limits (same key as the main fixture)."""
    return json.loads(EMPTY_FIXTURE.read_text())


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

    def test_refused_manifest_fails_closed_even_with_a_cache(self) -> None:
        self.fetch(self.server())
        good = json.loads(manifest_for(self.setup_bytes))
        for manifest in (dict(good, routeOrder=[*routing.ROUTE_ORDER, "newplan"]),
                         dict(good, review={"reviewedAt": "2026-09-30T09:00:00Z", "verdict": "reject"}),
                         "not json"):
            body = manifest.encode() if isinstance(manifest, str) else json.dumps(manifest).encode()
            server = self.server(manifest=body)
            result = self.fetch(server, force=True)
            self.assertEqual((result["routing"], result["status"]), ("UNKNOWN", "MANIFEST_REFUSED"))
            self.assertEqual([url for url, _ in server.calls], [MANIFEST_URL])
        self.assertEqual((self.state / "routing-cache" / "manifest.json").read_bytes(), manifest_for(self.setup_bytes))

    def cli(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), "--state-dir", str(self.state), *args],
                              capture_output=True, text=True)

    def test_refusal_persists_until_an_acceptable_manifest(self) -> None:
        self.fetch(self.server())
        good = json.loads(manifest_for(self.setup_bytes))
        bad = json.dumps(dict(good, version="2026-10-01.1", review={"verdict": "reject"})).encode()
        self.assertEqual(self.fetch(self.server(manifest=bad), force=True)["status"], "MANIFEST_REFUSED")
        state = json.loads((self.state / "routing-cache" / "state.json").read_text())
        self.assertEqual(state["refused"]["manifestVersion"], "2026-10-01.1")
        self.assertNotIn("checkedOn", state["setups"][KEY])
        # Same day, not forced: the rejected manifest, a dropped network and --offline all refuse.
        for server, kw in ((self.server(manifest=bad), {}), (self.server(offline=True), {}),
                           (self.server(offline=True), {"offline": True})):
            self.assertEqual(self.fetch(server, **kw)["status"], "MANIFEST_REFUSED")
        # The refusal flag alone also blocks the same-day cache, even if checkedOn comes back.
        state_path = self.state / "routing-cache" / "state.json"
        state = json.loads(state_path.read_text())
        state["setups"][KEY]["checkedOn"] = NOW.astimezone().date().isoformat()
        state_path.write_text(json.dumps(state))
        self.assertEqual(self.fetch(self.server(offline=True))["status"], "MANIFEST_REFUSED")
        target = Path(self.temp.name) / "AGENTS.md"
        target.write_text("# Rules\n")
        for command in (["fetch", "--offline"], ["policy"], ["apply", "--file", str(target), "--block", "router"]):
            run = self.cli(command[0], "--routes", "openai,anthropic", *command[1:])
            self.assertEqual(run.returncode, 3, run.stderr)
            self.assertEqual(json.loads(run.stdout)["status"], "MANIFEST_REFUSED")
        self.assertEqual(self.fetch(self.server(), force=True)["routing"], "AVAILABLE")
        self.assertEqual(self.cli("policy", "--routes", "openai,anthropic").returncode, 0)

    def test_tampered_cache_is_never_reported_as_verified(self) -> None:
        self.fetch(self.server())
        cached = self.state / "routing-cache" / f"{KEY}.json"
        cached.write_bytes(json.dumps(dict(self.setup, version="tampered")).encode())
        for now in (NOW, NOW + dt.timedelta(days=1)):
            result = self.fetch(self.server(offline=True), now=now)
            self.assertEqual((result["routing"], result["status"]), ("UNKNOWN", "INTEGRITY_MISMATCH"))
        self.assertEqual(self.fetch(self.server(offline=True), offline=True)["routing"], "UNKNOWN")
        self.assertEqual(self.cli("policy", "--routes", "openai,anthropic").returncode, 3)
        repaired = self.fetch(self.server())
        self.assertEqual((repaired["status"], repaired["version"]), ("UPDATED", "2026-09-29.1"))

    def test_not_modified_cache_that_misses_the_manifest_is_not_used(self) -> None:
        self.fetch(self.server())
        newer = json.dumps(dict(self.setup, version="2026-10-06.1")).encode()
        calls = []

        def stale_host(body: bytes):
            def fetcher(url: str, etag: str | None):
                calls.append((url, etag))
                if url == MANIFEST_URL:
                    return 200, manifest_for(newer), '"m2"'
                return (304, b"", etag) if etag else (200, body, '"s2"')
            return fetcher

        result = self.fetch(stale_host(newer), force=True)
        self.assertEqual((result["status"], result["version"]), ("UPDATED", "2026-10-06.1"))
        self.assertEqual(calls[-1], (SETUP_URL, None))
        self.assertEqual(self.fetch(self.server(), force=True)["version"], "2026-09-29.1")  # original again
        result = self.fetch(stale_host(b"{}"), force=True)
        self.assertEqual((result["routing"], result["status"]), ("UNKNOWN", "SHA_MISMATCH"))

    def test_broken_http_responses_fall_back_instead_of_crashing(self) -> None:
        self.fetch(self.server())
        with mock.patch.object(routing.urllib.request, "urlopen", side_effect=http.client.IncompleteRead(b"")):
            with self.assertRaises(routing.RoutingError):
                routing.http_fetch(SETUP_URL, None)
            result = routing.fetch_setup(KEY, self.state, now=NOW, force=True)
        self.assertEqual((result["routing"], result["status"]), ("AVAILABLE", "CACHED_AFTER_ERROR"))

    def test_cli_only_fetches_from_the_published_host(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit_:
            routing.main(["--state-dir", str(self.state), "fetch", "--routes", "openai", "--offline",
                          "--base-url", "https://example.com/"])
        self.assertEqual(exit_.exception.code, 2)

    def test_corrupt_state_counts_as_an_empty_cache(self) -> None:
        cache = self.state / "routing-cache"
        cache.mkdir(parents=True)
        (cache / f"{KEY}.json").write_bytes(self.setup_bytes)
        for broken in ('{"setups": [1, 2], "manifest": "x"}', '[1]', '{"setups": {"%s": 5}}' % KEY):
            (cache / "state.json").write_text(broken)
            self.assertEqual(self.fetch(self.server(offline=True), offline=True)["routing"], "UNKNOWN")
            self.assertEqual(self.cli("policy", "--routes", "openai,anthropic").returncode, 3)
        self.assertEqual(self.fetch(self.server())["status"], "UPDATED")

    def test_setup_for_another_key_is_refused(self) -> None:
        other = json.dumps(dict(self.setup, key="openai.f0.b0")).encode()
        self.assertEqual(self.fetch(self.server(other))["routing"], "UNKNOWN")

    def test_empty_setup_is_no_recommendation(self) -> None:
        result = self.fetch(self.server(json.dumps(empty_setup(self.setup)).encode()))
        self.assertEqual((result["routing"], result["integrity"]), ("NO_RECOMMENDATION", "VERIFIED"))
        broken = dict(empty_setup(self.setup), blocks=self.setup["blocks"])
        with self.assertRaises(routing.RoutingError):
            routing.validate_setup(broken, KEY)
        with self.assertRaises(routing.RoutingError):
            routing.validate_setup(dict(self.setup, blocks=None), KEY)

    def test_cli_offline_without_cache_exits_unknown(self) -> None:
        run = subprocess.run([sys.executable, str(SCRIPT), "--state-dir", str(self.state), "fetch",
                              "--routes", "anthropic,openai", "--offline"], capture_output=True, text=True)
        self.assertEqual(run.returncode, 3)
        self.assertEqual(json.loads(run.stdout)["routing"], "UNKNOWN")


class LedgerPolicyTests(Base):
    def record(self, job: str, model: str, route: str, outcome: str, times: int = 1, **kw) -> None:
        for _ in range(times):
            routing.record(self.state, job=job, model=model, route=route, outcome=outcome, now=NOW, **kw)

    def policy(self, **kw) -> dict:
        rows, _ = routing.read_ledger(self.state)
        return routing.compute_policy(self.setup, rows, kw.pop("excluded", []), kw.pop("min_samples", 5), NOW)

    def order(self, job: str = "coding", **kw) -> list[str]:
        return [c["id"] for c in self.policy(**kw)["jobs"][job]["candidates"]]

    def test_ledger_rows_are_content_free(self) -> None:
        self.record("coding", "openai/alpha-2", "openai", "pass", duration=12.345, quota_error=True)
        row = json.loads((self.state / "routing-ledger.jsonl").read_text())
        self.assertEqual(set(row), {"ts", "job", "model", "route", "effort", "outcome", "durationS", "quotaError"})
        self.assertEqual(row["durationS"], 12.3)
        for model in ("fix the login bug in app.py", "openai/alpha 2", "x" * 200):
            with self.assertRaises(routing.RoutingError):
                self.record("coding", model, "openai", "pass")
        for job, effort in (("writing", None), ("coding", "turbo")):
            with self.assertRaises(routing.RoutingError):
                self.record(job, "openai/alpha-2", "openai", "pass", effort=effort)

    def test_benchmark_order_holds_below_the_minimum_sample_count(self) -> None:
        benchmark = ["openai/alpha-2", "anthropic/beta-5", "openai/gamma-mini", "openai/gamma-mini",
                     "anthropic/delta-small", "astra-native"]
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
        pairs = [(c["id"], c["effort"]) for c in self.policy()["jobs"]["coding"]["candidates"]]
        self.assertEqual(len(pairs), len(set(pairs)))
        self.assertEqual(self.order("planning"), ["anthropic/beta-5", "openai/alpha-2"])

    def test_bare_openai_ids_match_prefixed_ledger_rows(self) -> None:
        self.record("coding", "openai/astra-native", "openai", "pass", times=5)
        self.assertEqual(self.order()[0], "astra-native")
        self.assertEqual(self.order(excluded=["astra-native"])[-1], "anthropic/delta-small")

    def test_empty_setup_writes_no_block_and_no_new_policy(self) -> None:
        self.fetch(self.server())
        base = [sys.executable, str(SCRIPT), "--state-dir", str(self.state)]
        routes = ["--routes", "openai,anthropic"]
        self.assertEqual(subprocess.run(base + ["policy", *routes], capture_output=True).returncode, 0)
        previous = (self.state / "routing-policy.json").read_bytes()
        self.setup = empty_setup(self.setup)
        self.record("coding", "openai/alpha-2", "openai", "pass", times=9)
        rows, _ = routing.read_ledger(self.state)
        policy = routing.compute_policy(self.setup, rows, [], 5, NOW)
        self.assertEqual(policy["recommendation"], "NONE")
        self.assertTrue(all(not job["candidates"] for job in policy["jobs"].values()))
        self.assertEqual((policy["bulk"], policy["fallbackChain"]), (None, []))
        fetched = self.fetch(self.server(json.dumps(self.setup).encode()), force=True)
        self.assertEqual(fetched["action"], routing.NO_RECOMMENDATION)
        target = Path(self.temp.name) / "AGENTS.md"
        target.write_text("# Rules\n")
        for command in (["apply", *routes, "--file", str(target), "--block", "router"], ["policy", *routes]):
            run = subprocess.run(base + command, capture_output=True, text=True)
            self.assertEqual(run.returncode, 3)
            self.assertEqual(json.loads(run.stdout)["action"], "no recommendation: keep the current routing")
        self.assertEqual(target.read_text(), "# Rules\n")
        self.assertEqual((self.state / "routing-policy.json").read_bytes(), previous)
        with self.assertRaises(routing.RoutingError):
            routing.apply_block(target, self.setup, "router")

    def test_without_evidence_each_job_starts_with_its_default_pick(self) -> None:
        policy = self.policy()
        for job, data in policy["jobs"].items():
            first, default = data["candidates"][0], self.setup["jobs"][job]
            self.assertEqual((first["id"], first["effort"]), (default["id"], default["effort"]), job)
            self.assertEqual(data["order"], "BENCHMARK")
        self.assertEqual(policy["bulk"]["id"], self.setup["jobs"]["bulk"]["id"])

    def test_effort_variants_learn_separately(self) -> None:
        self.record("coding", "openai/gamma-mini", "openai", "pass", times=6)
        self.assertEqual(self.order()[:2], ["openai/alpha-2", "anthropic/beta-5"])
        self.record("coding", "openai/gamma-mini", "openai", "pass", times=6, effort="high")
        top = self.policy()["jobs"]["coding"]["candidates"][0]
        self.assertEqual((top["id"], top["effort"], top["pass"]), ("openai/gamma-mini", "high", 6))
        self.record("coding", "delta-small", "anthropic", "pass", times=6)
        delta = [c for c in self.policy()["jobs"]["coding"]["candidates"] if c["id"].endswith("delta-small")]
        self.assertEqual(delta[0]["pass"], 6)

    def test_skip_entries_keep_excluded_by(self) -> None:
        skip = {item["family"]: item for item in self.policy()["skip"]}
        self.assertEqual(skip["Zeta"]["excludedBy"], "cost")
        self.assertNotIn("excludedBy", skip["Alpha 1"])

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
        backups = self.state / "routing-backups"
        written = routing.apply_block(path, self.setup, "router", write=True, confirm=preview["previewId"],
                                      backup_dir=backups)
        self.assertEqual((written["change"], written["readback"]), ("WRITTEN", "OK"))
        backup = Path(written["backup"])
        self.assertEqual(backup.parent, backups)
        self.assertTrue(backup.name.startswith(path.name + ".") and backup.name.endswith("Z.bak"))
        self.assertEqual([p.name for p in path.parent.iterdir() if p.is_file()], [path.name])
        self.assertEqual(routing.apply_block(path, self.setup, "router")["change"], "NO_CHANGE")
        return written

    def test_block_is_appended_once_and_replacement_is_idempotent(self) -> None:
        path = self.target("# Rules\n\n- Keep it small.")
        self.apply_twice(path)
        text = path.read_text()
        self.assertTrue(text.startswith("# Rules\n\n- Keep it small.\n\n" + routing.START))
        self.assertEqual(text.count(routing.START), 1)
        self.assertEqual(text.count("## Model routing for nobrainer-tech-flow"), 1)
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
        self.assertNotIn("NoBrainer.Tech Flow", text)
        self.assertEqual(text.count("## Model routing for nobrainer-tech-flow"), 1)
        self.assertTrue(text.startswith("# Flow\n\nIntro.\n\n" + routing.START))
        self.assertTrue(text.endswith(routing.END + "\n\n## Knowledge\n\n- Keep the wiki.\n"))

    def test_unmarked_section_with_current_title_is_replaced(self) -> None:
        path = self.target("# Flow\n\n## Model routing for nobrainer-tech-flow\n\n- Old line.\n\n## Next\n")
        self.assertEqual(routing.apply_block(path, self.setup, "router")["region"], "SECTION lines 3-5")
        self.apply_twice(path)
        self.assertNotIn("Old line", path.read_text())
        self.assertTrue(path.read_text().endswith(routing.END + "\n\n## Next\n"))

    def test_ambiguous_or_broken_regions_are_refused(self) -> None:
        both = self.setup["blocks"]["router"] + "\n\n## Model routing for NoBrainer.Tech Flow\n\nOld.\n"
        titles = ("## Model routing for nobrainer-tech-flow\n\nNew.\n\n"
                  "## Model routing for NoBrainer.Tech Flow\n\nOld.\n")
        for text in (both, titles, routing.START + "\nhalf a block\n", "text\n" + routing.END + "\n"):
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
        written = routing.apply_block(path, self.setup, "router", write=True, confirm=preview["previewId"],
                                      backup_dir=self.state / "routing-backups")
        self.assertEqual(written["readback"], "OK")
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
