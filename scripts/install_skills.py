#!/usr/bin/env python3
"""Install active skills without overwriting an existing installation."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
CLIENT_DESTINATIONS = {
    "claude": Path.home() / ".claude" / "skills",
    "codex": Path.home() / ".agents" / "skills",
    "opencode": Path.home() / ".config" / "opencode" / "skills",
    "copilot": Path.home() / ".copilot" / "skills",
    "agents": Path.home() / ".agents" / "skills",
}

CURATED_SKILLS = frozenset(
    {
        "nobrainer-codex-context",
        "nobrainer-autoimprove",
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
        "nobrainer-ultra",
        "nobrainer-wiki",
        "nobrainer-team",
    }
)

# Reviewed predecessor names and migration candidates. A legacy symlink is
# migratable only when its name and target both match this table and this exact
# checkout; foreign/private targets remain conflicts and are never touched.
LEGACY_TO_CANONICAL = {
    "add-gitleaks": "nobrainer-review",
    "agent-browser": "nobrainer-browser",
    "agents-restraint": "nobrainer-ultra",
    "codex-in-claude-code": "nobrainer-ultra",
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
    "nb-flow": "nobrainer-ultra",
    "nb-dispatcher": "nobrainer-dispatcher",
    "nb-get": "nobrainer-wiki",
    "nb-multi": "nobrainer-sessions",
    "nb-tidy": "nobrainer-wiki",
    "nb-workflow": "nobrainer-ultra",
    "nb-write": "nobrainer-writing",
    "nobrainer-autopilot": "nobrainer-ultra",
    "nobrainer-browser": "nobrainer-browser",
    "nobrainer-capture-lesson": "nobrainer-autoimprove",
    "nobrainer-continuous-improvement": "nobrainer-autoimprove",
    "nobrainer-skill-browser": "nobrainer-team",
    "nobrainer-simplifier": "nobrainer-build",
    "nobrainer-style": "nobrainer-writing",
    "nobrainer-human-like": "nobrainer-writing",
    "nobrainer-starter": "nobrainer-ultra",
    "nobrainer-memory": "nobrainer-wiki",
    "nobrainer-memory-memsearch": "nobrainer-wiki",
    "nobrainer-npm-secure": "nobrainer-security",
    "nobrainer-reddit": "nobrainer-ultra",
    "nobrainer-team-builder": "nobrainer-team",
    "nobrainer-ultracode-workflow": "nobrainer-ultra",
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


def tree_manifest(root: Path) -> TreeManifest:
    """Fingerprint a tree without following links or accepting special files."""

    entries: list[tuple[str, str, int, str]] = []
    for current, directories, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        traversable: list[str] = []
        for name in sorted(directories):
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
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            metadata = path.lstat()
            if stat.S_ISLNK(metadata.st_mode):
                entries.append((relative, "symlink", 0, os.readlink(path)))
            elif stat.S_ISREG(metadata.st_mode):
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
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
        shutil.copytree(source, staged, symlinks=True)
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
    if resolved.resolve(strict=False) not in known_sources:
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
    elif os.name == "nt":
        # Windows os.rename already refuses to replace an existing target.
        os.rename(source, target)
        return
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
        except FileNotFoundError:
            pass
        if legacy_name_for(target, source) is not None:
            return "legacy"
    return "conflict"


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

    destination = (args.dest or CLIENT_DESTINATIONS[args.client]).expanduser().resolve()
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

    destination.mkdir(parents=True, exist_ok=True)
    created: list[tuple[Path, EntryFingerprint, TreeManifest | None]] = []
    migrated: list[tuple[Path, Path, str, EntryFingerprint]] = []
    copied_manifests: dict[Path, TreeManifest] = {}
    try:
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
