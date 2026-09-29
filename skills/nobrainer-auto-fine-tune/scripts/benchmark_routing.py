#!/usr/bin/env python3
"""Benchmark routing prior with local learning for nobrainer-auto-fine-tune.

Builds the setup key from reachable routes, fetches and caches one published
routing setup, appends content-free ledger rows, recomputes the local routing
policy and previews or applies the routing block in an instruction file.
"""

from __future__ import annotations

import argparse
import datetime as dt
import difflib
import hashlib
import http.client
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable


BASE_URL = "https://nobrainer.tech/benchmark/routing/v1/"
ROUTE_PREFIX = {
    "openai": "openai/",
    "anthropic": "anthropic/",
    "zai": "zai/",
    "kimi": "kimi/",
    "minimax": "minimax/",
    "copilot": "github-copilot/",
    "zen": "opencode-zen/",
}
ROUTE_ORDER = tuple(ROUTE_PREFIX)
JOBS = ("coding", "agentic", "research", "planning", "orchestration", "bulk")
CANDIDATE_JOBS = JOBS[:-1]
OUTCOMES = ("pass", "fail", "unknown")
EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")
SKIP_FIELDS = ("family", "reason", "replacedBy", "betterValue", "excludedBy")
NO_RECOMMENDATION = "no recommendation: keep the current routing"
BLOCKS = ("router", "plain", "bare")
START = "<!-- nobrainer-routing:start -->"
END = "<!-- nobrainer-routing:end -->"
# Current title first; older copies say "NoBrainer.Tech Flow". Both count as existing routing.
SECTION_RE = re.compile(
    r"^(#{1,6})[ \t]+Model routing for (?:nobrainer-tech-flow|NoBrainer\.Tech Flow)[ \t#]*$", re.I
)
HEADING_RE = re.compile(r"^(#{1,6})[ \t]")
FENCE_RE = re.compile(r"^[ \t]{0,3}(```|~~~)")
# Router ids carry a provider prefix; Codex-native openai ids may be bare.
PICK_ID_RE = re.compile(r"^(?:[a-z0-9-]+/)?[A-Za-z0-9._:-]+$")
MODEL_RE = re.compile(r"^(?:[a-z0-9-]+/)?[A-Za-z0-9._:-]{1,120}$")
ROLE = r"\b(subagents?|workers?|main agent)\b"
MODEL_LINE_RE = re.compile(rf"(?i)\bmodels?\b.*{ROLE}|{ROLE}.*\bmodels?\b")
MAX_BYTES = 1024 * 1024
TIMEOUT_SECONDS = 10
DEFAULT_MIN_SAMPLES = 5
# Beta(1, 1) prior: an untried or under-sampled candidate counts as an even chance.
PRIOR_MEAN = 0.5

Fetcher = Callable[[str, "str | None"], "tuple[int, bytes, str | None]"]


class RoutingError(Exception):
    """A refused input, invalid file or failed fetch, reported in one line."""


def build_key(routes: list[str], fast: bool, budget: bool) -> str:
    chosen = set()
    for route in routes:
        route = route.strip().lower()
        if route not in ROUTE_PREFIX:
            raise RoutingError(f"unknown route: {route!r}; use {', '.join(ROUTE_ORDER)}")
        chosen.add(route)
    if not chosen:
        raise RoutingError("at least one reachable route is required")
    return "-".join(r for r in ROUTE_ORDER if r in chosen) + f".f{int(fast)}.b{int(budget)}"


def parse_time(value: Any) -> dt.datetime:
    try:
        parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise RoutingError(f"invalid timestamp: {value!r}") from None
    if parsed.tzinfo is None:
        raise RoutingError(f"timestamp has no timezone: {value!r}")
    return parsed


