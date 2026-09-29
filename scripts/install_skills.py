#!/usr/bin/env python3
"""Install active skills without overwriting an existing installation."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import os
import re
import shutil
import stat
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"


def client_destinations(
    environ: Mapping[str, str] | None = None, home: Path | None = None
) -> dict[str, Path]:
    """Skill directories per client, honouring the variables the clients read.

    Claude Code reads CLAUDE_CONFIG_DIR and OpenCode follows XDG_CONFIG_HOME; an
    empty value counts as unset, and a value that is not an absolute path is an error
    (it would resolve against whatever directory the script happens to run from).
    """

    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else home
    values = {}
    for name in ("CLAUDE_CONFIG_DIR", "XDG_CONFIG_HOME"):
        value = (environ.get(name) or "").strip()
        if value and not Path(value).is_absolute():
            raise ValueError(f"{name} must be an absolute path, not {value!r}")
        values[name] = value
    claude = values["CLAUDE_CONFIG_DIR"]
    xdg = values["XDG_CONFIG_HOME"]
    return {
        "claude": (Path(claude) if claude else home / ".claude") / "skills",
        "codex": home / ".agents" / "skills",
        "opencode": (Path(xdg) if xdg else home / ".config") / "opencode" / "skills",
        "copilot": home / ".copilot" / "skills",
        "agents": home / ".agents" / "skills",
    }


try:
    CLIENT_DESTINATIONS = client_destinations()
except ValueError:
    # main() reports a bad environment value; the module itself must still import.
    CLIENT_DESTINATIONS = client_destinations({})

CURATED_SKILLS = frozenset(
    {
        "nobrainer-codex-context",
        "nobrainer-skill-doctor",
        "nobrainer-autoimprove",
        "nobrainer-auto-fine-tune",
        "nobrainer-browser",
        "nobrainer-build",
        "nobrainer-security",
        "nobrainer-decide",
        "nobrainer-dispatcher",
        "nobrainer-rca",
        "nobrainer-review",
        "nobrainer-research",
        "nobrainer-writing",
        "nobrainer-sessions",
        "nobrainer-spec-driven-development",
        "nobrainer-tech-flow",
        "nobrainer-wiki",
        "nobrainer-team",
    }
)

# Reviewed predecessor names and migration candidates. A legacy symlink is
# migratable only when its name and target both match this table and this exact
# checkout; foreign/private targets remain conflicts and are never touched.
LEGACY_TO_CANONICAL = {
    "nobrainer-ultra": "nobrainer-tech-flow",
    "add-gitleaks": "nobrainer-review",
    "agent-browser": "nobrainer-browser",
    "agents-restraint": "nobrainer-tech-flow",
    "codex-in-claude-code": "nobrainer-tech-flow",
    "code-autoresearch": "nobrainer-autoimprove",
    "deep-audit": "nobrainer-review",
    "deep-autoreview": "nobrainer-review",
    "deep-autoresearch": "nobrainer-autoimprove",
    "deep-bugs-finder": "nobrainer-review",
    "deep-code-review": "nobrainer-review",
    "deep-decide": "nobrainer-decide",
    "dispatching-parallel-agents": "nobrainer-dispatcher",
    "deep-rca": "nobrainer-rca",
    "engineering-standards": "nobrainer-build",
    "karpathy-auto-improver": "nobrainer-autoimprove",
    "karpathy-llm-wiki": "nobrainer-wiki",
    "llm-wiki": "nobrainer-wiki",
    "nb-add": "nobrainer-wiki",
    "nb-flow": "nobrainer-tech-flow",
    "nb-dispatcher": "nobrainer-dispatcher",
    "nb-get": "nobrainer-wiki",
    "nb-multi": "nobrainer-sessions",
    "nb-tidy": "nobrainer-wiki",
    "nb-workflow": "nobrainer-tech-flow",
    "nb-write": "nobrainer-writing",
    "nobrainer-autopilot": "nobrainer-tech-flow",
    "nobrainer-browser": "nobrainer-browser",
    "nobrainer-capture-lesson": "nobrainer-autoimprove",
    "nobrainer-continuous-improvement": "nobrainer-autoimprove",
    "nobrainer-skill-browser": "nobrainer-team",
    "nobrainer-simplifier": "nobrainer-build",
    "nobrainer-style": "nobrainer-writing",
    "nobrainer-human-like": "nobrainer-writing",
    "nobrainer-starter": "nobrainer-tech-flow",
    "nobrainer-memory": "nobrainer-wiki",
    "nobrainer-memory-memsearch": "nobrainer-wiki",
    "nobrainer-npm-secure": "nobrainer-security",
    "nobrainer-reddit": "nobrainer-tech-flow",
    "nobrainer-team-builder": "nobrainer-team",
    "nobrainer-ultracode-workflow": "nobrainer-tech-flow",
    "nobrainer-wiki-add": "nobrainer-wiki",
    "nobrainer-wiki-get": "nobrainer-wiki",
    "nobrainer-wiki-tidy": "nobrainer-wiki",
    "playwright-cli": "nobrainer-browser",
    "security-review": "nobrainer-security",
    "session-handoff": "nobrainer-sessions",
    "wiki-add": "nobrainer-wiki",
    "wiki-get": "nobrainer-wiki",
    "wiki-tidy": "nobrainer-wiki",
}
UNMAPPED_LEGACY = frozenset({"nobrainer-fast-audit"})


EntryFingerprint = tuple[int, int, int, str | None]
TreeManifest = tuple[tuple[str, str, int, str], ...]


def entry_fingerprint(target: Path) -> EntryFingerprint | None:
    """Fingerprint one directory entry without following a symlink."""

    try:
        metadata = target.lstat()
        linked = os.readlink(target) if stat.S_ISLNK(metadata.st_mode) else None
    except OSError:
        return None
    return metadata.st_dev, metadata.st_ino, metadata.st_mode, linked


JUNK_NAMES = frozenset({"__pycache__", ".DS_Store", "Thumbs.db"})


def is_junk(name: str) -> bool:
    """Bytecode and file-manager litter: never part of a skill, so never compared."""

    return name in JUNK_NAMES or name.endswith(".pyc")


def file_digest(path: Path) -> str:
    """SHA-256 in bounded chunks, so a huge foreign file cannot exhaust memory."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_manifest(root: Path, hash_files: bool = True) -> TreeManifest:
    """Fingerprint a tree without following links or accepting special files.

    With ``hash_files=False`` a file is identified by its size only, which is enough
    to tell two different trees apart without reading a byte of either.
    """

    entries: list[tuple[str, str, int, str]] = []
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        traversable: list[str] = []
        for name in sorted(directories):
            if is_junk(name):
                continue
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                entries.append((relative, "symlink", 0, os.readlink(path)))
            elif stat.S_ISDIR(metadata.st_mode):
                entries.append(
                    (relative, "directory", stat.S_IMODE(metadata.st_mode), "")
                )
                traversable.append(name)
            else:
                raise RuntimeError(f"unsupported source entry: {path}")
        directories[:] = traversable

        for name in sorted(files):
            if is_junk(name):
                continue
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                entries.append((relative, "symlink", 0, os.readlink(path)))
            elif stat.S_ISREG(metadata.st_mode):
                digest = (
                    file_digest(path) if hash_files else f"size:{metadata.st_size}"
                )
                entries.append(
                    (relative, "file", stat.S_IMODE(metadata.st_mode), digest)
                )
            else:
                raise RuntimeError(f"unsupported source entry: {path}")
    return tuple(sorted(entries))


