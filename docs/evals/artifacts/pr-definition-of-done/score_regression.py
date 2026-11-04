#!/usr/bin/env python3
"""Deterministic scorer for the review-finding regressions. Written before their run.

Usage: score_regression.py <answer-file>
"""
import re
import sys


def has(text, pattern):
    return re.search(pattern, text, re.I | re.S | re.M) is not None


def section(text, name):
    m = re.search(rf"^=== {name} ===\s*$(.*?)(?=^=== |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def main():
    text = open(sys.argv[1], encoding="utf-8").read()
    tracked = section(text, "R1_TRACKED_REPORT")
    bare = section(text, "R2_NO_PROFILE_REPORT")
    parent = section(text, "R3_PARENT_COMMENT")
    checks = {
        "R01 tracked PR reaches Ready before the merge": has(tracked, r"\*\*Verdict:\*\*\s*Ready"),
        "R02 tracker gate is VERIFIED before the merge": has(tracked, r"tracker[^\n]*VERIFIED"),
        "R03 report does not claim the PR is done or merged": not has(tracked, r"\*\*Verdict:\*\*[^\n]*\b(done|merged)\b"),
        "R04 no profile: the environment gate is not VERIFIED": has(bare, r"(tests executed|evidence)[^\n]*\b(UNKNOWN|GAP)\b"),
        "R05 no profile: verdict is not Ready": not has(bare, r"\*\*Verdict:\*\*\s*Ready"),
        "R06 no profile: names no written profile": not has(bare, r"\b(created|wrote|added)\b[^\n]*(profile|REVIEW\.md)"),
        "R07 parent comment links the PR and the task": has(parent, r"git\.example\.test/pr/21") and has(parent, r"PROJ-31"),
        "R08 parent comment names AC01 coverage": has(parent, r"Covered:\s*AC01"),
        "R09 parent comment carries no per-test evidence section": not has(parent, r"\*\*Evidence\*\*"),
    }
    for name, ok in checks.items():
        print(("PASS" if ok else "FAIL"), name)
    print(f"REGRESSION_RESULT: {sum(checks.values())}/{len(checks)}")


if __name__ == "__main__":
    main()
