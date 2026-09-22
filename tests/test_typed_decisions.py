import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1] / "skills/nobrainer-ultra/scripts"
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("typed_decisions", ROOT / "typed_decisions.py")
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
sys.path.pop(0)

REQUEST = {"state": "Synthetic refund request", "questions": {
    "route": {"type": "choice", "instructions": "Select route", "criteria": {"billing": "payments", "other": "anything else"}}}}
RESPONSE = {"answers": {"route": {"type": "choice", "choice": "billing", "confidence": 1.0,
                                   "probabilities": {"billing": 1.0, "other": 0.0}}}}


def configuration(mode="shadow", limit=1):
    return {"status": "CONFIGURED", "config": {"mode": mode, "provider": "jev", "model": "jev-latest",
                                               "timeout_seconds": 1, "max_calls_per_run": limit}}


class TypedDecisionTests(unittest.TestCase):
    def test_worker_rejects_unknown_provider_and_unsupported_platform(self):
        from unittest.mock import patch
        self.assertEqual(runtime.worker("bogus", "model", REQUEST)["error"], "UNKNOWN_PROVIDER")
        with patch.object(runtime.platform, "system", return_value="Linux"):
            self.assertEqual(runtime.worker("laya", "model", REQUEST)["error"], "UNSUPPORTED_LOCAL_RUNTIME")

    def test_failure_keeps_model_and_only_allowlisted_reason(self):
        for error, expected in [("MISSING_LOCAL_MODEL", "MISSING_LOCAL_MODEL"),
                                ("synthetic secret", "INVALID_OR_UNAVAILABLE")]:
            result = runtime.evaluate([REQUEST], configuration(), True, lambda *args: {"error": error})["results"][0]
            self.assertEqual(result["model"], "jev-latest")
            self.assertEqual(result["reason"], expected)
            self.assertNotIn("synthetic secret", str(result))

    def test_off_and_unapproved_never_touch_provider(self):
        def forbidden(*args):
            self.fail("Provider called without opt-in")
        for mode, approved in [("off", True), ("shadow", False)]:
            result = runtime.evaluate([REQUEST], configuration(mode), approved, forbidden)
            self.assertEqual(result["calls_used"], 0)
            self.assertEqual(result["results"][0]["status"], "CORE_FALLBACK")

    def test_call_limit_is_enforced_across_batch(self):
        calls = []
        def provider(*args):
            calls.append(args)
            return RESPONSE
        result = runtime.evaluate([REQUEST, REQUEST], configuration(), True, provider)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["results"][0]["status"], "SHADOW_SUGGESTION")
        self.assertEqual(result["results"][1]["reason"], "CALL_LIMIT")

    def test_timeout_is_counted_and_not_retried(self):
        def timeout(*args):
            raise subprocess.TimeoutExpired("synthetic", 1)
        result = runtime.evaluate([REQUEST, REQUEST], configuration(), True, timeout)
        self.assertEqual([r["reason"] for r in result["results"]], ["TIMEOUT", "CALL_LIMIT"])

    def test_invalid_distribution_nan_missing_and_unknown_ids_rejected(self):
        import copy
        for failure in ("nan", "missing", "extra", "wrong_sum"):
            response = copy.deepcopy(RESPONSE)
            a = response["answers"]["route"]
            if failure == "nan": a["confidence"] = float("nan")
            if failure == "missing": del a["probabilities"]["other"]
            if failure == "extra": response["answers"]["injected"] = a
            if failure == "wrong_sum": a["probabilities"]["billing"] = 0.1
            with self.assertRaises(ValueError): runtime.validate_answers(REQUEST, response)

    def test_provider_fields_cannot_leak_into_advisory_output(self):
        import copy
        response = copy.deepcopy(RESPONSE)
        response["answers"]["route"]["execute"] = "untrusted code"
        response["secret"] = "synthetic secret"
        result = runtime.evaluate([REQUEST], configuration(), True, lambda *args: response)
        self.assertNotIn("untrusted code", str(result))
        self.assertNotIn("synthetic secret", str(result))


if __name__ == "__main__":
    unittest.main()
