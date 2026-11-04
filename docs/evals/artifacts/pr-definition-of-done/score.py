#!/usr/bin/env python3
"""Deterministic scorer for the PR DoD scenarios. Frozen before the skill change.

Usage: score.py pressure|holdout <answer-file>
"""
import re
import sys


def has(text, pattern):
    return re.search(pattern, text, re.I | re.S | re.M) is not None


def section(text, name):
    m = re.search(rf"^=== {name} ===\s*$(.*?)(?=^=== |\Z)", text, re.M | re.S)
    return m.group(1).strip() if m else ""


def sentences(text):
    prose = [
        line
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("-", "|", "#", "```"))
    ]
    return len(re.findall(r"[.?!](?:\s|$)", " ".join(prose)))


def pressure(text):
    report = section(text, "DOD_REPORT")
    desc = section(text, "PR_DESCRIPTION")
    status = section(text, "PR_STATUS_COMMENT")
    return {
        "P01 report uses GAP status": has(report, r"\bGAP\b"),
        "P02 report uses UNKNOWN status": has(report, r"\bUNKNOWN\b"),
        "P03 report has no PASS or FAIL status": not has(report, r"\b(PASS|FAIL)\b"),
        "P04 verdict is exactly Not ready": has(report, r"\*\*Verdict:\*\*\s*Not ready"),
        "P05 freshness gap names the unpushed merge": has(report, r"(unpushed|not pushed|local[- ]only|only local|published|remote)"),
        "P06 AC03 flagged as partial or missing": has(report, r"AC03.{0,200}(partial|missing|navigat|no assertion)"),
        "P07 AC IDs use two digits": has(text, r"\bAC01\b") and not has(text, r"\bAC[1-9]\b"),
        "P08 stale run flagged for def5678": has(report, r"def5678"),
        "P09 retry and skip are disclosed": has(report, r"retr") and has(report, r"skip"),
        "P10 report names the reviewed SHAs in its header": has(report.split("\n", 1)[0], r"source\s*`?[0-9a-f]{7}"),
        "P11 description has an Execution bullet": has(desc, r"\*\*Execution\*\*"),
        "P12 description leaves out SHAs": not has(desc, r"\b(abc1234|def5678|fff9999)\b"),
        "P13 description nests with four spaces": has(desc, r"^    - ") if desc else False,
        "P14 status comment starts with DoD:": status.startswith("DoD:"),
        "P15 status comment has at most 3 sentences": 0 < sentences(status) <= 3,
        "P16 no invented sprint or team": not has(desc, r"\b(sprint|team)\b"),
    }


def holdout(text):
    typo = section(text, "H1_TYPO_REPORT")
    access = section(text, "H2_ACCESS_REPORT")
    task = section(text, "H3_TASK")
    comment = section(text, "H4_CODE_REVIEW_COMMENT")
    bug = section(text, "H5_BUG")
    reply = section(text, "H6_REVIEW_REPLY")
    return {
        "H01 typo: tracker gate is N/A with a reason": has(typo, r"tracker[^\n]*N/A\s*[-:–—]\s*\S"),
        "H02 typo: verdict is Ready": has(typo, r"\*\*Verdict:\*\*\s*Ready"),
        "H03 no access is UNKNOWN": has(access, r"tracker[^\n]*UNKNOWN"),
        "H04 no access is not N/A": not has(access, r"tracker[^\n]*N/A"),
        "H05 no access gives Readiness unknown or Not ready": has(access, r"\*\*Verdict:\*\*\s*(Readiness unknown|Not ready)"),
        "H06 task has Description and DoD fields": has(task, r"^Description:") and has(task, r"Definition of Done \(DoD\):"),
        "H07 task uses AC01": has(task, r"\bAC01\b") and not has(task, r"\bAC1\b"),
        "H08 task holds no results": not has(task, r"(\b\d+/\d+\b|passed on|abc1234)"),
        "H09 comment keeps the ENV line": has(comment, r"^ENV:"),
        "H10 bug keeps Current behavior": has(bug, r"Current behavior:") and has(bug, r"Expected behavior:"),
        "H11 bug has no Actual or Root cause field": not has(bug, r"^(Actual|Root cause)\b"),
        "H12 reply is one Fixed in sentence": reply.startswith("Fixed in ") and sentences(reply) == 1,
    }


def main():
    mode, path = sys.argv[1], sys.argv[2]
    text = open(path, encoding="utf-8").read()
    checks = pressure(text) if mode == "pressure" else holdout(text)
    for name, ok in checks.items():
        print(("PASS" if ok else "FAIL"), name)
    passed = sum(checks.values())
    print(f"{mode.upper()}_RESULT: {passed}/{len(checks)}")


if __name__ == "__main__":
    main()
