#!/usr/bin/env python3
"""Export the Claude-directory copy of nobrainer-tech-flow from a canonical release ZIP.

The copy (nobrainer-tech/nobrainer-tech-flow-plugin) is what the Claude plugin directory
scans. It keeps, byte for byte, every file of the release ZIP's skills/ that the directory
accepts from an unverified organization (Markdown, plain text, JSON, YAML, images) and no
script, so it omits skills/*/scripts/ and skills/nobrainer-tech-flow/VERSION (a file
without an extension that is not a license, a readme or .gitignore; the manifests carry the
version). Both rules come from verify_native_export.file_problem. From the ZIP it also takes LICENSE, SECURITY.md,
docs/CHAT_PLUGINS.md and docs/PRIVACY.md. From the current copy it keeps the files only
the copy has (README.md, AGENTS.md, the brand icon, the marketplace manifest, the CI
workflow) and the copy's own listing fields in .claude-plugin/plugin.json. It writes
SOURCE.json for the tag, commit and ZIP digest, then checks the result with
verify_native_export.py.

Example, after the release tag exists:

    python3 scripts/export_native.py nobrainer-tech-flow-X.Y.Z-plugin.zip \\
        --tag vX.Y.Z --commit <tag commit> --copy ../nobrainer-tech-flow-plugin

Without --out the copy is rewritten in place; it must be a Git checkout with no
uncommitted changes, and everything in it except .git/ is replaced.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_native_export import CANONICAL, FROM_RELEASE, file_problem, verify  # noqa: E402

# Files only the copy has; each must exist in the current copy.
COPY_ONLY = ("README.md", "AGENTS.md", ".claude-plugin/icon.png", ".claude-plugin/marketplace.json",
             ".github/workflows/validate.yml")
# Listing fields the copy sets in its Claude manifest; every other field comes from the release.
LISTING_FIELDS = ("displayName", "homepage", "privacyPolicyUrl", "supportUrl", "termsOfServiceUrl")
DISTRIBUTION = "https://github.com/nobrainer-tech/nobrainer-tech-flow-plugin"


def build(payload: bytes, tag: str, commit: str, current: dict[str, bytes]) -> dict[str, bytes]:
    """The copy's files for the release ZIP PAYLOAD, given the CURRENT copy's own files."""

    missing = [name for name in (*COPY_ONLY, ".claude-plugin/plugin.json", "SOURCE.json") if name not in current]
    if missing:
        raise ValueError("the current copy lacks " + ", ".join(missing))
    version = tag[1:]
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        release = {safe_name(n): archive.read(n) for n in archive.namelist() if not n.endswith("/")}
    files = {n: d for n, d in release.items() if n.startswith("skills/") and file_problem(n, d) is None}
    files.update({name: release[name] for name in FROM_RELEASE})
    files.update({name: current[name] for name in COPY_ONLY})

    previous = json.loads(current["SOURCE.json"])
    old_tag = previous.get("tag", "")
    if old_tag and old_tag != tag:
        files["README.md"] = files["README.md"].replace(f"/{old_tag}".encode(), f"/{tag}".encode())
    market = json.loads(files[".claude-plugin/marketplace.json"])
    for plugin in market["plugins"]:
        plugin["version"] = version
    files[".claude-plugin/marketplace.json"] = dumps(market)

    canonical, own = json.loads(release[".claude-plugin/plugin.json"]), json.loads(current[".claude-plugin/plugin.json"])
    manifest = {key: own[key] if key in LISTING_FIELDS else canonical[key] for key in own if key in canonical or key in LISTING_FIELDS}
    manifest.update({key: value for key, value in canonical.items() if key not in manifest and key not in ("icon", "hooks", "mcpServers")})
    manifest["version"] = version
    files[".claude-plugin/plugin.json"] = dumps(manifest)
    files["SOURCE.json"] = dumps({
        "canonical_repository": CANONICAL,
        "tag": tag,
        "commit": commit,
        "distribution_repository": DISTRIBUTION,
        "skill_bodies": "identical to canonical release; scripts omitted",
        "plugin_zip_sha256": hashlib.sha256(payload).hexdigest(),
    })
    return files


def safe_name(name: str) -> str:
    """NAME if it is a plain relative archive path; it is checked before anything is written."""

    parts = name.split("/")
    if name.startswith("/") or "\\" in name or ":" in parts[0] or any(part in ("", ".", "..") for part in parts):
        raise ValueError(f"unsafe archive path {name!r}")
    return name


def dumps(value: dict) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def read_current(copy: Path) -> dict[str, bytes]:
    names = (*COPY_ONLY, ".claude-plugin/plugin.json", "SOURCE.json")
    return {name: (copy / name).read_bytes() for name in names if (copy / name).is_file()}


def write(files: dict[str, bytes], out: Path) -> None:
    root = out.resolve()
    for name, data in sorted(files.items()):
        target = out / name
        if not target.resolve().is_relative_to(root):
            raise ValueError(f"{name} would be written outside {out}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def clear_checkout(copy: Path) -> None:
    status = subprocess.run(["git", "-C", str(copy), "status", "--porcelain"], capture_output=True, text=True, check=True)
    if status.stdout.strip():
        raise ValueError(f"{copy} has uncommitted changes; commit or discard them first")
    for entry in copy.iterdir():
        if entry.name == ".git":
            continue
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("zip", type=Path, help="the release's nobrainer-tech-flow-X.Y.Z-plugin.zip")
    parser.add_argument("--tag", required=True, help="the release tag, vX.Y.Z")
    parser.add_argument("--commit", required=True, help="the full commit SHA the tag points to")
    parser.add_argument("--copy", type=Path, required=True, help="a checkout of nobrainer-tech-flow-plugin")
    parser.add_argument("--out", type=Path, help="write to this new or empty folder instead of the checkout")
    args = parser.parse_args(argv)
    try:
        payload = args.zip.read_bytes()
        files = build(payload, args.tag, args.commit, read_current(args.copy))
        if args.out:
            if args.out.exists() and any(args.out.iterdir()):
                raise ValueError(f"{args.out} is not empty")
            out = args.out
        else:
            clear_checkout(args.copy)
            out = args.copy
        out.mkdir(parents=True, exist_ok=True)
        write(files, out)
        problems = verify(out, payload, json.loads(files["SOURCE.json"]))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, subprocess.CalledProcessError) as exc:
        print(f"NATIVE_EXPORT_FAILED: {exc}")
        return 1
    if problems:
        print("NATIVE_EXPORT_INVALID")
        for problem in problems:
            print("- " + problem)
        return 1
    print(f"NATIVE_EXPORT_READY: {out} holds {len(files)} files for {args.tag}; review the diff, then publish through a PR.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
