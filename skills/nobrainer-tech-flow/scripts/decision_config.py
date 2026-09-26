#!/usr/bin/env python3
"""Inspect or explicitly set non-secret optional decision preferences."""
import argparse
import json
import os
from pathlib import Path
import tempfile


DEFAULT = {
    "schema_version": 1,
    "provider": "core",
    "mode": "off",
    "model": None,
    "timeout_seconds": 10,
    "max_calls_per_run": 0,
}
MODELS = {"core": None, "jev": "jev-latest", "laya": "aac6fef/laya-multilingual-mlx"}


def validate(value):
    if not isinstance(value, dict) or set(value) != set(DEFAULT):
        raise ValueError("Configuration fields do not match schema version 1")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise ValueError("Unsupported schema version")
    if not isinstance(value["provider"], str) or value["provider"] not in MODELS or value["mode"] not in ("off", "shadow"):
        raise ValueError("Unknown provider or mode")
    if value["provider"] == "core":
        if value["mode"] != "off" or value["model"] is not None or value["max_calls_per_run"] != 0:
            raise ValueError("Core profile requires off mode, no model and zero calls")
    elif not isinstance(value["model"], str) or not value["model"].strip():
        raise ValueError("An optional provider requires a model identifier")
    for field, low, high in (("timeout_seconds", 1, 120), ("max_calls_per_run", 0, 100)):
        if type(value[field]) is not int or not low <= value[field] <= high:
            raise ValueError(f"Invalid {field}")
    if value["mode"] == "shadow" and value["max_calls_per_run"] == 0:
        raise ValueError("Shadow mode requires a positive call limit")
    return value


def read(path):
    if not path.exists():
        return {"status": "DEFAULT_CORE", "configured": False, "config": dict(DEFAULT)}
    try:
        value = validate(json.loads(path.read_text(encoding="utf-8")))
        return {"status": "CONFIGURED", "configured": True, "config": value}
    except (OSError, ValueError, TypeError):
        return {"status": "INVALID_CONFIG_CORE_FALLBACK", "configured": True, "config": dict(DEFAULT)}


def configure(path, provider, mode, model, timeout, calls):
    value = validate({"schema_version": 1, "provider": provider, "mode": mode,
                      "model": model, "timeout_seconds": timeout, "max_calls_per_run": calls})
    if path.is_symlink():
        raise ValueError("Refusing to replace a symlink configuration")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".flow-config-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return read(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(".nobrainer/flow.json"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show")
    setup = sub.add_parser("setup")
    setup.add_argument("--non-interactive", action="store_true")
    setter = sub.add_parser("set")
    setter.add_argument("--provider", choices=tuple(MODELS), required=True)
    setter.add_argument("--mode", choices=("off", "shadow"), default="off")
    setter.add_argument("--model")
    setter.add_argument("--timeout", type=int, default=10)
    setter.add_argument("--max-calls", type=int, default=0)
    args = parser.parse_args()
    try:
        if args.command == "setup":
            result = read(args.config)
            if not result["configured"]:
                import sys
                choice = "core"
                if not args.non_interactive and sys.stdin.isatty():
                    choice = input("Optional decisions: enter core (default), jev (remote), or laya (local): ").strip().lower() or "core"
                if choice not in MODELS:
                    raise ValueError("Unknown choice")
                # Remember provider choice without authorizing data or charges.
                result = configure(args.config, choice, "off", MODELS[choice], 10, 0)
        else:
            result = read(args.config) if args.command == "show" else configure(
            args.config, args.provider, args.mode, args.model or MODELS[args.provider],
            args.timeout, args.max_calls)
    except (ValueError, OSError):
        print(json.dumps({"status": "CONFIG_NOT_SAVED"}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
