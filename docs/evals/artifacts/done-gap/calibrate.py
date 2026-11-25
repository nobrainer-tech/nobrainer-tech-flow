"""Calibrate the done-gap tasks: hidden check fails on base + overlay, passes with the reference.

Usage: python3 calibrate.py WORK_DIR [D1,D2,...]
Prints one line per task and exits 1 if any task fails calibration.
"""
import sys
import tempfile
from pathlib import Path

import common


def main() -> int:
    work = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(tempfile.mkdtemp())
    tasks = sys.argv[2].split(",") if len(sys.argv) > 2 else common.TASKS
    bad = 0
    for task in tasks:
        base, ref = work / task / "base", work / task / "ref"
        common.build(task, base)
        base_ok = common.check(task, base, work / task / "base.txt")
        common.build(task, ref, with_ref=True)
        ref_ok = all(common.check(task, ref, work / task / f"ref{i}.txt") for i in range(3))
        ok = (not base_ok) and ref_ok
        bad += not ok
        print(f"{task}\tbase_passes={base_ok}\tref_passes_3x={ref_ok}\t{'OK' if ok else 'FAIL'}", flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