def stage_and_publish_copy(
    source: Path, target: Path
) -> tuple[EntryFingerprint, TreeManifest, Path]:
    """Verify a private copy, then publish it with native no-replace rename."""

    stage_parent = Path(
        tempfile.mkdtemp(prefix=".nobrainer-install-", dir=target.parent)
    )
    staged = stage_parent / target.name
    try:
        source_before = tree_manifest(source)
        shutil.copytree(
            source,
            staged,
            symlinks=True,
            ignore=lambda _directory, names: [name for name in names if is_junk(name)],
        )
        staged_manifest = tree_manifest(staged)
        source_after = tree_manifest(source)
        if source_before != source_after:
            raise RuntimeError(f"source changed while copying: {source}")
        if staged_manifest != source_before:
            raise RuntimeError(f"staged copy verification failed: {source}")

        expected = entry_fingerprint(staged)
        if expected is None:
            raise RuntimeError(f"staged copy disappeared before publish: {staged}")
        atomic_rename_no_replace(staged, target)
    except Exception as exc:
        raise RuntimeError(
            f"copy staging preserved for manual recovery at {stage_parent}: {exc}"
        ) from exc
    return expected, source_before, stage_parent


def stage_and_publish_symlink(
    source: Path, target: Path
) -> tuple[EntryFingerprint, Path]:
    """Fingerprint a private symlink, then publish that exact entry atomically."""

    stage_parent = Path(
        tempfile.mkdtemp(prefix=".nobrainer-install-", dir=target.parent)
    )
    staged = stage_parent / target.name
    try:
        os.symlink(source, staged, target_is_directory=True)
        expected = entry_fingerprint(staged)
        if expected is None:
            raise RuntimeError(f"staged symlink disappeared before publish: {staged}")
        atomic_rename_no_replace(staged, target)
    except Exception as exc:
        raise RuntimeError(
            f"symlink staging preserved for manual recovery at {stage_parent}: {exc}"
        ) from exc
    return expected, stage_parent


