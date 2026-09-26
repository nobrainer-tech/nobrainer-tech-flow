#!/usr/bin/env python3
"""Guide a read-only nobrainer-tech-flow setup preflight and install an approved subset."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import stat
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 can still inspect JSON-based clients.
    tomllib = None  # type: ignore[assignment]


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
PERSONALIZATION = ROOT / "scripts" / "install_personalization.py"
STATE_NAME = ".nobrainer-flow-onboarding.json"


@dataclass(frozen=True)
class Item:
    id: str
    skill: str
    label: str
    profiles: tuple[str, ...]
    reason: str


# IDs are a user-facing selection contract. Keep them stable when descriptions
# or the repository's directory ordering changes; retired IDs must not be reused.
ITEMS = (
    Item("01", "nobrainer-tech-flow", "Task orchestration", ("all",), "one task entrypoint and completion checks"),
    Item("02", "nobrainer-auto-fine-tune", "Capability audit", ("all",), "read-only client/model/context/delegation audit; preserve MAIN"),
    Item("03", "nobrainer-build", "Implementation", ("software-development", "operations"), "bounded code and configuration changes with verification"),
    Item("04", "nobrainer-review", "Code review", ("software-development",), "independent checks for defects, security and maintainability"),
    Item("05", "nobrainer-security", "Security review", ("software-development", "operations"), "trust-boundary and security analysis"),
    Item("06", "nobrainer-research", "Research", ("research", "product"), "source-backed answers for uncertain or changing questions"),
    Item("07", "nobrainer-writing", "Writing", ("writing", "product", "research"), "clear, fact-preserving user-facing and technical prose"),
    Item("08", "nobrainer-browser", "Browser work", ("software-development", "operations"), "inspect and verify rendered web behavior"),
    Item("09", "nobrainer-decide", "Decision support", ("product", "research", "operations"), "compare real options against stated constraints"),
    Item("10", "nobrainer-dispatcher", "Work queue", ("software-development", "operations"), "order ready independent units and manage backpressure"),
    Item("11", "nobrainer-sessions", "Session continuity", ("software-development", "operations", "research"), "checkpoint, hand off and verify task continuity"),
    Item("12", "nobrainer-skill-doctor", "Skill quality", ("software-development",), "audit skill structure and practical behavior"),
    Item("13", "nobrainer-autoimprove", "Measured improvement", ("software-development", "product"), "run bounded baseline/candidate/holdout improvement work"),
    Item("14", "nobrainer-spec-driven-development", "Specifications", ("software-development", "product"), "define durable contracts for architectural changes"),
    Item("15", "nobrainer-rca", "Root-cause analysis", ("software-development", "operations"), "diagnose repeated or causally unclear failures"),
    Item("16", "nobrainer-team", "Capability-to-role design", ("software-development", "operations"), "assign available capabilities to bounded work"),
    Item("17", "nobrainer-codex-context", "Project context", ("software-development", "operations"), "inspect and maintain project instructions and context"),
    Item("18", "nobrainer-wiki", "Durable knowledge", ("research", "product", "operations"), "query and maintain a sourced project knowledge base"),
)
BY_ID = {item.id: item for item in ITEMS}
BY_SKILL = {item.skill: item for item in ITEMS}
PROFILE_CHOICES = ("software-development", "research", "writing", "operations", "product")
MAX_LOCAL_FILE_BYTES = 64 * 1024
MAX_API_RESPONSE_BYTES = 1_200_000


def safe_repo_url(value: str) -> str:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("repo URL must be an HTTPS URL without embedded credentials")
    if not re.fullmatch(r"[A-Za-z0-9.-]+", parsed.hostname or ""):
        raise ValueError("repo URL host is invalid")
    return value.strip().rstrip("/")


def display_repo_url(value: str) -> str:
    parsed = urlparse(value)
    return f"{parsed.scheme}://{parsed.hostname}{parsed.path.rstrip('/')}"


@dataclass(frozen=True)
class RepositoryContext:
    status: str
    signals: str = ""
    files: tuple[str, ...] = ()
    summary: str = ""
    existing_skills: tuple[str, ...] = ()


def _read_local_text(path: Path) -> str | None:
    """Read a small regular source file without following repo-owned symlinks."""

    for parent in reversed(path.parents[:-1]):
        try:
            if stat.S_ISLNK(parent.lstat().st_mode):
                return None
        except OSError:
            return None
    descriptor = -1
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_LOCAL_FILE_BYTES:
            return None
        with os.fdopen(descriptor, "rb") as handle:
            descriptor = -1
            return handle.read(MAX_LOCAL_FILE_BYTES + 1).decode("utf-8", errors="replace")
    except OSError:
        return None
    finally:
        if descriptor >= 0:
            os.close(descriptor)


REPO_TEXT_FILES = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "requirements.txt",
)
SKILL_DIRS = (".agents/skills", ".claude/skills", ".codex/skills", ".opencode/skills")


def inspect_local_repository(root: Path) -> RepositoryContext:
    root = root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"local repository path is not a directory: {root}")
    try:
        git_marker = (root / ".git").lstat()
    except OSError as exc:
        raise ValueError(f"local path is not a Git checkout: {root}") from exc
    if stat.S_ISLNK(git_marker.st_mode) or not (
        stat.S_ISDIR(git_marker.st_mode) or stat.S_ISREG(git_marker.st_mode)
    ):
        raise ValueError(f"local Git metadata path is not a regular checkout marker: {root}")
    documents: dict[str, str] = {}
    for relative in REPO_TEXT_FILES:
        value = _read_local_text(root / relative)
        if value is not None:
            documents[relative] = value
    skill_names: set[str] = set()
    for relative in SKILL_DIRS:
        folder = root / relative
        try:
            metadata = folder.lstat()
        except OSError:
            continue
        if not folder.is_dir() or folder.is_symlink():
            continue
        for child in folder.iterdir():
            if child.name in BY_SKILL and child.is_dir():
                skill_names.add(child.name)
    texts = "\n".join(documents.values())
    mention = {item.skill for item in ITEMS if re.search(rf"(?<![A-Za-z0-9_-]){re.escape(item.skill)}(?![A-Za-z0-9_-])", texts)}
    file_list = tuple(documents)
    summary = f"local files read={','.join(file_list) or 'none'}; project skill directories={len(skill_names)}"
    return RepositoryContext(
        "LOCAL_READ_ONLY",
        signals=texts,
        files=file_list,
        summary=summary,
        existing_skills=tuple(sorted(skill_names | mention)),
    )


def _safe_label(value: str, limit: int = 100) -> str:
    cleaned = "".join(char if char.isprintable() and char not in "`<>" else " " for char in value)
    return " ".join(cleaned.split())[:limit]


def github_repo_parts(repo_url: str) -> tuple[str, str] | None:
    parsed = urlparse(repo_url)
    if (parsed.hostname or "").lower() not in {"github.com", "www.github.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError("GitHub repository link must include owner and repository")
    owner, repository = parts[:2]
    repository = repository.removesuffix(".git")
    valid = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
    if not valid.fullmatch(owner) or not valid.fullmatch(repository) or owner in {".", ".."} or repository in {".", ".."}:
        raise ValueError("GitHub owner or repository name is invalid")
    return owner, repository


class _GitHubRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        target = urlparse(urljoin(request.full_url, new_url))
        if target.scheme != "https" or target.hostname != "api.github.com":
            return None
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)


def _open_github_api(request: Request, timeout: int):
    return build_opener(_GitHubRedirectHandler()).open(request, timeout=timeout)


def _github_json(endpoint: str, timeout: int = 8) -> tuple[dict[str, object] | None, str]:
    """Read a bounded GitHub REST response, preferring an existing gh login."""

    timeout = min(timeout, 4)
    gh = shutil.which("gh")
    if gh:
        try:
            result = subprocess.run(
                [gh, "api", "--hostname", "github.com", endpoint],
                cwd=ROOT,
                text=True,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
            if result.returncode == 0 and len(result.stdout.encode("utf-8")) <= MAX_API_RESPONSE_BYTES:
                value = json.loads(result.stdout)
                if isinstance(value, dict):
                    return value, "GITHUB_READ_ONLY_GH"
            if result.returncode == 0:
                return None, "RESPONSE_TOO_LARGE"
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
            pass

    request = Request(
        f"https://api.github.com/{endpoint}",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "nobrainer-tech-flow-setup-preflight",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with _open_github_api(request, timeout=timeout) as response:
            raw = response.read(MAX_API_RESPONSE_BYTES + 1)
        if len(raw) > MAX_API_RESPONSE_BYTES:
            return None, "RESPONSE_TOO_LARGE"
        value = json.loads(raw)
        if isinstance(value, dict):
            return value, "GITHUB_READ_ONLY_API"
        return None, "INVALID_RESPONSE"
    except HTTPError as exc:
        return None, f"HTTP_{exc.code}"
    except (OSError, URLError, TimeoutError, json.JSONDecodeError):
        return None, "NETWORK_UNAVAILABLE"


def inspect_github_repository(repo_url: str) -> RepositoryContext:
    parts = github_repo_parts(repo_url)
    if parts is None:
        return RepositoryContext("UNSUPPORTED_HOST")
    owner, repository = parts
    owner_path, repo_path = quote(owner, safe=""), quote(repository, safe="")
    metadata, source = _github_json(f"repos/{owner_path}/{repo_path}")
    if metadata is None:
        return RepositoryContext(source)
    readme, readme_source = _github_json(f"repos/{owner_path}/{repo_path}/readme")
    text = ""
    if readme is not None and readme.get("encoding") == "base64" and isinstance(readme.get("content"), str):
        try:
            content = base64.b64decode(readme["content"], validate=True)
            if len(content) <= MAX_LOCAL_FILE_BYTES:
                text = content.decode("utf-8", errors="replace")
        except (ValueError, TypeError):
            text = ""
    language = metadata.get("language") if isinstance(metadata.get("language"), str) else "UNKNOWN"
    description = metadata.get("description") if isinstance(metadata.get("description"), str) else ""
    topics = metadata.get("topics") if isinstance(metadata.get("topics"), list) else []
    safe_topics = [
        _safe_label(topic, 40)
        for topic in topics
        if isinstance(topic, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,40}", topic)
    ][:12]
    signals = " ".join((str(language), description[:1000], " ".join(safe_topics), text))
    summary = f"GitHub metadata read; language={_safe_label(str(language), 40)}; README={'read' if text else 'unavailable'}"
    # Never print README text, repo instructions or descriptions: all are
    # untrusted data used only as bounded keyword context for recommendations.
    return RepositoryContext(source + (f"+README_{readme_source}" if readme_source else ""), signals=signals, summary=summary)


CLIENT_CONFIGS = {
    "codex": ".codex/config.toml",
    "claude": ".claude/settings.json",
    "opencode": ".config/opencode/opencode.json",
    "copilot": ".copilot/config.json",
}


def inspect_client_config(client: str, home: Path) -> dict[str, str]:
    path = home.expanduser() / CLIENT_CONFIGS[client]
    report = {
        "config_path": str(path),
        "config_status": "MISSING",
        "configured_main_model": "UNKNOWN",
        "configured_effort": "UNKNOWN",
        "active_profile": "UNKNOWN",
        "advertised_models": "UNKNOWN",
        "callable_workers": "UNKNOWN",
        "runtime_main_and_effort": "UNKNOWN",
        "runtime_context": "UNKNOWN",
    }
    try:
        metadata = path.lstat()
    except OSError:
        return report
    if path.is_symlink() or not path.is_file() or metadata.st_size > MAX_LOCAL_FILE_BYTES:
        report["config_status"] = "PRESENT_UNREADABLE_OR_UNSUPPORTED"
        return report
    try:
        text = path.read_text(encoding="utf-8")
        if client == "codex":
            config = tomllib.loads(text)
        else:
            config = json.loads(text)
        if not isinstance(config, dict):
            report["config_status"] = "INVALID_FORMAT"
            return report
        model = config.get("model")
        effort = config.get("model_reasoning_effort") or config.get("reasoningEffort")
        if isinstance(model, str) and len(model) <= 128:
            report["configured_main_model"] = _safe_label(model, 128)
        if isinstance(effort, str) and len(effort) <= 64:
            report["configured_effort"] = _safe_label(effort, 64)
        report["config_status"] = "READ_OK_CONFIGURED_ONLY"
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, tomllib.TOMLDecodeError):
        report["config_status"] = "PARSE_ERROR"
    return report


def ask_if_missing(args: argparse.Namespace) -> None:
    print("nobrainer-tech-flow provides one task entrypoint, a required read-only capability audit, and optional specialists for implementation, research, writing, operations and product work.")
    questions = (
        ("work_profile", "Work type (software-development/research/writing/operations/product)", PROFILE_CHOICES),
        ("goal", "What outcome do you want from this setup?", None),
        ("tools", "Which client and tools do you already use?", None),
        ("existing_setup", "What relevant skills, instructions or workflows are already installed?", None),
    )
    for attribute, prompt, choices in questions:
        value = getattr(args, attribute)
        if value:
            continue
        while True:
            entered = input(f"{prompt}: ").strip()
            if entered and (choices is None or entered in choices):
                setattr(args, attribute, entered)
                break
            suffix = f" Choose one of: {', '.join(choices)}." if choices else " Enter a short answer."
            print("Please answer the question." + suffix, file=sys.stderr)


MATCH_TERMS = {
    "01": ("task", "complete", "orchestrat"),
    "02": ("model", "context", "agent", "capability"),
    "03": ("code", "build", "app", "software", "ship", "python"),
    "04": ("review", "defect", "quality", "code"),
    "05": ("security", "auth", "secret", "threat"),
    "06": ("research", "compare", "evidence", "source"),
    "07": ("write", "writing", "copy", "document", "content"),
    "08": ("browser", "web", "ui", "render"),
    "09": ("decide", "decision", "choice", "compare"),
    "10": ("queue", "parallel", "batch", "dispatch"),
    "11": ("session", "context", "handoff", "continuity"),
    "12": ("skill", "audit", "catalog", "quality"),
    "13": ("improve", "experiment", "baseline", "measure"),
    "14": ("spec", "architecture", "contract", "migration"),
    "15": ("root cause", "failure", "incident", "debug"),
    "16": ("team", "role", "delegate", "capability"),
    "17": ("project", "context", "instructions", "agents.md"),
    "18": ("wiki", "knowledge", "notes", "sources"),
}


def recommendations(
    profile: str,
    goal: str,
    tools: str,
    existing: str,
    present: set[str],
    repository: RepositoryContext | None = None,
) -> list[tuple[Item, int, str]]:
    context = f"{goal} {tools}".casefold()
    already = existing.casefold()
    repo_text = repository.signals.casefold() if repository else ""
    repo_existing = set(repository.existing_skills) if repository else set()
    ranked: list[tuple[Item, int]] = []
    for item in ITEMS:
        if item.id in {"01", "02"}:
            continue
        profile_match = profile in item.profiles
        goal_hits = [term for term in MATCH_TERMS[item.id] if term in context]
        repo_hits = [term for term in MATCH_TERMS[item.id] if term in repo_text]
        existing_hit = (
            item.skill.casefold() in already
            or item.label.casefold() in already
            or item.skill in repo_existing
        )
        actual_present = item.id in present
        score = 4 + (3 if profile_match else 0) + (2 if goal_hits else 0)
        if any(term in tools.casefold() for term in MATCH_TERMS[item.id]):
            score += 1
        if repo_hits:
            score += 1
        if existing_hit or actual_present:
            score -= 3
        score = max(1, min(10, score))
        if profile_match or goal_hits:
            reasons = []
            if profile_match:
                reasons.append(f"fits {profile}")
            if goal_hits:
                reasons.append("task/tool match: " + ", ".join(goal_hits[:3]))
            if repo_hits:
                reasons.append("repository context: " + ", ".join(repo_hits[:3]))
            if existing_hit or actual_present:
                reasons.append("possible overlap; verify current setup before adding")
            ranked.append((item, score, "; ".join(reasons)))
    # The core skill and standard first-setup audit are required and shown
    # separately; keep the optional recommendation list useful and short.
    return sorted(ranked, key=lambda row: (-row[1], row[0].id))[:6]


def installed_ids(destination: Path) -> set[str]:
    found: set[str] = set()
    for item in ITEMS:
        target = destination / item.skill
        if target.is_symlink():
            try:
                if target.resolve(strict=True) == (SKILLS_DIR / item.skill).resolve(strict=True):
                    found.add(item.id)
            except FileNotFoundError:
                continue
    return found


def target_state(destination: Path, item: Item) -> str:
    target = destination / item.skill
    if not target.exists() and not target.is_symlink():
        return "MISSING"
    if target.is_symlink():
        try:
            if target.resolve(strict=True) == (SKILLS_DIR / item.skill).resolve(strict=True):
                return "CURRENT"
        except FileNotFoundError:
            pass
    return "CONFLICT"


def selected_ids(raw: str | None) -> list[str]:
    if not raw:
        return []
    chosen = [part.strip().zfill(2) for part in raw.split(",") if part.strip()]
    if not chosen or len(chosen) != len(set(chosen)):
        raise ValueError("selection must be a comma-separated list of unique IDs")
    unknown = sorted(set(chosen) - set(BY_ID))
    if unknown:
        raise ValueError(f"unknown selection ID(s): {', '.join(unknown)}")
    return sorted(chosen)


def run(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    output = result.stdout + result.stderr
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    return result.returncode, output


def remove_exact_created_links(destination: Path, names: list[str]) -> None:
    for name in names:
        if name not in BY_SKILL:
            continue
        target = destination / name
        try:
            if target.is_symlink() and target.resolve(strict=True) == (SKILLS_DIR / name).resolve(strict=True):
                target.unlink()
        except FileNotFoundError:
            continue


def state_path(home: Path, override: Path | None, client: str) -> Path:
    if override is not None:
        return override.expanduser()
    suffix = STATE_NAME.removesuffix(".json")
    return (home / f"{suffix}-{client}.json").expanduser()


def legacy_state_path(home: Path, override: Path | None) -> Path | None:
    return None if override is not None else home / STATE_NAME


def legacy_state_client(state: dict[str, object], home: Path) -> str | None:
    """Infer the owner of a v1 single-client state without mutating it."""

    destinations = {
        "codex": home / ".agents" / "skills",
        "claude": home / ".claude" / "skills",
        "opencode": home / ".config" / "opencode" / "skills",
        "copilot": home / ".copilot" / "skills",
    }
    destination = state.get("destination")
    if isinstance(destination, str):
        resolved = Path(destination).expanduser().resolve()
        for client, path in destinations.items():
            if resolved == path.resolve():
                return client
    profile = state.get("profile")
    target = profile.get("target") if isinstance(profile, dict) else None
    if isinstance(target, str):
        targets = {
            "codex": home / ".codex" / "AGENTS.md",
            "claude": home / ".claude" / "CLAUDE.md",
            "opencode": home / ".config" / "opencode" / "AGENTS.md",
            "copilot": home / ".copilot" / "copilot-instructions.md",
        }
        for client, path in targets.items():
            if Path(target).expanduser() == path:
                return client
    return None


def read_state_file(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"setup state path is not a regular file: {path}")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(loaded, dict)
        or not isinstance(loaded.get("destination"), str)
        or not isinstance(loaded.get("created_skills"), list)
        or not isinstance(loaded.get("profile"), dict)
        or any(not isinstance(name, str) or name not in BY_SKILL for name in loaded.get("created_skills", []))
    ):
        raise ValueError(f"refusing to overwrite unrecognized setup state: {path}")
    return loaded


def save_state(path: Path, state: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(state, indent=2) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def rollback(args: argparse.Namespace, state_file: Path) -> int:
    try:
        metadata = state_file.lstat()
    except FileNotFoundError:
        print(f"ERROR: rollback state not found: {state_file}", file=sys.stderr)
        return 3
    if state_file.is_symlink() or not state_file.is_file():
        print(f"ERROR: rollback state must be a regular file: {state_file}", file=sys.stderr)
        return 3
    state = json.loads(state_file.read_text(encoding="utf-8"))
    if not isinstance(state, dict) or not isinstance(state.get("destination"), str):
        print("ERROR: invalid rollback state", file=sys.stderr)
        return 3
    destination = Path(state["destination"])
    created = state.get("created_skills", [])
    if not isinstance(created, list) or len(created) != len(set(created)) or any(name not in BY_SKILL for name in created):
        print("ERROR: rollback state contains invalid skill ownership entries", file=sys.stderr)
        return 3
    profile = state.get("profile", {})
    target_path = Path(str(profile.get("target", ""))) if profile else None
    backup = profile.get("backup") if profile else None
    if target_path:
        allowed_paths = {
            args.home / ".codex" / "AGENTS.md",
            args.home / ".claude" / "CLAUDE.md",
            args.home / ".config" / "opencode" / "AGENTS.md",
            args.home / ".copilot" / "copilot-instructions.md",
        }
        if target_path not in allowed_paths:
            print(f"ERROR: refusing unexpected personalization target: {target_path}", file=sys.stderr)
            return 3
        if backup:
            backup_file = Path(str(backup))
            if backup_file.parent != target_path.parent or not backup_file.name.startswith(target_path.name + ".bak."):
                print(f"ERROR: refusing unexpected personalization backup: {backup_file}", file=sys.stderr)
                return 3
            try:
                backup_metadata = backup_file.lstat()
            except FileNotFoundError:
                backup_metadata = None
            if backup_metadata is None or backup_file.is_symlink() or not backup_file.is_file():
                print(f"ERROR: personalization backup must be a regular file: {backup_file}", file=sys.stderr)
                return 3
        expected_hash = profile.get("written_sha256")
        if target_path and (not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash)):
            print("ERROR: invalid personalization readback hash in rollback state", file=sys.stderr)
            return 3
    if target_path and backup and not target_path.exists():
        print(f"PRESERVED: personalization target is missing: {target_path}")
        return 3
    if target_path and target_path.exists():
        current = target_path.read_bytes()
        expected_hash = profile.get("written_sha256")
        if hashlib.sha256(current).hexdigest() != expected_hash:
            print(f"PRESERVED: personalization changed since setup: {target_path}")
            return 3
        if backup and not Path(str(backup)).is_file():
            print(f"ERROR: personalization backup missing: {backup}", file=sys.stderr)
            return 3
    for name in created:
        target = destination / name
        if target.is_symlink():
            try:
                matches = target.resolve(strict=True) == (SKILLS_DIR / name).resolve(strict=True)
            except FileNotFoundError:
                matches = False
            if not matches:
                print(f"PRESERVED: changed target {target}")
                return 3
        elif target.exists():
            print(f"PRESERVED: changed target {target}")
            return 3
    print(f"ROLLBACK_PLAN: remove={','.join(created) or 'none'}; personalization={target_path or 'none'}; backup={backup or 'none'}")
    if not args.apply:
        print(f"ROLLBACK_DRY_RUN: no files changed; pass --apply to reverse setup from {state_file}")
        return 0
    removed: list[str] = []
    for name in created:
        target = destination / name
        source = SKILLS_DIR / name
        if target.is_symlink() and target.resolve(strict=True) == source.resolve(strict=True):
            target.unlink()
            removed.append(name)
        elif target.exists() or target.is_symlink():
            print(f"PRESERVED: changed target {target}")

    if target_path and target_path.exists():
        current = target_path.read_bytes()
        backup = profile.get("backup")
        if backup:
            backup_path = Path(str(backup))
            original = backup_path.read_bytes()
            mode = target_path.stat().st_mode & 0o777
            descriptor, temporary_name = tempfile.mkstemp(prefix=f".{target_path.name}.rollback.", dir=target_path.parent)
            temporary = Path(temporary_name)
            try:
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(original)
                    handle.flush()
                    os.fsync(handle.fileno())
                temporary.chmod(mode)
                os.replace(temporary, target_path)
            except Exception:
                temporary.unlink(missing_ok=True)
                raise
            if target_path.read_bytes() != original:
                raise OSError(f"personalization restore readback mismatch: {target_path}")
            print(f"RESTORED: {target_path} from {backup_path}")
        else:
            content = current.decode("utf-8")
            start = content.find("<!-- NOBRAINER-TECH-FLOW:START -->")
            end_marker = "<!-- NOBRAINER-TECH-FLOW:END -->"
            end = content.find(end_marker)
            if start < 0 or end < start:
                print(f"PRESERVED: managed block not found in {target_path}")
                return 3
            end += len(end_marker)
            content = content[:start] + content[end:]
            if content.strip():
                target_path.write_text(content, encoding="utf-8")
                if target_path.read_text(encoding="utf-8") != content:
                    raise OSError(f"personalization rollback readback mismatch: {target_path}")
            else:
                target_path.unlink()
                if target_path.exists() or target_path.is_symlink():
                    raise OSError(f"personalization file remained after rollback: {target_path}")
            print(f"REMOVED_MANAGED_BLOCK: {target_path}")

    if state_file.lstat().st_ino != metadata.st_ino or state_file.lstat().st_dev != metadata.st_dev:
        print(f"ERROR: rollback state changed during rollback; preserved at {state_file}", file=sys.stderr)
        return 3
    for name in removed:
        target = destination / name
        if target.exists() or target.is_symlink():
            raise OSError(f"skill rollback readback mismatch: {target}")
    state_file.unlink()
    try:
        destination.rmdir()
    except OSError:
        pass
    print(f"ROLLBACK_READBACK: removed={','.join(removed) or 'none'}; profile=restored")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-url", required=True, help="repository link supplied for setup context")
    parser.add_argument("--repo-path", type=Path, help="local checkout to inspect instead of contacting GitHub")
    parser.add_argument("--offline", action="store_true", help="skip network lookup and use only supplied context and local paths")
    parser.add_argument("--client", choices=("codex", "claude", "opencode", "copilot"), required=True)
    parser.add_argument("--work-profile", choices=PROFILE_CHOICES)
    parser.add_argument("--goal", help="task or outcome the setup should support")
    parser.add_argument("--tools", help="client and tools already in use")
    parser.add_argument("--existing-setup", help="existing skills or workflow setup")
    parser.add_argument("--selection", help="comma-separated recommendation IDs; required for --apply")
    parser.add_argument("--preferences", help="short owner-approved persistent setup preference")
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--dest", type=Path, help="skill target directory override for controlled setup/tests")
    parser.add_argument("--state-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--apply", action="store_true", help="apply the reviewed selected subset")
    parser.add_argument("--rollback", action="store_true", help="reverse the most recent managed setup")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        args.home = args.home.expanduser()
        repo_url = safe_repo_url(args.repo_url)
        state = state_path(args.home, args.state_file, args.client)
        legacy_state = legacy_state_path(args.home, args.state_file)
        if args.rollback:
            if not state.exists() and not state.is_symlink() and legacy_state is not None and legacy_state.exists():
                legacy = read_state_file(legacy_state)
                legacy_owner = legacy_state_client(legacy, args.home)
                if legacy_owner is None:
                    print(f"ERROR: legacy rollback state has no provable client owner: {legacy_state}", file=sys.stderr)
                    return 3
                if legacy_owner != args.client:
                    print(f"ERROR: legacy rollback state belongs to {legacy_owner}; no {args.client} state exists", file=sys.stderr)
                    return 3
                state = legacy_state
            return rollback(args, state)
        previous: dict[str, object] = {}
        try:
            state_metadata = state.lstat()
        except FileNotFoundError:
            state_metadata = None
        if state_metadata is not None:
            previous = read_state_file(state)
        elif legacy_state is not None and legacy_state.exists():
            legacy = read_state_file(legacy_state)
            legacy_owner = legacy_state_client(legacy, args.home)
            if legacy_owner is None:
                raise ValueError(f"legacy setup state has no provable client owner; preserve and inspect it: {legacy_state}")
            if legacy_owner == args.client:
                previous = legacy
                print(f"LEGACY_STATE_MIGRATION: this {args.client} setup will be copied to {state}; original retained at {legacy_state}")
            else:
                print(f"LEGACY_STATE_PRESERVED: belongs to {legacy_owner}; current client={args.client}")
        ask_if_missing(args)
        if args.apply and not args.selection:
            raise ValueError("--apply requires an explicit --selection")
        if args.preferences and (
            len(args.preferences) > 240
            or any(char in args.preferences for char in ("\n", "\r", "`", "<", ">"))
        ):
            raise ValueError("preferences must be a single line of at most 240 safe characters")
        if args.repo_path is not None:
            repository_context = inspect_local_repository(args.repo_path)
        elif args.offline:
            repository_context = RepositoryContext("OFFLINE")
        else:
            repository_context = inspect_github_repository(repo_url)
        client_destinations = {
            "codex": args.home / ".agents" / "skills",
            "claude": args.home / ".claude" / "skills",
            "opencode": args.home / ".config" / "opencode" / "skills",
            "copilot": args.home / ".copilot" / "skills",
        }
        destination = (args.dest or client_destinations[args.client]).expanduser().resolve()
        if previous and Path(str(previous["destination"])).expanduser().resolve() != destination:
            raise ValueError(f"existing setup state belongs to a different skills destination: {previous['destination']}")
        before = installed_ids(destination)
        ranked = recommendations(
            args.work_profile,
            args.goal,
            args.tools,
            args.existing_setup,
            before,
            repository_context,
        )
        print(f"REPOSITORY: {display_repo_url(repo_url)}")
        print(f"REPOSITORY_SOURCE: {repository_context.status}; {repository_context.summary or 'repository content unavailable; using supplied answers only'}")
        if repository_context.status.startswith("LOCAL_") or repository_context.status.startswith("GITHUB_"):
            print("REPOSITORY_TRUST: README and instruction content treated as untrusted data; no scripts, hooks or installers executed.")
        for name, value in (("goal", args.goal), ("tools", args.tools), ("existing setup", args.existing_setup)):
            if len(value) > 240 or any(ord(char) < 0x20 for char in value):
                raise ValueError(f"{name} must be a single line of at most 240 characters")
        print(f"NEEDS: profile={args.work_profile}; goal={args.goal}; tools={args.tools}; existing={args.existing_setup}")
        capability = inspect_client_config(args.client, args.home)
        print(
            "CLIENT_CAPABILITY_AUDIT: "
            f"client={args.client}; config_status={capability['config_status']}; "
            f"config_path={capability['config_path']}; "
            f"configured_main={capability['configured_main_model']}; "
            f"configured_effort={capability['configured_effort']}; "
            "active_profile=UNKNOWN; advertised_models=UNKNOWN; callable_workers=UNKNOWN; "
            "runtime_main_and_effort=UNKNOWN; runtime_context=UNKNOWN"
        )
        audit_skill = SKILLS_DIR / "nobrainer-auto-fine-tune" / "SKILL.md"
        if not audit_skill.is_file():
            raise ValueError(f"required Auto Fine Tune skill is missing: {audit_skill}")
        skill_text = audit_skill.read_text(encoding="utf-8")
        if "Preserve the owner's choice" not in skill_text or "Discover this client's actual capabilities" not in skill_text:
            raise ValueError(f"Auto Fine Tune audit instructions are incomplete: {audit_skill}")
        print("CAPABILITY_AUDIT: skill=nobrainer-auto-fine-tune; MAIN=UNKNOWN (preserved); effort=UNKNOWN; callable workers=UNKNOWN; runtime context=UNKNOWN; measurement=UNMEASURED")
        audit = SKILLS_DIR / "nobrainer-auto-fine-tune" / "references" / "capacity-audit.md"
        if not audit.is_file():
            raise ValueError(f"required Auto Fine Tune audit reference is missing: {audit}")
        audit_text = audit.read_text(encoding="utf-8")
        if "Separate four evidence layers" not in audit_text or "Client adapters" not in audit_text:
            raise ValueError(f"Auto Fine Tune capacity-audit reference is incomplete: {audit}")
        print(f"AUDIT_REFERENCE_READ: {audit.relative_to(ROOT)}")
        print("REQUIRED: 01,02 (nobrainer-tech-flow entrypoint plus standard read-only capability audit)")
        print("AVAILABLE OPTIONS:")
        for item in ITEMS:
            print(f"{item.id} {item.label}: {item.reason}")
        print("RECOMMENDATIONS (fit is a task-specific heuristic, not a benchmark):")
        for item, score, reason in ranked:
            conflict = target_state(destination, item)
            print(
                f"{item.id} {item.label} | Fit (heuristic)={score}/10 | {reason} | "
                f"Dependencies=01,02 | Target={conflict} | "
                f"Change scope=install {item.skill} and update selected client nobrainer-tech-flow instructions"
            )
        selection_text = args.selection
        if not selection_text and sys.stdin.isatty():
            selection_text = input("Choose any recommendation IDs to install (comma-separated, blank to stop): ").strip()
        chosen = selected_ids(selection_text)
        if not chosen:
            print("DRY_RUN: no files changed; choose IDs with --selection and review this plan.")
            return 0
        install_ids = sorted(set(chosen) | {"01", "02"})
        install_names = [BY_ID[item_id].skill for item_id in install_ids]
        new_skills = [name for name in install_names if BY_SKILL[name].id not in before]
        print(f"SELECTED: {','.join(chosen)}")
        print(f"INSTALL_SET: {','.join(install_ids)} (includes required 01,02)")
        personalization_client = args.client
        profile_args = [sys.executable, str(PERSONALIZATION), "--client", personalization_client, "--home", str(args.home)]
        if args.preferences:
            profile_args.extend(("--preferences", args.preferences))
        code, profile_output = run(profile_args)
        if code:
            return code
        inherited = "INHERITS_CODEX:" in profile_output
        if inherited and args.preferences:
            personalization_client = "codex"
            profile_args = [sys.executable, str(PERSONALIZATION), "--client", personalization_client, "--home", str(args.home), "--preferences", args.preferences]
            code, profile_output = run(profile_args)
            if code:
                return code
        profile_target = {
            "codex": args.home / ".codex" / "AGENTS.md",
            "claude": args.home / ".claude" / "CLAUDE.md",
            "opencode": args.home / ".config" / "opencode" / "AGENTS.md",
            "copilot": args.home / ".copilot" / "copilot-instructions.md",
        }[personalization_client]
        old_profile = previous.get("profile", {})
        if old_profile.get("target") and Path(str(old_profile["target"])) != profile_target:
            raise ValueError(f"existing setup state belongs to a different personalization target: {old_profile['target']}")
        if not args.apply:
            return 0
        # Inspect every target before writing any of them. This keeps a later
        # conflict from leaving a partial selection installed.
        for name in install_names:
            command = [sys.executable, str(ROOT / "scripts" / "install_skills.py"), "--client", args.client, "--dest", str(destination), "--skill", name]
            code, _ = run(command)
            if code:
                return code
        if args.apply:
            for name in install_names:
                command = [sys.executable, str(ROOT / "scripts" / "install_skills.py"), "--client", args.client, "--dest", str(destination), "--skill", name, "--apply"]
                code, _ = run(command)
                if code:
                    remove_exact_created_links(destination, new_skills)
                    return code
        if not inherited or args.preferences:
            profile_args.append("--apply")
            code, profile_output = run(profile_args)
            if code:
                # A profile write can race after preflight. Reverse only the
                # exact new symlinks from this invocation before returning.
                remove_exact_created_links(destination, new_skills)
                return code
        backup_match = re.search(r"^BACKUP: (.+)$", profile_output, re.MULTILINE)
        if inherited and not args.preferences:
            profile = {}
        else:
            profile = {
                "target": str(profile_target),
                "backup": backup_match.group(1) if backup_match else old_profile.get("backup"),
                "written_sha256": hashlib.sha256(profile_target.read_bytes()).hexdigest(),
            }
        created = sorted(set(previous.get("created_skills", [])) | {name for name in new_skills if (destination / name).is_symlink()})
        save_state(state, {"destination": str(destination), "created_skills": created, "profile": profile})
        after = installed_ids(destination)
        actual_added = sorted(after - before)
        expected_added = sorted(BY_SKILL[name].id for name in new_skills)
        if actual_added != expected_added:
            print(f"ERROR: install readback mismatch expected={expected_added} actual={actual_added}", file=sys.stderr)
            return 3
        for item_id in set(BY_ID) - set(install_ids) - before:
            if (destination / BY_ID[item_id].skill).exists() or (destination / BY_ID[item_id].skill).is_symlink():
                print(f"ERROR: unselected item was installed: {item_id}", file=sys.stderr)
                return 3
        print(f"READBACK: installed={','.join(sorted(after))}; rejected/unselected remain absent unless previously present")
        if profile.get("target"):
            print(f"PREFERENCE_READBACK: {profile_target}; hash={profile['written_sha256']}")
        else:
            print("PREFERENCE_READBACK: inherited from Codex global instructions; no duplicate block written")
        print(f"ROLLBACK_STATE: {state}")
        print("CAPABILITY_AUDIT_LIMIT: host runtime evidence remains UNKNOWN; run the loaded skill in the active client before recommending route changes.")
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
