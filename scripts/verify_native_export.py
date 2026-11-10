#!/usr/bin/env python3
"""Verify the Claude-directory copy of nobrainer-tech-flow against its canonical release.

The copy lives in nobrainer-tech/nobrainer-tech-flow-plugin and is the only one the Claude
plugin directory scans. The directory refuses scripts, programs and files outside a few
types from organizations it has not verified (LOCAL_CODE_FILE_TYPE), so the copy holds only
Markdown, plain text, JSON, YAML and a few image types. This script checks that rule and
that every skill file the copy keeps is byte-identical to the reviewed release ZIP.

Run from the copy's root (its CI does). By default it downloads the ZIP named in
SOURCE.json and checks the tag-to-commit binding on GitHub; --zip PATH reads a local ZIP
instead and --offline skips the tag lookup. Exit 0 prints NATIVE_EXPORT_VERIFIED; any
failure prints NATIVE_EXPORT_INVALID with one reason per line and exits 1.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import urllib.request
import zipfile

CANONICAL = "https://github.com/nobrainer-tech/nobrainer-tech-flow"
API = "https://api.github.com/repos/nobrainer-tech/nobrainer-tech-flow/git/"
TEXT_SUFFIXES = {".md", ".txt", ".json", ".yml", ".yaml"}
# The portal lets only "a license, a readme, .gitignore" stay without a type, as UTF-8
# text; any other extension-less file, such as skills/nobrainer-tech-flow/VERSION, is
# refused (it refused a0dab22 for that file), so the export leaves it out.
EXTENSIONLESS = {"license", "licence", "readme", ".gitignore"}
IMAGE_MAGIC = {
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".gif": (b"GIF87a", b"GIF89a"),
    ".ico": (b"\x00\x00\x01\x00",),
}
PACKAGE_FILES = {
    "package.json", "package-lock.json", "npm-shrinkwrap.json", "pnpm-lock.yaml",
    "pnpm-workspace.yaml", "yarn.lock", ".yarnrc", ".yarnrc.yml", ".npmrc", "bun.lock",
    "bun.lockb", "bunfig.toml", "uv.toml", "uv.lock", "pyproject.toml", "requirements.txt",
    "pipfile", "pipfile.lock", "poetry.lock", "pip.conf", ".pypirc", "deno.json", "deno.jsonc",
    "deno.lock", "gemfile", "gemfile.lock", "cargo.toml", "cargo.lock", "go.mod", "go.sum",
    "composer.json", "composer.lock", "pnpmfile.cjs", ".pnpmfile.cjs",
}
FORBIDDEN_PATHS = ("bin", "hooks", "assets", ".codex-plugin", ".mcp.json", "mcp.json", "plugin.json")
KEPT_DOCS = ["docs/CHAT_PLUGINS.md", "docs/PRIVACY.md"]
FROM_RELEASE = ["LICENSE", "SECURITY.md", *KEPT_DOCS]


def file_problem(name: str, data: bytes) -> str | None:
    """Why the directory would refuse this file from an unverified organization, or None."""

    base = name.rsplit("/", 1)[-1]
    suffix = Path(base).suffix.lower()
    if base.lower() in PACKAGE_FILES:
        return "package manager file"
    if suffix == ".webp":
        return None if data[:4] == b"RIFF" and data[8:12] == b"WEBP" else "not a WebP image"
    if suffix in IMAGE_MAGIC:
        return None if data.startswith(IMAGE_MAGIC[suffix]) else f"not a {suffix[1:].upper()} image"
    if suffix == "" and base.lower() not in EXTENSIONLESS:
        return "a file without an extension must be a license, a readme or .gitignore"
    if suffix not in TEXT_SUFFIXES and suffix != "":
        return f"type {suffix} is not allowed"
    if data.startswith(b"#!"):
        return "starts with #!"
    if b"\x00" in data:
        return "holds a NUL byte"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "is not UTF-8 text"
    if suffix == ".json":
        try:
            json.loads(text)
        except ValueError:
            return "is not valid JSON"
    return None


def copy_files(root: Path) -> tuple[dict[str, bytes], list[str]]:
    files, problems = {}, []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative == ".git" or relative.startswith(".git/"):
            continue
        if path.is_symlink():
            problems.append(f"{relative}: symbolic link")
        elif path.is_file():
            files[relative] = path.read_bytes()
    return files, problems


def verify(root: Path, payload: bytes, source: dict) -> list[str]:
    """Every reason ROOT is not a valid export of the release ZIP PAYLOAD; empty when valid."""

    problems = []
    if source.get("canonical_repository") != CANONICAL:
        problems.append("SOURCE.json: canonical_repository is not " + CANONICAL)
    tag = source.get("tag", "")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", str(tag)):
        problems.append("SOURCE.json: tag is not vX.Y.Z")
    if not re.fullmatch(r"[0-9a-f]{40}", str(source.get("commit", ""))):
        problems.append("SOURCE.json: commit is not a full SHA")
    if hashlib.sha256(payload).hexdigest() != source.get("plugin_zip_sha256"):
        problems.append("SOURCE.json: plugin_zip_sha256 does not match the release ZIP")
    version = str(tag)[1:]

    files, link_problems = copy_files(root)
    problems += link_problems
    for name, data in files.items():
        reason = file_problem(name, data)
        if reason:
            problems.append(f"{name}: {reason}")
    for name in FORBIDDEN_PATHS:
        if (root / name).exists():
            problems.append(f"{name}: must not be in this copy")

    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        release = {n: archive.read(n) for n in archive.namelist() if not n.endswith("/")}
    expected = {n: d for n, d in release.items() if n.startswith("skills/") and file_problem(n, d) is None}
    kept = {n: d for n, d in files.items() if n.startswith("skills/")}
    for name in sorted(set(expected) - set(kept)):
        problems.append(f"{name}: missing; only files of a refused type may be left out")
    for name in sorted(set(kept) - set(expected)):
        problems.append(f"{name}: not an allowed file of the release ZIP")
    for name in sorted(set(kept) & set(expected)):
        if kept[name] != expected[name]:
            problems.append(f"{name}: differs from the release ZIP")
    for name in FROM_RELEASE:
        if files.get(name) != release.get(name):
            problems.append(f"{name}: missing or differs from the release ZIP")
    docs = sorted(n for n in files if n.startswith("docs/"))
    if docs != KEPT_DOCS:
        problems.append(f"docs/: must hold exactly {', '.join(KEPT_DOCS)}")
    if len([n for n in kept if re.fullmatch(r"skills/[^/]+/SKILL\.md", n)]) != 18:
        problems.append("skills/: must hold exactly 18 SKILL.md files")

    problems += manifest_problems(files, version)
    return problems


def manifest_problems(files: dict[str, bytes], version: str) -> list[str]:
    problems = []
    try:
        claude = json.loads(files[".claude-plugin/plugin.json"])
        market = json.loads(files[".claude-plugin/marketplace.json"])
    except (KeyError, ValueError) as exc:
        return [f".claude-plugin: manifest missing or unreadable ({exc})"]
    if claude.get("name") != "nobrainer-tech-flow" or claude.get("version") != version:
        problems.append(".claude-plugin/plugin.json: name or version does not match the release")
    if {"hooks", "mcpServers", "icon"} & set(claude):
        problems.append(".claude-plugin/plugin.json: hooks, mcpServers and icon fields are not allowed")
    if [p.get("version") for p in market.get("plugins", [])] != [version]:
        problems.append(".claude-plugin/marketplace.json: plugin version does not match the release")
    if ".claude-plugin/icon.png" not in files:
        problems.append(".claude-plugin/icon.png: missing")
    return problems


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def tag_commit(tag: str) -> str:
    ref = json.loads(fetch(API + "ref/tags/" + tag))["object"]
    if ref["type"] == "tag":
        ref = json.loads(fetch(API + "tags/" + ref["sha"]))["object"]
    return ref["sha"] if ref["type"] == "commit" else ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("root", nargs="?", type=Path, default=Path("."), help="the copy's root (default: .)")
    parser.add_argument("--zip", type=Path, help="local release ZIP instead of downloading it")
    parser.add_argument("--offline", action="store_true", help="skip the tag-to-commit lookup on GitHub")
    args = parser.parse_args(argv)
    try:
        source = json.loads((args.root / "SOURCE.json").read_text(encoding="utf-8"))
        tag = source["tag"]
        payload = args.zip.read_bytes() if args.zip else fetch(
            f"{CANONICAL}/releases/download/{tag}/nobrainer-tech-flow-{tag[1:]}-plugin.zip")
        problems = verify(args.root, payload, source)
        if not args.offline and tag_commit(tag) != source.get("commit"):
            problems.append("SOURCE.json: commit is not the one the canonical tag points to")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
        problems = [f"cannot read the copy or the release: {exc}"]
    if problems:
        print("NATIVE_EXPORT_INVALID")
        for problem in problems:
            print("- " + problem)
        return 1
    print("NATIVE_EXPORT_VERIFIED: allowed file types only; every kept skill file matches the release ZIP.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