def remove_created_entry(
    target: Path,
    expected: EntryFingerprint,
    expected_manifest: TreeManifest | None = None,
) -> None:
    """Move a created entry out of the public target and preserve it for recovery."""

    current_fingerprint = entry_fingerprint(target)
    if current_fingerprint is None:
        return
    if current_fingerprint == expected and expected_manifest is not None:
        try:
            current_manifest = tree_manifest(target)
        except (OSError, RuntimeError) as exc:
            raise RuntimeError(
                f"created copy could not be verified; target preserved at {target}"
            ) from exc
        if current_manifest != expected_manifest:
            raise RuntimeError(
                f"created copy content changed; target preserved at {target}"
            )

    claim_dir = Path(
        tempfile.mkdtemp(prefix=".nobrainer-rollback-", dir=target.parent)
    )
    claim = claim_dir / target.name
    try:
        target.rename(claim)
    except OSError as exc:
        try:
            claim_dir.rmdir()
        except OSError:
            pass
        if entry_fingerprint(target) is None:
            return
        raise RuntimeError(f"created target could not be claimed: {target}") from exc

    claimed = entry_fingerprint(claim)
    if claimed != expected:
        try:
            restore_claim(target, claim)
        except RuntimeError as exc:
            raise RuntimeError(
                f"ownership changed after creation; foreign replacement preserved "
                f"at {claim}; {exc}"
            ) from exc
        raise RuntimeError(
            f"ownership changed after creation; foreign target restored at {target}"
        )

    if expected_manifest is not None:
        try:
            claimed_manifest = tree_manifest(claim)
        except (OSError, RuntimeError) as exc:
            try:
                restore_claim(target, claim, expected)
            except RuntimeError as restore_exc:
                raise RuntimeError(
                    f"created copy changed while claimed; recovery preserved at "
                    f"{claim}; {restore_exc}"
                ) from exc
            raise RuntimeError(
                f"created copy changed while claimed; target restored at {target}"
            ) from exc
        if claimed_manifest != expected_manifest:
            try:
                restore_claim(target, claim, expected)
            except RuntimeError as exc:
                raise RuntimeError(
                    f"created copy content changed while claimed; recovery preserved "
                    f"at {claim}; {exc}"
                ) from exc
            raise RuntimeError(
                f"created copy content changed while claimed; target restored at "
                f"{target}"
            )

    # There is no portable compare-and-delete primitive for a pathname. Keep the
    # verified private claim instead of risking deletion of a same-user
    # replacement between the last fingerprint and unlink/rmtree.
    raise RuntimeError(
        f"verified rollback claim preserved for manual recovery at {claim}"
    )


def is_exact_legacy_link(target: Path, legacy_name: str) -> bool:
    """Return whether target is the known stale link owned by this checkout."""

    return legacy_link_snapshot(target, legacy_name) is not None


