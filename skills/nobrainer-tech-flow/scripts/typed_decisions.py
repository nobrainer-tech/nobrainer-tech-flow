#!/usr/bin/env python3
"""Bounded advisory typed decisions; never executes selected actions."""
import argparse
import functools
import json
import math
import os
import platform
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

from decision_config import read


def finite(value, low, high):
    return type(value) in (int, float) and math.isfinite(value) and low <= value <= high


def validate_request(request):
    if not isinstance(request, dict) or set(request) != {"state", "questions"}:
        raise ValueError("request_fields")
    if not isinstance(request["state"], (str, dict, list)):
        raise ValueError("state")
    questions = request["questions"]
    if not isinstance(questions, dict) or not 1 <= len(questions) <= 16:
        raise ValueError("questions")
    for key, question in questions.items():
        if not isinstance(key, str) or not key or not isinstance(question, dict):
            raise ValueError("question")
        if not isinstance(question.get("instructions"), (str, dict, list)) or not question["instructions"]:
            raise ValueError("instructions")
        kind = question.get("type")
        criteria = question.get("criteria")
        if kind == "choice":
            if not isinstance(criteria, dict) or not criteria or not all(isinstance(k, str) and k for k in criteria):
                raise ValueError("choice_criteria")
        elif kind == "score":
            if not isinstance(criteria, list) or len(criteria) < 2:
                raise ValueError("score_criteria")
        elif kind != "noul":
            raise ValueError("question_type")
    return request


def validate_answers(request, response):
    answers = response.get("answers") if isinstance(response, dict) else None
    if not isinstance(answers, dict) or set(answers) != set(request["questions"]):
        raise ValueError("answer_ids")
    clean = {}
    for key, question in request["questions"].items():
        answer = answers[key]
        kind = question["type"]
        if not isinstance(answer, dict) or answer.get("type") != kind:
            raise ValueError("answer_type")
        if kind == "noul":
            if not finite(answer.get("noul"), 0, 1):
                raise ValueError("noul")
            clean[key] = {"type": kind, "noul": answer["noul"]}
            continue
        keys = set(question["criteria"]) if kind == "choice" else {str(i) for i in range(len(question["criteria"]))}
        probabilities = answer.get("probabilities")
        if not isinstance(probabilities, dict) or set(probabilities) != keys:
            raise ValueError("distribution_keys")
        if not all(finite(p, 0, 1) for p in probabilities.values()) or abs(sum(probabilities.values()) - 1) > 0.02:
            raise ValueError("distribution_values")
        if not finite(answer.get("confidence"), 0, 1):
            raise ValueError("confidence")
        value = answer.get(kind)
        if kind == "choice" and (not isinstance(value, str) or value not in keys):
            raise ValueError("choice")
        if kind == "score" and not finite(value, 0, len(keys) - 1):
            raise ValueError("score")
        clean[key] = {"type": kind, kind: value, "confidence": answer["confidence"], "probabilities": probabilities}
    return clean


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("redirect_not_allowed")


def worker(provider, model, request, key=None):
    if provider == "jev":
        if not key:
            return {"error": "MISSING_TYPESAFE_API_KEY"}
        payload = json.dumps(dict(request, model=model)).encode()
        req = urllib.request.Request("https://api.typesafe.ai/v1/systemone", data=payload,
                                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
        with urllib.request.build_opener(NoRedirect).open(req, timeout=120) as response:
            raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            return {"error": "RESPONSE_TOO_LARGE"}
        return json.loads(raw)
    if provider != "laya":
        return {"error": "UNKNOWN_PROVIDER"}
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        return {"error": "UNSUPPORTED_LOCAL_RUNTIME"}
    # Never fetch weights implicitly: model must already be available offline.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        import laya_mlx
        from huggingface_hub import snapshot_download
    except ImportError:
        return {"error": "MISSING_LOCAL_RUNTIME"}
    if not Path(model).is_dir():
        try:
            model_path = snapshot_download(model, local_files_only=True, allow_patterns=[
                "model.safetensors", "rl_agent_config.json", "encoder/config.json", "tokenizer/*", "mlx_config.json"])
        except Exception:
            return {"error": "MISSING_LOCAL_MODEL"}
    else:
        model_path = model
    try:
        agent = laya_mlx.load(model_path, dtype="float16")
    except Exception:
        return {"error": "INCOMPATIBLE_LOCAL_MODEL"}
    result = agent.predict(request["state"], request["questions"])
    result["model"] = model
    return result


# The worker child gets only these variables (compared in upper case: Windows names
# ignore case and proxies are often lower case). Nothing else from the environment
# reaches it, so neither a key nor any other secret can be forwarded by accident.
CHILD_ENV = {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "HOME", "USERPROFILE",
             "TMPDIR", "TEMP", "TMP", "LANG", "LC_ALL", "LC_CTYPE", "PYTHONPATH", "PYTHONHOME",
             "VIRTUAL_ENV", "XDG_CACHE_HOME", "HF_HOME", "HF_HUB_CACHE",
             "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE", "SSL_CERT_DIR"}
KEY_LIMIT = 4096


def invoke(provider, model, request, timeout, key=None):
    # The TypeSafe key comes only from the caller (piped with --key-stdin) and reaches
    # the child on stdin, only for Jev. The helper itself never reads a credential.
    env = {k: v for k, v in os.environ.items() if k.upper() in CHILD_ENV}
    process = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", provider, model],
                             input=json.dumps({"request": request, "key": key if provider == "jev" else None}),
                             capture_output=True, text=True, timeout=timeout, env=env)
    if process.returncode:
        raise ValueError("provider_failed")
    return json.loads(process.stdout)


