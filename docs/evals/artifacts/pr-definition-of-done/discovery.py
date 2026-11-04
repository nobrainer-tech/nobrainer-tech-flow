#!/usr/bin/env python3
"""Ask a real Claude Code client each frozen request and record every skill it loads.

Usage: discovery.py <plugin-dir> <output.json> [model]

Each run starts in an empty directory with only the given plugin. Skill is the only
tool approved, and other tools are refused under the default permission mode, so nothing
changes on disk. A run that loads no skill records an empty list.
"""
import concurrent.futures
import json
import subprocess
import sys
import tempfile

SHOULD_LOAD_REVIEW = [
    "Give me the DoD for PR #12.",
    "Is PR #12 ready to merge?",
    "CI is green on my pull request, can I merge it?",
    "Run the definition of done on this pull request.",
    "Daj DoD dla tego PR.",
    "Czy ten PR jest gotowy do merge?",
    "Sprawdz definition of done dla PR 12.",
]
SHOULD_NOT_LOAD_REVIEW = {
    "Write a user story with a DoD for a login page.": "nobrainer-writing",
    "Write the PR description for my branch.": "nobrainer-writing",
    "Napisz zgloszenie buga: koszyk pokazuje zla ilosc.": "nobrainer-writing",
    "Production returns 500 since this morning, find out why.": "nobrainer-rca",
    "Shorten this blog paragraph and fix the tone.": "nobrainer-writing",
}


def loaded_skills(request, plugin_dir, model):
    with tempfile.TemporaryDirectory() as cwd:
        result = subprocess.run(
            [
                "claude", "-p", request, "--plugin-dir", plugin_dir, "--model", model,
                "--setting-sources", "project", "--permission-mode", "default",
                "--allowedTools", "Skill", "--max-turns", "5",
                "--output-format", "stream-json", "--verbose",
            ],
            cwd=cwd, capture_output=True, text=True, timeout=240, check=False,
        )
    skills = []
    for line in result.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "Skill":
                skills.append(str(block.get("input", {}).get("skill", "")).split(":")[-1])
    if not result.stdout.strip():
        raise RuntimeError(f"no client output: {result.stderr[-160:]}")
    return skills


def main():
    plugin_dir, output = sys.argv[1], sys.argv[2]
    model = sys.argv[3] if len(sys.argv) > 3 else "sonnet"
    requests = SHOULD_LOAD_REVIEW + list(SHOULD_NOT_LOAD_REVIEW)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        loaded = list(pool.map(lambda r: loaded_skills(r, plugin_dir, model), requests))
    rows = dict(zip(requests, loaded))
    hits = sum("nobrainer-review" in rows[r] for r in SHOULD_LOAD_REVIEW)
    clean = sum("nobrainer-review" not in rows[r] for r in SHOULD_NOT_LOAD_REVIEW)
    exact = sum(want in rows[r] for r, want in SHOULD_NOT_LOAD_REVIEW.items())
    summary = {
        "DISCOVERY_HITS": f"{hits}/{len(SHOULD_LOAD_REVIEW)}",
        "NON_TRIGGER_CLEAN": f"{clean}/{len(SHOULD_NOT_LOAD_REVIEW)}",
        "NON_TRIGGER_EXACT_SKILL": f"{exact}/{len(SHOULD_NOT_LOAD_REVIEW)}",
        "rows": rows,
    }
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, indent=1, ensure_ascii=False)
    print(json.dumps(summary, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