def legacy_link_snapshot(
    target: Path, legacy_name: str
) -> EntryFingerprint | None:
    """Verify and fingerprint the same legacy symlink directory entry."""

    try:
        before = target.lstat()
        if not stat.S_ISLNK(before.st_mode):
            return None
        linked = os.readlink(target)
        after = target.lstat()
    except OSError:
        return None

    before_id = before.st_dev, before.st_ino, before.st_mode
    after_id = after.st_dev, after.st_ino, after.st_mode
    if before_id != after_id:
        return None

    resolved = Path(linked)
    if not resolved.is_absolute():
        resolved = target.parent / resolved
    known_sources = {
        (ROOT / legacy_name).resolve(strict=False),
        (SKILLS / legacy_name).resolve(strict=False),
    }
    try:
        resolved_target = resolved.resolve(strict=False)
    except (OSError, RuntimeError):
        # A symlink loop is never one of the known legacy links.
        return None
    if resolved_target not in known_sources:
        return None
    return before_id[0], before_id[1], before_id[2], linked


def legacy_name_for(target: Path, canonical: Path) -> str | None:
    """Return the known root-level predecessor referenced by a canonical target."""

    candidates = [canonical.name]
    candidates.extend(
        legacy_name
        for legacy_name, canonical_name in sorted(LEGACY_TO_CANONICAL.items())
        if canonical_name == canonical.name and legacy_name != canonical.name
    )
    canonical_source = canonical.resolve(strict=False)
    for legacy_name in candidates:
        old_source = (ROOT / legacy_name).resolve(strict=False)
        if old_source != canonical_source and is_exact_legacy_link(
            target, legacy_name
        ):
            return legacy_name
    return None


def claim_legacy_link(
    target: Path, legacy_name: str
) -> tuple[Path, EntryFingerprint]:
    """Atomically move a candidate aside, then verify ownership before deletion."""

    expected = legacy_link_snapshot(target, legacy_name)
    if expected is None:
        raise RuntimeError(f"legacy link changed before claim: {target}")

    claim_dir = Path(
        tempfile.mkdtemp(prefix=".nobrainer-migration-", dir=target.parent)
    )
    claim = claim_dir / target.name
    try:
        target.rename(claim)
    except OSError as exc:
        claim_dir.rmdir()
        raise RuntimeError(f"legacy link changed after preflight: {target}") from exc

    claimed = entry_fingerprint(claim)

    # Compare the moved directory entry itself. Re-resolving a relative link
    # from claim.parent would change its base and reject a valid legacy link.
    if claimed == expected:
        return claim, expected

    try:
        restore_claim(target, claim)
    except RuntimeError as exc:
        raise RuntimeError(
            f"legacy link changed after preflight; {exc}"
        ) from exc
    raise RuntimeError(
        f"legacy link changed after preflight; replacement restored at {target}"
    )


def atomic_rename_no_replace(source: Path, target: Path) -> None:
    """Rename one entry only when target is absent, using the native primitive."""

    if os.name == "nt":
        # Windows os.rename already refuses to replace an existing target, and
        # ctypes.CDLL(None) is not supported there.
        os.rename(source, target)
        return

    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    target_bytes = os.fsencode(target)

    if sys.platform == "darwin":
        renamex = getattr(libc, "renamex_np", None)
        if renamex is None:
            raise RuntimeError("atomic no-replace rename is unavailable")
        renamex.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        renamex.restype = ctypes.c_int
        result = renamex(source_bytes, target_bytes, 0x00000004)  # RENAME_EXCL
    elif sys.platform.startswith("linux"):
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise RuntimeError("atomic no-replace rename is unavailable")
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        result = renameat2(
            -100, source_bytes, -100, target_bytes, 0x00000001
        )  # AT_FDCWD, RENAME_NOREPLACE
    else:
        raise RuntimeError("atomic no-replace rename is unavailable")

    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number), str(target))


