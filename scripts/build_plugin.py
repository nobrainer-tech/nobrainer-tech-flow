#!/usr/bin/env python3
"""Build a hook-free portable plugin ZIP from the same eighteen canonical skills."""
import argparse
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ("skills", "scripts", "adapters", "docs", "assets")
ROOT_FILES = ("plugin.json", "README.md", "LICENSE", "SECURITY.md", "package.json")
EXCLUDED = {"__pycache__", ".DS_Store", "node_modules"}
ARCHIVES = {".zip", ".tgz", ".tar", ".gz"}


def build(output: Path) -> None:
    version = json.loads((ROOT / "plugin.json").read_text())["version"]
    files = []
    for directory in DIRECTORIES:
        for path in sorted((ROOT / directory).rglob("*")):
            if path.is_symlink():
                raise ValueError("plugin source must not contain symlinks: " + str(path))
            if path.is_file() and not set(path.parts) & EXCLUDED and path.suffix not in ARCHIVES | {".pyc"}:
                if directory == "docs" and path.parent not in (ROOT / "docs", ROOT / "docs/releases"):
                    continue
                if directory == "assets" and path.suffix not in (".svg", ".png"):
                    continue
                files.append(path)
    files.extend(ROOT / name for name in ROOT_FILES)
    skills = list((ROOT / "skills").glob("*/SKILL.md"))
    if len(skills) != 18:
        raise ValueError("plugin requires the exact eighteen-module portfolio")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.is_symlink():
        raise ValueError("output already exists; choose a fresh path")
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
        overlay = json.loads((ROOT / ".codex-plugin/plugin.json").read_text())
        archive.writestr(".codex-plugin/plugin.json", json.dumps(overlay, indent=2) + "\n")
        claude = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        claude.pop("hooks", None)
        archive.writestr(".claude-plugin/plugin.json", json.dumps(claude, indent=2) + "\n")
    print(f"PLUGIN_READY: {output.name}; version={version}; skills=18; hooks=none; bytes={output.stat().st_size}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output)