def _check_pick(pick: Any, routes: list[str], where: str, nullable: bool = False) -> None:
    if pick is None and nullable:
        return
    if not isinstance(pick, dict) or not isinstance(pick.get("family"), str):
        raise RoutingError(f"setup {where} is not a valid pick")
    if not isinstance(pick.get("id"), str) or not PICK_ID_RE.fullmatch(pick["id"]):
        raise RoutingError(f"setup {where} has an invalid id")
    if pick.get("route") not in routes:
        raise RoutingError(f"setup {where} uses a route outside the key")
    if pick.get("ifNotAvailable") is not None:
        _check_pick(pick["ifNotAvailable"], routes, f"{where}.ifNotAvailable")


def validate_setup(data: Any, key: str) -> dict[str, Any]:
    """Check the fields Flow relies on; anything else in the file is ignored."""
    if not isinstance(data, dict) or data.get("schema") != "nobrainer-routing-setup/1":
        raise RoutingError("not a nobrainer-routing-setup/1 file")
    if data.get("key") != key:
        raise RoutingError(f"setup key {data.get('key')!r} does not match {key!r}")
    routes, flags = key.split(".", 1)
    routes = routes.split("-")
    if not isinstance(data.get("fast"), bool) or not isinstance(data.get("budget"), bool):
        raise RoutingError("setup fast and budget must be booleans")
    if data.get("routes") != routes or flags != f"f{int(data['fast'])}.b{int(data['budget'])}":
        raise RoutingError("setup routes or flags do not match its key")
    parse_time(data.get("expiresAt"))
    if not isinstance(data.get("empty"), bool):
        raise RoutingError("setup empty must be a boolean")
    main, jobs, candidates, blocks = (data.get(k) for k in ("main", "jobs", "candidates", "blocks"))
    if not isinstance(main, dict) or not {"highStakes", "everyday"} <= set(main):
        raise RoutingError("setup main is incomplete")
    if not isinstance(jobs, dict) or not isinstance(candidates, dict) or not isinstance(data.get("subagents"), list):
        raise RoutingError("setup jobs, candidates or subagents are missing")
    for job in JOBS:
        if job not in jobs:
            raise RoutingError(f"setup jobs.{job} is missing")
        _check_pick(jobs[job], routes, f"jobs.{job}", nullable=True)
    for job in CANDIDATE_JOBS:
        picks = candidates.get(job)
        if not isinstance(picks, list) or len(picks) > 6:
            raise RoutingError(f"setup candidates.{job} must be a list of up to six picks")
        for index, pick in enumerate(picks):
            _check_pick(pick, routes, f"candidates.{job}[{index}]")
    for index, pick in enumerate(data["subagents"]):
        _check_pick(pick, routes, f"subagents[{index}]")
    if data["empty"]:
        picks = [main["highStakes"], main["everyday"], *jobs.values(), *data["subagents"]]
        if blocks is not None or any(p is not None for p in picks) or any(candidates[j] for j in CANDIDATE_JOBS):
            raise RoutingError("an empty setup must have no picks, no candidates and no blocks")
        return data
    if not isinstance(blocks, dict):
        raise RoutingError("setup blocks are missing")
    for name in BLOCKS:
        block = blocks.get(name)
        if block is None and name == "bare":
            continue
        if (not isinstance(block, str) or not block.startswith(START + "\n") or not block.endswith("\n" + END)
                or block.count(START) != 1 or block.count(END) != 1):
            raise RoutingError(f"setup blocks.{name} is not wrapped in one pair of routing markers")
    return data


def validate_manifest(data: Any) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema") != "nobrainer-routing-manifest/1":
        raise RoutingError("not a nobrainer-routing-manifest/1 file")
    if tuple(data.get("routeOrder") or ()) != ROUTE_ORDER:
        raise RoutingError("manifest route order differs from this helper; update nobrainer-tech-flow")
    if not isinstance(data.get("review"), dict) or data["review"].get("verdict") != "approve":
        raise RoutingError("manifest has no approve verdict")
    setups = data.get("setups")
    if not isinstance(setups, dict) or not all(
        isinstance(v, str) and re.fullmatch(r"[0-9a-f]{64}", v) for v in setups.values()
    ):
        raise RoutingError("manifest setups are not sha256 hex values")
    return data