def restore_claim(
    target: Path,
    claim: Path,
    expected: EntryFingerprint | None = None,
) -> None:
    """Restore a claimed entry atomically without replacing a new target."""

    fingerprint = entry_fingerprint(claim)
    if fingerprint is None:
        raise RuntimeError(f"missing or unreadable claim preserved at {claim}")
    if expected is not None and fingerprint != expected:
        raise RuntimeError(f"claim ownership changed; replacement preserved at {claim}")
    try:
        # Move the entry back instead of recreating and deleting a duplicate.
        # This preserves relative symlink text and has no deletion race.
        atomic_rename_no_replace(claim, target)
    except OSError as exc:
        raise RuntimeError(
            f"replacement preserved at {claim}; restore blocked by {target}"
        ) from exc
    except RuntimeError as exc:
        raise RuntimeError(f"replacement preserved at {claim}; {exc}") from exc

    if entry_fingerprint(target) != fingerprint:
        raise RuntimeError(
            f"restored entry changed concurrently; inspect preserved target {target}"
        )
    try:
        claim.parent.rmdir()
    except OSError as exc:
        raise RuntimeError(
            f"replacement restored at {target}; claim directory remains at {claim.parent}"
        ) from exc


def available_skills() -> dict[str, Path]:
    return {
        path.parent.name: path.parent
        for path in sorted(SKILLS.glob("*/SKILL.md"))
    }


def existing_state(target: Path, source: Path, mode: str) -> str:
    if not target.exists() and not target.is_symlink():
        return "missing"
    if target.is_symlink():
        try:
            if mode == "symlink" and target.resolve(strict=True) == source.resolve(
                strict=True
            ):
                return "current"
        except (OSError, RuntimeError):
            # Dangling links and symlink loops are conflicts, not crashes.
            pass
        if legacy_name_for(target, source) is not None:
            return "legacy"
    elif mode == "copy" and target.is_dir():
        try:
            # Compare names, kinds and sizes first: a foreign directory (possibly with
            # gigabytes in it) is then rejected without reading any file.
            if tree_manifest(target, hash_files=False) == tree_manifest(
                source, hash_files=False
            ) and tree_manifest(target) == tree_manifest(source):
                return "current"
        except (OSError, RuntimeError):
            pass
    return "conflict"


def destination_problem(destination: Path) -> str | None:
    """Explain why a destination cannot hold skills, before anything is planned."""

    for candidate in (destination, *destination.parents):
        if candidate.exists():
            if not candidate.is_dir():
                return f"destination is not a directory: {candidate}"
            return None
    return None


def linked_skills(name: str, catalogue: dict[str, Path]) -> list[str]:
    """Other skills that a skill links into with relative Markdown links."""

    found: list[str] = []
    for markdown in sorted(catalogue[name].rglob("*.md")):
        text = markdown.read_text(encoding="utf-8")
        for match in re.finditer(r"\]\((\.\./[^)#\s]+)", text):
            target = os.path.normpath(markdown.parent / match.group(1))
            try:
                relative = Path(target).relative_to(SKILLS)
            except ValueError:
                continue
            other = relative.parts[0] if relative.parts else ""
            if other and other != name and other in catalogue and other not in found:
                found.append(other)
    return found


