#!/usr/bin/env python3
"""Keep an npm release at a stable profile path, then use the existing reversible installer."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    spec = importlib.util.spec_from_file_location("_npm_" + name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    installer = load("install")
    args = installer.parse_args()
    if (args.apply or args.undo) and (ROOT / ".git").exists():
        print("ERROR: use scripts/install.py from a Git checkout; npm installation expects the packed release.", file=sys.stderr)
        return 2
    metadata = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    version = metadata["version"]
    # --home chooses storage and the client profile without changing the caller's HOME.
    home = (args.home or Path.home()).expanduser().resolve()
    storage = home / ".nobrainer-tech-flow" / "npm"
    target = storage / version
    if any(p.is_symlink() for p in (storage, *storage.parents)):
        print("ERROR: npm release storage must not pass through a symlink.", file=sys.stderr)
        return 3
    low = load("install_skills")
    source_manifest = low.tree_manifest(ROOT)
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_dir() or low.tree_manifest(target) != source_manifest:
            print(f"PRESERVED: release storage is different or untrusted: {target}", file=sys.stderr)
            return 3
    elif args.undo:
        print("ERROR: retained npm release is missing; preserve the client and inspect its setup record.", file=sys.stderr)
        return 3
    elif not args.apply:
        print("NPM_SOURCE: release files will be copied to a stable profile directory on --apply.")
        return installer.main()
    else:
        storage.mkdir(parents=True, exist_ok=True)
        if storage.resolve() != storage or any(p.is_symlink() for p in (storage, *storage.parents)):
            print("ERROR: npm release storage must not pass through a symlink.", file=sys.stderr)
            return 3
        _, expected, stage = low.stage_and_publish_copy(ROOT, target)
        if low.tree_manifest(target) != expected:
            raise RuntimeError("npm release copy failed its readback")
        stage.rmdir()
    print(f"NPM_SOURCE: retained release {version}; client links use this stable source.")
    run = subprocess.run([sys.executable, str(target / "scripts" / "install.py"), *sys.argv[1:]],
                         env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, check=False)
    if args.undo and run.returncode == 0:
        print("NPM_CACHE: retained release files remain available for other profiles and future setup.")
    return run.returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: npm installer stopped: {exc}", file=sys.stderr)
        raise SystemExit(2)