def http_fetch(url: str, etag: str | None) -> tuple[int, bytes, str | None]:
    """GET one public file; 304 returns an empty body. Never executes remote data."""
    headers = {"Accept": "application/json", "User-Agent": "nobrainer-tech-flow-routing"}
    if etag:
        headers["If-None-Match"] = etag
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=TIMEOUT_SECONDS) as response:
            if not response.geturl().startswith("https://"):
                raise RoutingError("routing file was redirected away from https")
            body = response.read(MAX_BYTES + 1)
            new_etag = response.headers.get("ETag")
    except urllib.error.HTTPError as exc:
        if exc.code == 304:
            return 304, b"", etag
        raise RoutingError(f"HTTP {exc.code} for {url}") from None
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError) as exc:
        raise RoutingError(f"network error: {type(exc).__name__}") from None
    if len(body) > MAX_BYTES:
        raise RoutingError("routing file exceeded the size limit")
    return 200, body, new_etag


def _write_atomic(path: Path, data: bytes, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _dump(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def load_state(state_dir: Path) -> dict[str, Any]:
    """Read the cache state; any part with the wrong shape counts as an empty cache."""
    raw = _read_json(state_dir / "routing-cache" / "state.json", {})
    raw = raw if isinstance(raw, dict) else {}
    setups = raw.get("setups") if isinstance(raw.get("setups"), dict) else {}
    state: dict[str, Any] = {"setups": {k: v for k, v in setups.items() if isinstance(v, dict)}}
    if isinstance(raw.get("manifest"), dict):
        state["manifest"] = raw["manifest"]
    if raw.get("refused"):
        # Fail closed: a recorded refusal stands until an acceptable manifest arrives.
        refused = raw["refused"]
        state["refused"] = refused if isinstance(refused, dict) else {"reason": "unreadable refusal record"}
    return state


def load_cached_setup(state_dir: Path, key: str, state: dict[str, Any] | None = None
                      ) -> tuple[dict[str, Any] | None, dict[str, Any], bytes | None, str | None]:
    """Return (setup, entry, bytes, problem); the bytes are re-hashed against the recorded sha256."""
    entry = (state or load_state(state_dir))["setups"].get(key, {})
    try:
        data = (state_dir / "routing-cache" / f"{key}.json").read_bytes()
    except OSError:
        return None, {}, None, None
    if not isinstance(entry.get("sha256"), str) or hashlib.sha256(data).hexdigest() != entry["sha256"]:
        return None, {}, None, "INTEGRITY_MISMATCH: the cached setup does not match its recorded sha256"
    try:
        return validate_setup(json.loads(data), key), entry, data, None
    except (ValueError, RoutingError) as exc:
        return None, {}, None, f"CACHE_INVALID: {exc}"


def refused_report(key: str, refused: dict[str, Any]) -> dict[str, Any]:
    return {"routing": "UNKNOWN", "status": "MANIFEST_REFUSED", "key": key, "reason": refused.get("reason"),
            "manifestVersion": refused.get("manifestVersion"),
            "action": "keep the current routing; update nobrainer-tech-flow or wait for an approved manifest"}


def _report(key: str, setup: dict[str, Any] | None, entry: dict[str, Any], status: str,
            now: dt.datetime, reason: str | None = None) -> dict[str, Any]:
    if setup is None:
        return {"routing": "UNKNOWN", "status": status, "key": key, "reason": reason,
                "action": "keep the current routing"}
    stale = now > parse_time(setup["expiresAt"])
    return {"routing": "NO_RECOMMENDATION" if setup["empty"] else "AVAILABLE", "status": status, "key": key,
            "version": setup.get("version"), **({"action": NO_RECOMMENDATION} if setup["empty"] else {}),
            "expiresAt": setup["expiresAt"], "stale": stale, "refreshDue": stale,
            "integrity": entry.get("integrity", "UNVERIFIED"), "checkedOn": entry.get("checkedOn"),
            "reason": reason}


def fetch_setup(key: str, state_dir: Path, *, now: dt.datetime, force: bool = False,
                offline: bool = False, fetcher: Fetcher = http_fetch, base_url: str = BASE_URL) -> dict[str, Any]:
    """Refresh at most once per local day unless forced; fall back to the last good copy."""
    if not base_url.startswith("https://"):
        raise RoutingError("base URL must use https")
    base_url = base_url.rstrip("/") + "/"
    cache = state_dir / "routing-cache"
    state = load_state(state_dir)
    cached, entry, cached_bytes, problem = load_cached_setup(state_dir, key, state)
    refused = state.get("refused")
    today = now.astimezone().date().isoformat()

    def fallback(reason: str) -> dict[str, Any]:
        reason = "; ".join(x for x in (problem, reason) if x)
        if cached:
            return _report(key, cached, entry, "CACHED_AFTER_ERROR", now, reason)
        return _report(key, None, {}, problem.split(":", 1)[0] if problem else "UNKNOWN", now, reason)

    if offline:
        if refused:
            return refused_report(key, refused)
        return _report(key, cached, entry, "CACHED_OFFLINE", now, "offline") if cached else fallback("offline")
    if cached and not refused and not force and entry.get("checkedOn") == today:
        return _report(key, cached, entry, "CACHED_TODAY", now)

    manifest, notes = None, []
    old = cache / "manifest.json"
    try:
        etag = state.get("manifest", {}).get("etag") if old.is_file() else None
        code, body, new_etag = fetcher(base_url + "manifest.json", etag)
    except (RoutingError, OSError) as exc:
        notes.append(f"manifest unavailable: {exc}")
    else:
        try:
            manifest = validate_manifest(json.loads(old.read_bytes() if code == 304 else body))
        except (RoutingError, ValueError, OSError) as exc:
            # Fail closed: a manifest that arrived but is unapproved or not understood blocks every setup,
            # and the refusal is kept so cached, offline, policy and apply runs refuse too.
            version = None
            try:
                version = json.loads(body).get("version")
            except (ValueError, AttributeError):
                pass
            state["refused"] = {"reason": str(exc), "manifestVersion": version,
                                "at": now.isoformat(timespec="seconds")}
            _write_atomic(cache / "state.json", _dump(state))
            return refused_report(key, state["refused"])
        if code != 304:
            _write_atomic(old, body)
            state["manifest"] = {"etag": new_etag, "version": manifest.get("version")}
        if code != 304 or refused:
            state.pop("refused", None)
            _write_atomic(cache / "state.json", _dump(state))
    if manifest is None and refused:
        return refused_report(key, refused)
    expected = None
    if manifest is not None:
        expected = manifest["setups"].get(key)
        if expected is None:
            return fallback(f"manifest does not list {key}")
    url, stale_cache = base_url + f"setups/{key}.json", False
    try:
        path = cache / f"{key}.json"
        code, body, new_etag = fetcher(url, entry.get("etag") if cached else None)
        if code == 304:
            if cached_bytes is None:
                raise RoutingError("host answered 304 but no verified copy is cached")
            body = cached_bytes
            if expected is not None and hashlib.sha256(body).hexdigest() != expected:
                # The cache is older than the manifest: never fall back to it; ask once without a validator.
                stale_cache = True
                code, body, new_etag = fetcher(url, None)
                if code == 304:
                    raise RoutingError("host answered 304 to a request without If-None-Match")
        digest = hashlib.sha256(body).hexdigest()
        if expected is not None and digest != expected:
            raise RoutingError("SHA_MISMATCH: setup bytes do not match the manifest")
        setup = validate_setup(json.loads(body), key)
    except (RoutingError, ValueError, OSError) as exc:
        reason = "; ".join(notes + [str(exc)])
        if stale_cache:
            reason = "the cached setup does not match the manifest; " + reason
            return _report(key, None, {}, "SHA_MISMATCH", now, reason)
        return fallback(reason)
    changed = code != 304 or stale_cache
    if changed:
        _write_atomic(path, body)
    entry = {"etag": new_etag if changed else entry.get("etag"), "checkedOn": today,
             "checkedAt": now.isoformat(timespec="seconds"), "sha256": digest,
             "integrity": "VERIFIED" if expected else "UNVERIFIED", "version": setup.get("version")}
    state["setups"][key] = entry
    _write_atomic(cache / "state.json", _dump(state))
    return _report(key, setup, entry, "UPDATED" if changed else "NOT_MODIFIED", now, "; ".join(notes) or None)


def record(state_dir: Path, *, job: str, model: str, route: str, outcome: str, now: dt.datetime,
           duration: float | None = None, quota_error: bool = False, effort: str | None = None) -> dict[str, Any]:
    """Append one content-free ledger row: no prompts, code, file contents or secrets."""
    if job not in JOBS or route not in ROUTE_PREFIX or outcome not in OUTCOMES or effort not in (None, *EFFORTS):
        raise RoutingError("job, route, outcome or effort is not an allowed value")
    if not MODEL_RE.fullmatch(model):
        raise RoutingError("model must be a bare model id or provider/model id")
    if duration is not None and not 0 <= duration < 1_000_000:
        raise RoutingError("duration must be seconds between 0 and 1000000")
    row = {"ts": now.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
           "job": job, "model": model, "route": route, "effort": effort, "outcome": outcome,
           "durationS": None if duration is None else round(duration, 1), "quotaError": bool(quota_error)}
    path = state_dir / "routing-ledger.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def _normal_id(model: str, route: str) -> str:
    return ROUTE_PREFIX[route] + model.split("/", 1)[-1]


def _excluded(pick: dict[str, Any], excluded: set[str]) -> bool:
    names = {pick["id"], pick["id"].split("/", 1)[-1], pick["family"]}
    return any(name.lower() in excluded for name in names)


def _summary(pick: dict[str, Any], blocked: set[str]) -> dict[str, Any]:
    summary = {k: pick.get(k) for k in ("id", "route", "family", "effort")}
    older = pick.get("ifNotAvailable")
    if older is not None and not _excluded(older, blocked):
        summary["ifNotAvailable"] = _summary(older, blocked)
    return summary


def compute_policy(setup: dict[str, Any], rows: list[dict[str, Any]], excluded: list[str],
                   min_samples: int, now: dt.datetime) -> dict[str, Any]:
    """Re-order only inside each job's candidates; never add a model or touch MAIN."""
    blocked = {name.lower() for name in excluded}
    # Keyed by job, model and effort; a row without effort is None-keyed.
    stats: dict[tuple[str, str, str | None], list[int]] = {}
    for row in rows:
        if row.get("job") not in JOBS or row.get("route") not in ROUTE_PREFIX or not isinstance(row.get("model"), str):
            continue
        key = (row["job"], _normal_id(row["model"], row["route"]), row.get("effort"))
        counts = stats.setdefault(key, [0, 0, 0])
        if row.get("outcome") in ("pass", "fail"):
            counts[0 if row["outcome"] == "pass" else 1] += 1
        counts[2] += row.get("quotaError") is True
    jobs = {}
    for job in CANDIDATE_JOBS:
        entries, seen = [], set()
        picks = [(pick, _normal_id(pick["id"], pick["route"])) for pick in setup["candidates"][job]]
        for rank, (pick, nid) in enumerate(picks, start=1):
            # Candidates are distinct by id + effort; the same model can appear at two efforts.
            if (nid, pick.get("effort")) in seen or _excluded(pick, blocked):
                continue
            seen.add((nid, pick.get("effort")))
            counts = [stats.get((job, nid, pick.get("effort")), [0, 0, 0])]
            # A row without effort counts only when the model has a single effort among the candidates.
            if pick.get("effort") is not None and len({p.get("effort") for p, n in picks if n == nid}) == 1:
                counts.append(stats.get((job, nid, None), [0, 0, 0]))
            passed, failed, quota = (sum(c[i] for c in counts) for i in range(3))
            entries.append({**_summary(pick, blocked), "benchmarkRank": rank, "pass": passed, "fail": failed,
                            "quotaErrors": quota, "posteriorMean": round((passed + 1) / (passed + failed + 2), 4),
                            "eligible": passed + failed >= min_samples})
        ordered = sorted(entries, key=lambda e: -(e["posteriorMean"] if e["eligible"] else PRIOR_MEAN))
        jobs[job] = {"order": "LEARNED" if ordered != entries else "BENCHMARK", "candidates": ordered}
    bulk = setup["jobs"].get("bulk")
    return {
        "schema": "nobrainer-routing-policy/1", "key": setup["key"], "setupVersion": setup.get("version"),
        "expiresAt": setup["expiresAt"], "stale": now > parse_time(setup["expiresAt"]),
        "generatedAt": now.astimezone(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "recommendation": "NONE" if setup["empty"] else "AVAILABLE", "main": "PRESERVED",
        "minSamples": min_samples, "excluded": sorted(blocked), "jobs": jobs,
        "bulk": _summary(bulk, blocked) if bulk and not _excluded(bulk, blocked) else None,
        "fallbackChain": [_summary(p, blocked) for p in setup["subagents"] if not _excluded(p, blocked)],
        "skip": [{k: item[k] for k in SKIP_FIELDS if k in item} for item in setup.get("skip") or []
                 if isinstance(item, dict)],
    }


def read_ledger(state_dir: Path) -> tuple[list[dict[str, Any]], int]:
    rows, skipped = [], 0
    try:
        lines = (state_dir / "routing-ledger.jsonl").read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return rows, 0
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            row = None
        if isinstance(row, dict):
            rows.append(row)
        elif line.strip():
            skipped += 1
    return rows, skipped


def find_regions(lines: list[str]) -> list[tuple[str, int, int]]:
    """Marker blocks and unmarked routing sections, as (kind, first line, end line exclusive)."""
    regions, fence, start = [], False, None
    for index, line in enumerate(lines):
        if FENCE_RE.match(line):
            fence = not fence
        elif not fence and line.strip() == START:
            if start is not None:
                raise RoutingError(f"nested routing start marker at line {index + 1}")
            start = index
        elif not fence and line.strip() == END:
            if start is None:
                raise RoutingError(f"routing end marker without a start at line {index + 1}")
            regions.append(("MARKERS", start, index + 1))
            start = None
    if start is not None:
        raise RoutingError(f"routing start marker at line {start + 1} has no end marker")
    inside = {i for _, s, e in regions for i in range(s, e)}
    fence, index = False, 0
    while index < len(lines):
        line = lines[index]
        if FENCE_RE.match(line):
            fence = not fence
        match = None if fence or index in inside else SECTION_RE.match(line.rstrip("\r\n"))
        if match:
            level, end, inner = len(match.group(1)), index + 1, False
            while end < len(lines) and end not in inside:
                if FENCE_RE.match(lines[end]):
                    inner = not inner
                heading = None if inner else HEADING_RE.match(lines[end])
                if heading and len(heading.group(1)) <= level:
                    break
                end += 1
            while end > index + 1 and not lines[end - 1].strip():
                end -= 1
            regions.append(("SECTION", index, end))
            index = end
            continue
        index += 1
    return sorted(regions, key=lambda region: region[1])


def plan_block(text: str, block: str) -> tuple[str, tuple[str, int, int] | None]:
    newline = "\r\n" if "\r\n" in text else "\n"
    block = block.replace("\r\n", "\n").replace("\n", newline) + newline
    lines = text.splitlines(keepends=True)
    regions = find_regions(lines)
    if len(regions) > 1:
        where = ", ".join(f"{kind} at line {s + 1}" for kind, s, _ in regions)
        raise RoutingError(f"found {len(regions)} routing regions ({where}); keep one by hand, then rerun")
    if regions:
        _, first, end = regions[0]
        return "".join(lines[:first]) + block + "".join(lines[end:]), regions[0]
    prefix = text if not text or text.endswith(("\n", "\r")) else text + newline
    return prefix + (newline if prefix.strip() else "") + block, None


def other_routing_lines(text: str, setup: dict[str, Any], region: tuple[str, int, int] | None) -> list[str]:
    ids = {p["id"] for job in CANDIDATE_JOBS for p in setup["candidates"][job]}
    ids |= {i.split("/", 1)[-1] for i in ids}
    found = []
    for index, line in enumerate(text.splitlines(), start=1):
        if region and region[1] < index <= region[2]:
            continue
        if MODEL_LINE_RE.search(line) or any(re.search(rf"(?<![\w./-]){re.escape(i)}(?![\w.-])", line) for i in ids):
            found.append(f"line {index}: {line.strip()[:120]}")
    return found


def apply_block(path: Path, setup: dict[str, Any], choice: str, *, write: bool = False,
                confirm: str | None = None, backup_dir: Path | None = None) -> dict[str, Any]:
    if setup["empty"]:
        raise RoutingError(f"the setup is empty: {NO_RECOMMENDATION}")
    block = setup["blocks"].get(choice)
    if block is None:
        raise RoutingError(f"this setup has no {choice} block; use router or plain")
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise RoutingError("target must be a regular file; pass the resolved path")
    before = path.read_bytes() if path.exists() else b""
    text = before.decode("utf-8")
    after_text, region = plan_block(text, block)
    after = after_text.encode("utf-8")
    preview_id = hashlib.sha256(before + b"\0" + after).hexdigest()[:16]
    where = f"{region[0]} lines {region[1] + 1}-{region[2]}" if region else "NONE (append)"
    result = {"target": str(path), "region": where,
              "change": "NO_CHANGE" if before == after else "PENDING_CONFIRMATION", "previewId": preview_id,
              "otherRoutingLines": other_routing_lines(text, setup, region),
              "diff": "".join(difflib.unified_diff(text.splitlines(keepends=True), after_text.splitlines(keepends=True),
                                                  f"{path.name} (before)", f"{path.name} (after)"))}
    if not write or before == after:
        return result
    if confirm != preview_id:
        raise RoutingError("file or setup changed since the confirmed preview; preview again")
    if backup_dir is None:
        raise RoutingError("a write needs a backup directory")
    backup = None
    if path.exists():
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / f"{path.name}.{dt.datetime.now(dt.timezone.utc):%Y%m%dT%H%M%S%fZ}.bak"
        shutil.copy2(path, backup)
    _write_atomic(path, after, stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644)
    # Compare bytes: text-mode reads would turn CRLF into LF and fail every CRLF file.
    written_bytes = path.read_bytes()
    lines = written_bytes.decode("utf-8").splitlines(keepends=True)
    regions = find_regions(lines)
    newline = "\r\n" if b"\r\n" in written_bytes else "\n"
    ok = written_bytes == after and len(regions) == 1 and regions[0][0] == "MARKERS" and "".join(
        lines[regions[0][1]:regions[0][2]]).rstrip("\r\n") == block.replace("\n", newline)
    result.update(change="WRITTEN", backup=str(backup) if backup else None, readback="OK" if ok else "FAILED")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--state-dir", type=Path, default=Path(".nobrainer"))
    sub = parser.add_subparsers(dest="command", required=True)
    commands = {name: sub.add_parser(name) for name in ("key", "fetch", "record", "policy", "apply")}
    for name in ("key", "fetch", "policy", "apply"):
        commands[name].add_argument("--routes", required=True, help="comma-separated reachable routes")
        commands[name].add_argument("--fast", action="store_true", help="time per task matters")
        commands[name].add_argument("--budget", action="store_true", help="small budget")
    commands["fetch"].add_argument("--force", action="store_true", help="refresh now (on request)")
    commands["fetch"].add_argument("--offline", action="store_true")
    commands["record"].add_argument("--job", choices=JOBS, required=True)
    commands["record"].add_argument("--model", required=True)
    commands["record"].add_argument("--route", choices=ROUTE_ORDER, required=True)
    commands["record"].add_argument("--outcome", choices=OUTCOMES, required=True)
    commands["record"].add_argument("--effort", choices=EFFORTS)
    commands["record"].add_argument("--duration", type=float)
    commands["record"].add_argument("--quota-error", action="store_true")
    commands["policy"].add_argument("--exclude", action="append", default=[],
                                    help="model id or family the user excluded")
    commands["policy"].add_argument("--clear-excludes", action="store_true")
    commands["policy"].add_argument("--min-samples", type=int, default=DEFAULT_MIN_SAMPLES)
    commands["apply"].add_argument("--file", type=Path, required=True)
    commands["apply"].add_argument("--block", choices=BLOCKS, required=True)
    commands["apply"].add_argument("--write", action="store_true")
    commands["apply"].add_argument("--confirm")
    args = parser.parse_args(argv)
    now = dt.datetime.now().astimezone()
    try:
        if args.command == "record":
            print(json.dumps(record(args.state_dir, job=args.job, model=args.model, route=args.route,
                                    outcome=args.outcome, now=now, duration=args.duration,
                                    quota_error=args.quota_error, effort=args.effort), sort_keys=True))
            return 0
        key = build_key(args.routes.split(","), args.fast, args.budget)
        if args.command == "key":
            print(key)
            return 0
        if args.command == "fetch":
            result = fetch_setup(key, args.state_dir, now=now, force=args.force, offline=args.offline)
            print(json.dumps(result, indent=2, sort_keys=True))
            # 3 means keep the current routing: no usable setup, or one with no recommendation.
            return 0 if result["routing"] == "AVAILABLE" else 3
        state = load_state(args.state_dir)
        if state.get("refused"):
            print(json.dumps(refused_report(key, state["refused"])))
            return 3
        setup, _, _, problem = load_cached_setup(args.state_dir, key, state)
        if setup is None:
            print(json.dumps({"routing": "UNKNOWN", "key": key, "reason": problem,
                              "action": "run fetch first; keep the current routing"}))
            return 3
        if setup["empty"]:
            # Never write a block or a new policy from an empty setup; any previous policy file stays as it was.
            print(json.dumps({"routing": "NO_RECOMMENDATION", "key": key, "action": NO_RECOMMENDATION}))
            return 3
        if args.command == "policy":
            if args.min_samples < 1:
                raise RoutingError("--min-samples must be at least 1")
            path = args.state_dir / "routing-policy.json"
            previous = _read_json(path, {})
            kept = previous.get("excluded") if isinstance(previous, dict) and not args.clear_excludes else []
            excluded = [x for x in kept if isinstance(x, str)] if isinstance(kept, list) else []
            excluded += args.exclude
            rows, skipped = read_ledger(args.state_dir)
            policy = compute_policy(setup, rows, excluded, args.min_samples, now)
            policy.update(ledgerRows=len(rows), skippedRows=skipped)
            _write_atomic(path, _dump(policy))
            print(json.dumps(policy, indent=2, sort_keys=True))
            return 0
        result = apply_block(args.file, setup, args.block, write=args.write, confirm=args.confirm,
                             backup_dir=args.state_dir / "routing-backups")
    except (RoutingError, OSError, UnicodeDecodeError) as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    print(f"ROUTING_KEY: {key}\nSETUP_VERSION: {setup.get('version')}"
          f"{' (STALE: refresh due)' if now > parse_time(setup['expiresAt']) else ''}")
    for label, field in (("TARGET", "target"), ("REGION", "region")):
        print(f"{label}: {result[field]}")
    print(result["diff"] or "(no difference)", end="" if result["diff"].endswith("\n") else "\n")
    print("OTHER_ROUTING_LINES: " + ("NONE" if not result["otherRoutingLines"] else "review by hand, not changed"))
    for line in result["otherRoutingLines"]:
        print(f"  {line}")
    print(f"CHANGE: {result['change']}")
    if result["change"] == "PENDING_CONFIRMATION":
        print(f"PREVIEW_ID: {result['previewId']}")
        print(f"NEXT: after the user confirms, rerun with --write --confirm {result['previewId']}")
    if result["change"] == "WRITTEN":
        print(f"BACKUP: {result['backup'] or 'NONE (new file)'}\nREADBACK: {result['readback']}")
        return 0 if result["readback"] == "OK" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