def unmet_references(
    names: list[str], catalogue: dict[str, Path], destination: Path
) -> list[tuple[str, str]]:
    """Cross-skill links from selected skills to skills that will be absent."""

    present = set(names) | {
        name for name in catalogue if (destination / name / "SKILL.md").is_file()
    }
    return [
        (name, other)
        for name in names
        for other in linked_skills(name, catalogue)
        if other not in present
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Dry-run or install NoBrainer skills into one client directory."
    )
    parser.add_argument("--client", choices=sorted(CLIENT_DESTINATIONS), required=True)
    parser.add_argument(
        "--dest",
        type=Path,
        help="Override the client destination (useful for controlled tests).",
    )
    parser.add_argument("--mode", choices=("symlink", "copy"), default="symlink")
    parser.add_argument(
        "--skill",
        action="append",
        dest="skills",
        help="Install only this skill; repeat for several. Default: all curated skills.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Perform writes. Without this flag the command is a dry-run.",
    )
    parser.add_argument(
        "--migrate-legacy",
        action="store_true",
        help=(
            "Migrate only exact stale symlinks from this checkout's previous "
            "root-level layout and renamed aliases."
        ),
    )
    return parser.parse_args()


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            # Piped output on Windows uses the ANSI code page, which cannot print every
            # character of a user's paths.
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = parse_args()
    catalogue = available_skills()
    actual_inventory = set(catalogue)
    if actual_inventory != CURATED_SKILLS:
        missing = sorted(CURATED_SKILLS - actual_inventory)
        extra = sorted(actual_inventory - CURATED_SKILLS)
        print(
            f"ERROR: curated skill inventory drift: missing={missing}, extra={extra}",
            file=sys.stderr,
        )
        return 2

    requested = sorted(set(args.skills)) if args.skills else sorted(CURATED_SKILLS)
    unknown = sorted(set(requested) - CURATED_SKILLS)
    if unknown:
        print(f"ERROR: unknown active skill(s): {', '.join(unknown)}", file=sys.stderr)
        return 2

    try:
        destination = (
            args.dest or client_destinations()[args.client]
        ).expanduser().resolve()
        problem = destination_problem(destination)
    except (OSError, RuntimeError, ValueError) as exc:
        # Symlink loops, unreadable parents and unusable environment variables.
        print(f"ERROR: cannot use the destination: {exc}", file=sys.stderr)
        return 2
    if problem:
        print(f"ERROR: {problem}", file=sys.stderr)
        return 2
    plan: list[tuple[str, Path, Path, str]] = []
    conflicts: list[Path] = []
    for name in requested:
        source = catalogue[name]
        target = destination / name
        state = existing_state(target, source, args.mode)
        plan.append((name, source, target, state))
        if state == "conflict" or (state == "legacy" and not args.migrate_legacy):
            conflicts.append(target)

    alias_plan: list[tuple[str, str, Path, str]] = []
    for legacy_name, canonical_name in sorted(LEGACY_TO_CANONICAL.items()):
        if legacy_name == canonical_name or canonical_name not in requested:
            continue
        target = destination / legacy_name
        if not target.exists() and not target.is_symlink():
            continue
        state = "legacy" if is_exact_legacy_link(target, legacy_name) else "conflict"
        alias_plan.append((legacy_name, canonical_name, target, state))
        if state == "conflict" or not args.migrate_legacy:
            conflicts.append(target)

    unmapped_plan: list[Path] = []
    for legacy_name in sorted(UNMAPPED_LEGACY):
        target = destination / legacy_name
        if target.exists() or target.is_symlink():
            unmapped_plan.append(target)
            conflicts.append(target)

    for name, source, target, state in plan:
        action = (
            "KEEP"
            if state == "current"
            else "CONFLICT"
            if state == "conflict"
            else "MIGRATE"
            if state == "legacy" and args.migrate_legacy
            else "LEGACY"
            if state == "legacy"
            else args.mode.upper()
        )
        print(f"{action}: {name}: {source} -> {target}")

    for legacy_name, canonical_name, target, state in alias_plan:
        action = (
            "MIGRATE_ALIAS"
            if state == "legacy" and args.migrate_legacy
            else "LEGACY_ALIAS"
            if state == "legacy"
            else "CONFLICT_ALIAS"
        )
        print(f"{action}: {legacy_name} -> {canonical_name}: {target}")

    for name, other in unmet_references(requested, catalogue, destination):
        print(
            f"NOTE: {name} links to {other}, which is not selected or installed; "
            f"add --skill {other} to include it"
        )

    for target in unmapped_plan:
        print(
            "UNMAPPED_CONFLICT: "
            f"{target.name}: preserve and audit before selecting a canonical owner: "
            f"{target}"
        )

    if conflicts:
        has_unknown_conflict = (
            bool(unmapped_plan)
            or any(state == "conflict" for _, _, _, state in plan)
            or any(state == "conflict" for _, _, _, state in alias_plan)
        )
        has_migratable_legacy = any(
            state == "legacy" for _, _, _, state in plan
        ) or any(state == "legacy" for _, _, _, state in alias_plan)
        if has_migratable_legacy and not args.migrate_legacy and not has_unknown_conflict:
            print(
                "ERROR: legacy symlink detected; rerun with "
                "--migrate-legacy --apply",
                file=sys.stderr,
            )
        else:
            print("ERROR: refusing to overwrite existing targets", file=sys.stderr)
        return 3
    if not args.apply:
        suffix = (
            " with --migrate-legacy --apply"
            if any(state == "legacy" for _, _, _, state in plan)
            or any(state == "legacy" for _, _, _, state in alias_plan)
            else " with --apply"
        )
        print(f"DRY_RUN: no files changed; rerun{suffix} to install")
        return 0

    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"ERROR: cannot create destination {destination}: {exc}", file=sys.stderr)
        return 2
    created: list[tuple[Path, EntryFingerprint, TreeManifest | None]] = []
    migrated: list[tuple[Path, Path, str, EntryFingerprint]] = []
    copied_manifests: dict[Path, TreeManifest] = {}
    try:
        for _, source, target, state in plan:
            if state == "current" and args.mode == "copy":
                copied_manifests[target] = tree_manifest(source)
        for legacy_name, _, target, state in alias_plan:
            if state != "legacy":
                continue
            claim, expected = claim_legacy_link(target, legacy_name)
            migrated.append((target, claim, legacy_name, expected))

        for _, source, target, state in plan:
            if state == "current":
                continue
            if state == "legacy":
                legacy_name = legacy_name_for(target, source)
                if legacy_name is None:
                    raise RuntimeError(f"legacy target changed after preflight: {target}")
                claim, expected = claim_legacy_link(target, legacy_name)
                migrated.append((target, claim, legacy_name, expected))
            if args.mode == "symlink":
                expected, stage_parent = stage_and_publish_symlink(source, target)
                created.append((target, expected, None))
                if entry_fingerprint(target) != expected:
                    raise RuntimeError(
                        f"published symlink changed before readback: {target}"
                    )
                try:
                    stage_parent.rmdir()
                except OSError as exc:
                    raise RuntimeError(
                        f"published symlink is complete but private staging directory "
                        f"could not be removed: {stage_parent}"
                    ) from exc
            else:
                expected, manifest, stage_parent = stage_and_publish_copy(
                    source, target
                )
                created.append((target, expected, manifest))
                copied_manifests[target] = manifest
                if entry_fingerprint(target) != expected:
                    raise RuntimeError(
                        f"published target changed before readback: {target}"
                    )
                try:
                    stage_parent.rmdir()
                except OSError as exc:
                    raise RuntimeError(
                        f"published copy is complete but private staging directory "
                        f"could not be removed: {stage_parent}"
                    ) from exc

        for _, source, target, _ in plan:
            if not (target / "SKILL.md").is_file():
                raise RuntimeError(f"readback failed for {target}")
            if (
                args.mode == "symlink"
                and target.resolve(strict=True) != source.resolve(strict=True)
            ):
                raise RuntimeError(f"symlink readback mismatch for {target}")
            if args.mode == "copy" and tree_manifest(target) != copied_manifests.get(
                target
            ):
                raise RuntimeError(f"copy readback mismatch for {target}")
    except Exception as exc:
        rollback_errors: list[str] = []
        for target, fingerprint, manifest in reversed(created):
            try:
                remove_created_entry(target, fingerprint, manifest)
            except (OSError, RuntimeError) as rollback_exc:
                rollback_errors.append(f"{target}: {rollback_exc}")
        for target, claim, _, expected in reversed(migrated):
            try:
                restore_claim(target, claim, expected)
            except (OSError, RuntimeError) as rollback_exc:
                rollback_errors.append(
                    f"{target} (legacy preserved at {claim}): {rollback_exc}"
                )
        if rollback_errors:
            print(
                "ERROR: installation failed and rollback was incomplete: "
                f"{exc}; leftovers: {'; '.join(rollback_errors)}",
                file=sys.stderr,
            )
        else:
            print(f"ERROR: installation rolled back: {exc}", file=sys.stderr)
        return 4

    changed_backups: list[str] = []
    for _, claim, _, expected in migrated:
        if entry_fingerprint(claim) == expected:
            print(f"BACKUP_PRESERVED: migrated legacy link: {claim}")
        else:
            changed_backups.append(str(claim))
    if changed_backups:
        print(
            "WARNING: install succeeded, but migration backup ownership changed; "
            "entries were preserved without deletion: " + "; ".join(changed_backups),
            file=sys.stderr,
        )

    print(
        f"OK: installed {len(created)} skill(s) for {args.client}; "
        f"{len(migrated)} legacy link(s) migrated; "
        f"{len(plan) - len(created)} unchanged; "
        f"{len(migrated)} recovery backup(s) preserved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
