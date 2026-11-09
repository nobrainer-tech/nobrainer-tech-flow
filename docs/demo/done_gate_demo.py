#!/usr/bin/env python3
"""Record and render the README demo: the done gate catching a false "done".

Two steps, both reproducible with the Python standard library only:

    python3 docs/demo/done_gate_demo.py capture   # calls the live MCP server
    python3 docs/demo/done_gate_demo.py render    # writes assets/done-gate-demo*.svg

`capture` runs one task against https://mcp.nobrainer.tech/mcp (free, no sign-in,
read-only tools) and saves every request and response in
docs/demo/done-gate-transcript.json. Signed tokens are shortened to `nbf1.<token>`
and `nbr1.<receipt>`; everything else is stored as the server returned it.

`render` reads only that transcript, so both SVGs (desktop and phone width) can be
rebuilt offline. Every tool line comes from a recorded request or response; the two
"agent" lines are the scenario the calls test.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRANSCRIPT = ROOT / "docs" / "demo" / "done-gate-transcript.json"
SVG = ROOT / "assets" / "done-gate-demo.svg"
NARROW_SVG = ROOT / "assets" / "done-gate-demo-narrow.svg"  # phones: <picture> max-width 600px
ENDPOINT = "https://mcp.nobrainer.tech/mcp"
PROTOCOL = "2025-06-18"

FAILING_RUN = (
    "tests/test_dates.py ....F\n"
    "FAILED tests/test_dates.py::test_feb_30 - DID NOT RAISE ValueError\n"
    "========================= 1 failed, 4 passed in 0.21s ========================="
)
PASSING_RUN = (
    "tests/test_dates.py .....\n"
    "============================== 5 passed in 0.18s ==============================="
)

# The agent's false claim: exit code 0 and "all tests pass", over a log that says otherwise.
STEPS = [
    ("start_flow_task", {
        "outcome": "parse('2026-02-30') raises ValueError for library users",
        "dod": [{"text": "new unit test for 2026-02-30 passes", "proof": "test"}],
    }),
    ("check_flow_evidence", {
        "evidence": [{"item": "AC01", "kind": "test", "cmd": "pytest -q", "exit": 0,
                      "out": FAILING_RUN}],
    }),
    ("check_flow_done", {}),
    ("check_flow_evidence", {
        "evidence": [{"item": "AC01", "kind": "test", "cmd": "pytest -q", "exit": 0,
                      "out": PASSING_RUN, "passed": 5, "failed": 0}],
    }),
    ("check_flow_done", {}),
    ("draft_flow_handoff", {}),
]


def rpc(method: str, params: dict, ident: int) -> dict:
    body = json.dumps({"jsonrpc": "2.0", "id": ident, "method": method, "params": params}).encode()
    request = urllib.request.Request(ENDPOINT, data=body, method="POST", headers={
        "content-type": "application/json",
        "accept": "application/json, text/event-stream",
        "mcp-protocol-version": PROTOCOL,
        "user-agent": "nobrainer-tech-flow-readme-demo",
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        reply = json.loads(response.read())
    if "error" in reply:
        raise SystemExit(f"{method} failed: {reply['error']}")
    return reply["result"]


def shorten(value):
    if isinstance(value, str):
        value = re.sub(r"\bnbf1\.[A-Za-z0-9_\-]+", "nbf1.<token>", value)
        return re.sub(r"\bnbr1\.[A-Za-z0-9_\-]+", "nbr1.<receipt>", value)
    if isinstance(value, list):
        return [shorten(item) for item in value]
    if isinstance(value, dict):
        return {key: shorten(item) for key, item in value.items()}
    return value


def capture() -> None:
    init = rpc("initialize", {"protocolVersion": PROTOCOL, "capabilities": {},
                              "clientInfo": {"name": "readme-demo", "version": "1.0.0"}}, 1)
    token = receipt = None
    calls = []
    for ident, (tool, args) in enumerate(STEPS, start=2):
        args = dict(args)
        if tool in ("check_flow_evidence", "check_flow_done"):
            args["token"] = token
        if tool == "draft_flow_handoff":
            args["receipt"] = receipt
        result = rpc("tools/call", {"name": tool, "arguments": args}, ident)
        data = json.loads(result["content"][0]["text"])
        token = data.get("token", token)
        receipt = data.get("receipt", receipt)
        calls.append({"tool": tool, "arguments": shorten(args), "result": shorten(data)})
    TRANSCRIPT.parent.mkdir(parents=True, exist_ok=True)
    TRANSCRIPT.write_text(json.dumps({
        "endpoint": ENDPOINT,
        "protocol": PROTOCOL,
        "server": init["serverInfo"]["version"],
        "captured": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "calls": calls,
    }, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {TRANSCRIPT.relative_to(ROOT)}")


# ---------------------------------------------------------------- rendering

PAD, LINE, FONT = 28, 25, 15.5
TOP = 50  # first baseline sits one line below this, under the title bar
STEP = 0.3  # seconds each printed line takes
INK, MUTED, COBALT, VERMILION, PAPER, RULE = (
    "#151515", "#5f5a52", "#2f55d4", "#b8380d", "#fbf8f3", "#e3dccf")
LOOP_HOLD = 5.0  # seconds the finished log stays on screen before the loop restarts


def lines_from(transcript: dict) -> list[tuple[str, list[tuple[str, str]], float]]:
    """Return (kind, [(css class, text)], pause before the line) from recorded results."""
    calls = {i: c for i, c in enumerate(transcript["calls"])}
    start, bad, not_done, good, done = (calls[i]["result"] for i in range(5))
    item = start["items"][0]
    bad_result = bad["results"][0]
    missing = not_done["missing"][0]
    good_result = good["results"][0]
    out = []

    def add(kind, parts, pause=0.35):
        out.append((kind, parts, pause))

    add("say", [("muted", "agent  "), ("ink", "Fixed the date parser. All tests pass. Done.")], 0.6)
    add("gap", [], 0.2)
    add("cmd", [("prompt", "> "), ("cmd", "start_flow_task"),
                ("muted", ' DoD: "new unit test passes"')], 0.9)
    add("out", [("muted", "  path "), ("ink", start["path"]),
                ("muted", f"  {item['id']} "), ("ink", f"{item['proof']}, {item['level']}"),
                ("muted", "  next "), ("ink", start["next"]["stage"])])
    add("gap", [], 0.2)
    add("cmd", [("prompt", "> "), ("cmd", "check_flow_evidence"),
                ("muted", f" {item['id']} pytest -q exit=0, log:")], 0.9)
    add("log", [("muted", "    FAILED tests/test_dates.py::test_feb_30")], 0.15)
    add("log", [("muted", "    ===== 1 failed, 4 passed in 0.21s =====")], 0.15)
    verdict = [("muted", f"  {bad_result['item']} "), ("bad", bad_result["verdict"])]
    if bad_result.get("code"):
        verdict.append(("muted", f"  {bad_result['code']}"))
    add("out", verdict, 0.6)
    if bad_result.get("why"):
        add("out", [("muted", "  " + bad_result["why"].split(": ", 1)[-1])])
    add("gap", [], 0.2)
    add("cmd", [("prompt", "> "), ("cmd", "check_flow_done")], 0.9)
    add("out", [("bad", f"  {not_done['verdict']}"), ("muted", f"  missing {missing['item']}")], 0.6)
    add("out", [("muted", f"  needs {missing['need']}")])
    add("gap", [], 0.2)
    add("say", [("muted", "agent  "), ("ink", "Fixed the leap-day check. Running the tests again.")], 0.9)
    add("cmd", [("prompt", "> "), ("cmd", "check_flow_evidence"),
                ("muted", f" {item['id']} pytest -q: 5 passed")], 1.0)
    add("out", [("muted", f"  {good_result['item']} "), ("good", good_result["verdict"]),
                ("muted", f"  {good_result['level']}  digest {good_result['digest']}")], 0.6)
    add("cmd", [("prompt", "> "), ("cmd", "check_flow_done")], 1.0)
    add("out", [("good", f"  {done['verdict']}"), ("muted", "  receipt nbr1.<receipt>  next "),
                ("ink", done.get("next", "draft_flow_handoff"))], 0.6)
    return out


def wrap(parts: list[tuple[str, str]], limit: int) -> list[list[tuple[str, str]]]:
    """Split one styled line at spaces so no row exceeds `limit` characters."""
    chars = [(css, ch) for css, chunk in parts for ch in chunk]
    rows = []
    while len(chars) > limit:
        cut = max(i for i in range(6, limit + 1) if chars[i][1] == " ")
        rows.append(chars[:cut])
        chars = [("muted", " ")] * 4 + chars[cut + 1:]
    rows.append(chars)
    grouped = []
    for row in rows:
        spans: list[tuple[str, str]] = []
        for css, ch in row:
            if spans and spans[-1][0] == css:
                spans[-1] = (css, spans[-1][1] + ch)
            else:
                spans.append((css, ch))
        grouped.append(spans)
    return grouped


def render_variant(transcript: dict, path: Path, width: int, limit: int) -> None:
    lines = []
    for kind, parts, pause in lines_from(transcript):
        for n, row in enumerate(wrap(parts, limit) if parts else [[]]):
            lines.append((row, pause if n == 0 else 0.0))
    caption = [f"> lines: live calls to {transcript['endpoint']}",
               f"(server {transcript['server']}, {transcript['captured'][:10]}), shortened.",
               "agent lines: the scenario."]
    caption = [" ".join(caption)] if width >= 800 else [caption[0], " ".join(caption[1:])]
    height = TOP + LINE * len(lines) + 32 + 18 * len(caption)
    t, rows, keyframes = 0.4, [], []
    total = sum(pause for _, pause in lines) + STEP * len(lines) + 1.0 + LOOP_HOLD
    for index, (parts, pause) in enumerate(lines):
        t += pause
        if not parts:
            continue
        text = "".join(f'<tspan class="{css}">{html.escape(chunk)}</tspan>' for css, chunk in parts)
        appear = t / total * 100
        keyframes.append(
            f"@keyframes l{index}{{0%,{appear:.2f}%{{opacity:0}}"
            f"{min(appear + 1.2, 97):.2f}%,97%{{opacity:1}}100%{{opacity:0}}}}"
            f".l{index}{{animation:l{index} {total:.1f}s linear infinite}}")
        rows.append(f'<text class="l{index}" x="{PAD}" y="{TOP + LINE * (index + 1)}" '
                    f'xml:space="preserve">{text}</text>')
        t += STEP
    captions = "\n".join(
        f'<text class="cap" x="{PAD}" y="{height - 16 - 18 * (len(caption) - 1 - n)}">{html.escape(c)}</text>'
        for n, c in enumerate(caption))
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">
<title id="title">nobrainer-tech-flow done gate demo</title>
<desc id="desc">An agent says all tests pass. The Flow MCP server reads the test log, rejects the claim and answers NOT_DONE. After a real fix and a passing run it answers DONE.</desc>
<style>
text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-size:{FONT}px;fill:{INK}}}
.muted{{fill:{MUTED}}}.ink{{fill:{INK}}}.prompt{{fill:{COBALT};font-weight:700}}.cmd{{fill:{COBALT};font-weight:700}}
.bad{{fill:{VERMILION};font-weight:700}}.good{{fill:{COBALT};font-weight:700}}
.cap{{font-family:system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;font-size:12.5px;fill:{MUTED}}}
.ttl{{font-family:system-ui,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif;font-size:13.5px;fill:{MUTED};font-weight:600}}
{"".join(keyframes)}
@media (prefers-reduced-motion:reduce){{text{{animation:none!important;opacity:1!important}}}}
</style>
<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="14" fill="{PAPER}" stroke="{RULE}" stroke-width="2"/>
<path d="M1 44H{width - 1}" stroke="{RULE}" stroke-width="2"/>
<circle cx="26" cy="23" r="6" fill="#f04a14"/><circle cx="46" cy="23" r="6" fill="{RULE}"/><circle cx="66" cy="23" r="6" fill="{RULE}"/>
<text class="ttl" x="{width // 2 + 20}" y="28" text-anchor="middle">done gate · mcp.nobrainer.tech</text>
{chr(10).join(rows)}
{captions}
</svg>
"""
    path.write_text(svg, encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)} ({len(svg)} bytes, {total:.1f}s loop)")


def render() -> None:
    transcript = json.loads(TRANSCRIPT.read_text(encoding="utf-8"))
    render_variant(transcript, SVG, 860, 86)
    render_variant(transcript, NARROW_SVG, 500, 48)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=("capture", "render"))
    step = parser.parse_args().step
    capture() if step == "capture" else render()
    return 0


if __name__ == "__main__":
    sys.exit(main())
