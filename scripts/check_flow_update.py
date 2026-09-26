#!/usr/bin/env python3
"""Repository wrapper for the installed skill's nobrainer-tech-flow update checker."""

from __future__ import annotations

import sys
from pathlib import Path


_HELPER_DIR = Path(__file__).resolve().parents[1] / "skills" / "nobrainer-tech-flow" / "scripts"
sys.path.insert(0, str(_HELPER_DIR))

# Keep the historical import surface available to tests and repository callers.
from check_flow_update import *  # noqa: E402,F401,F403


if __name__ == "__main__":
    raise SystemExit(main())