def read_piped_key(stream):
    """Return the first line of a piped key, or None when nothing usable was piped."""
    line = stream.readline(KEY_LIMIT + 1).strip()
    if not line or len(line) > KEY_LIMIT:
        return None
    return line


def evaluate(requests, configuration, approved=False, call=invoke):
    cfg = configuration["config"]
    results = []
    attempted = 0
    for request in requests:
        reason = None
        if configuration["status"] == "INVALID_CONFIG_CORE_FALLBACK":
            reason = "INVALID_CONFIG"
        elif cfg["mode"] == "off" or cfg["provider"] == "core":
            reason = "OFF"
        elif not approved:
            reason = "DATA_NOT_APPROVED"
        elif attempted >= cfg["max_calls_per_run"]:
            reason = "CALL_LIMIT"
        started = time.monotonic()
        result = {"status": "CORE_FALLBACK", "provider": cfg["provider"], "model": cfg["model"]}
        if reason is None:
            try:
                validate_request(request)
                attempted += 1
                response = call(cfg["provider"], cfg["model"], request, cfg["timeout_seconds"])
                if isinstance(response, dict) and response.get("error"):
                    allowed = {"MISSING_TYPESAFE_API_KEY", "UNSUPPORTED_LOCAL_RUNTIME", "MISSING_LOCAL_RUNTIME",
                               "MISSING_LOCAL_MODEL", "INCOMPATIBLE_LOCAL_MODEL", "UNKNOWN_PROVIDER"}
                    reason = response["error"] if isinstance(response["error"], str) and response["error"] in allowed else "INVALID_OR_UNAVAILABLE"
                else:
                    result["answers"] = validate_answers(request, response)
                    result["status"] = "SHADOW_SUGGESTION"
                    model = response.get("model")
                    result["model"] = model if isinstance(model, str) and len(model) <= 128 else cfg["model"]
            except subprocess.TimeoutExpired:
                reason = "TIMEOUT"
            except (ValueError, TypeError, KeyError, OSError):
                reason = "INVALID_OR_UNAVAILABLE"
        result.update(reason=reason, calls_used=attempted,
                      elapsed_seconds=round(time.monotonic() - started, 6))
        results.append(result)
    return {"status": "ADVISORY_ONLY", "calls_used": attempted, "results": results}


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        try:
            # Third-party stdout may contain progress or input; contain it.
            import contextlib
            import io
            payload = json.load(sys.stdin)
            request = validate_request(payload["request"])
            key = payload.get("key") if isinstance(payload.get("key"), str) else None
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                result = worker(sys.argv[2], sys.argv[3], request, key)
            print(json.dumps(result))
            return 0
        except Exception:
            print(json.dumps({"error": "PROVIDER_UNAVAILABLE"}))
            return 2
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(".nobrainer/flow.json"))
    parser.add_argument("--request", type=Path, help="JSON array of requests; otherwise stdin")
    parser.add_argument("--approved-data", action="store_true", help="Only with existing approval for this data and provider")
    parser.add_argument("--key-stdin", action="store_true",
                        help="Jev only: read your TypeSafe key from the first line of stdin (pipe it from your "
                             "secret manager); requires --request")
    # Removed in 2.7.3: the helper no longer reads a key from the environment.
    parser.add_argument("--key-env", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.key_env is not None:
        print(json.dumps({"status": "CORE_FALLBACK", "reason": "KEY_ENV_REMOVED_USE_KEY_STDIN"}))
        return 2
    try:
        if args.key_stdin and not args.request:
            raise ValueError("key_stdin_requires_request")
        key = read_piped_key(sys.stdin) if args.key_stdin else None
        data = json.loads(args.request.read_text()) if args.request else json.load(sys.stdin)
        if not isinstance(data, list) or len(data) > 100:
            raise ValueError("batch")
        call = functools.partial(invoke, key=key)
        print(json.dumps(evaluate(data, read(args.config), args.approved_data, call), ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError):
        print(json.dumps({"status": "CORE_FALLBACK", "reason": "INVALID_INPUT"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
