"""Count opening text, silent tool stretches, tokens and words in Claude Code stream-json runs.

Usage: python3 score.py RUN.jsonl [RUN.jsonl ...]
Prints one tab-separated row per run: name, M1, M2, M3, M4, tool calls, final text.
"""
import json
import sys
from pathlib import Path


def score(path: Path) -> dict:
    blocks = []
    output_tokens = None
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                kind = block.get("type")
                if kind == "text" and block.get("text", "").strip():
                    blocks.append(("text", block["text"].strip()))
                elif kind == "tool_use":
                    blocks.append(("tool", block.get("name", "")))
        elif event.get("type") == "result":
            output_tokens = (event.get("usage") or {}).get("output_tokens")
    first_tool = next((i for i, b in enumerate(blocks) if b[0] == "tool"), None)
    opening = int(first_tool is not None and any(b[0] == "text" for b in blocks[:first_tool]))
    longest = run = 0
    for kind, _ in blocks:
        run = run + 1 if kind == "tool" else 0
        longest = max(longest, run)
    texts = [t for k, t in blocks if k == "text"]
    return {
        "name": path.stem,
        "m1": opening,
        "m2": longest,
        "m3": output_tokens,
        "m4": sum(len(t.split()) for t in texts),
        "tools": sum(1 for k, _ in blocks if k == "tool"),
        "final": texts[-1].replace("\n", " ")[:300] if texts else "",
    }


def main() -> int:
    for arg in sys.argv[1:]:
        row = score(Path(arg))
        print("\t".join(str(row[k]) for k in ("name", "m1", "m2", "m3", "m4", "tools", "final")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
