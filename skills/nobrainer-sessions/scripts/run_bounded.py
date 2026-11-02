#!/usr/bin/env python3
"""Run one explicit command with bounded wall time and captured output.

This is a command wrapper, not a sandbox or a global agent/runtime limit. On
POSIX it owns a new process group so timeout and output-limit cleanup includes
descendants. Receipts omit argv unless the caller explicitly records it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import errno
import json
import math
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import tempfile
import time
from typing import BinaryIO


EXIT_TIMEOUT = 124
EXIT_OUTPUT_LIMIT = 125
EXIT_RUNNER_ERROR = 70
TERM_GRACE_SECONDS = 0.30
FINAL_DRAIN_SECONDS = 0.50
READ_CHUNK_BYTES = 65_536


def positive_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or not parsed > 0:
        raise argparse.ArgumentTypeError("must be finite and greater than zero")
    return parsed


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an argv command with wall-time and combined-output caps."
    )
    parser.add_argument("--wall-seconds", required=True, type=positive_float)
    parser.add_argument("--max-output-bytes", required=True, type=positive_int)
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument(
        "--record-argv",
        action="store_true",
        help="Include argv in the receipt; disabled by default to avoid leaking secrets.",
    )
    parser.add_argument(
        "--stdin-file",
        type=Path,
        default=None,
        help="Feed this file to the command's stdin; without it stdin is empty.",
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.stdin_file is not None and not args.stdin_file.is_file():
        parser.error(f"--stdin-file is not a readable file: {args.stdin_file}")
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("an explicit argv command is required after --")
    if os.name != "posix":
        parser.error(
            "unsupported platform: process-tree cleanup is implemented only for POSIX"
        )
    args.cwd = args.cwd.expanduser().resolve()
    if not args.cwd.is_dir():
        parser.error(f"cwd is not a directory: {args.cwd}")
    args.receipt = Path(os.path.abspath(os.path.expanduser(str(args.receipt))))
    if args.receipt.exists() or args.receipt.is_symlink():
        parser.error(f"receipt already exists; refusing to overwrite: {args.receipt}")
    if not args.receipt.parent.is_dir():
        parser.error(f"receipt parent is not a directory: {args.receipt.parent}")
    return args


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="milliseconds").replace(
        "+00:00", "Z"
    )


def signal_group(process_group: int, sig: signal.Signals) -> bool:
    try:
        os.killpg(process_group, sig)
        return True
    except ProcessLookupError:
        return False


def emergency_cleanup(process: subprocess.Popen[bytes], process_group: int) -> None:
    """Best-effort bounded cleanup used when streaming exits unexpectedly."""

    signal_group(process_group, signal.SIGTERM)
    try:
        process.wait(timeout=TERM_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        pass
    signal_group(process_group, signal.SIGKILL)
    try:
        process.wait(timeout=FINAL_DRAIN_SECONDS)
    except subprocess.TimeoutExpired:
        pass


def atomic_write_new(path: Path, payload: dict[str, object]) -> None:
    """Publish a complete receipt without replacing an existing directory entry."""

    encoded = (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise RuntimeError(f"receipt appeared during run; not overwritten: {path}") from exc
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            try:
                os.fsync(directory_fd)
            except OSError as exc:
                if exc.errno not in {errno.EINVAL, errno.ENOTSUP, errno.EPERM}:
                    raise
        finally:
            os.close(directory_fd)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def close_registered(
    selector: selectors.BaseSelector, streams: dict[int, tuple[str, BinaryIO]]
) -> None:
    for file_number, (_, stream) in list(streams.items()):
        try:
            selector.unregister(file_number)
        except (KeyError, ValueError):
            pass
        stream.close()
        streams.pop(file_number, None)


def run_bounded(
    args: argparse.Namespace,
) -> tuple[dict[str, object], int, dict[str, bytes]]:
    started_utc = utc_now()
    started = time.monotonic()
    stdin_file = getattr(args, "stdin_file", None)
    stdin_handle = (
        open(stdin_file, "rb") if stdin_file is not None else subprocess.DEVNULL
    )
    try:
        process = subprocess.Popen(
            args.command,
            cwd=args.cwd,
            stdin=stdin_handle,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            close_fds=True,
        )
    finally:
        if stdin_handle is not subprocess.DEVNULL:
            stdin_handle.close()
    process_group = process.pid
    selector: selectors.BaseSelector | None = None
    streams: dict[int, tuple[str, BinaryIO]] = {}
    captured = {"stdout": bytearray(), "stderr": bytearray()}
    emitted = {"stdout": 0, "stderr": 0}
    observed = {"stdout": 0, "stderr": 0}
    truncated = {"stdout": False, "stderr": False}
    stop_reason: str | None = None
    term_sent = False
    kill_sent = False
    cleanup_after_leader_exit = False
    cleanup_started = False
    term_deadline: float | None = None
    final_drain_deadline: float | None = None
    leader_exit_seen: float | None = None
    kill_attempted = False
    loop_cleanup_complete = False

    try:
        selector = selectors.DefaultSelector()
        for name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
            assert stream is not None
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
            streams[stream.fileno()] = (name, stream)
        while True:
            now = time.monotonic()
            leader_code = process.poll()
            if leader_code is not None and leader_exit_seen is None:
                leader_exit_seen = now
            if (
                stop_reason is None
                and leader_exit_seen is None
                and now - started >= args.wall_seconds
            ):
                stop_reason = "timed_out"
            if stop_reason is not None and not cleanup_started:
                cleanup_started = True
                term_sent = signal_group(process_group, signal.SIGTERM)
                term_deadline = now + TERM_GRACE_SECONDS
                final_drain_deadline = term_deadline + FINAL_DRAIN_SECONDS
            if (
                stop_reason is None
                and leader_exit_seen is not None
                and not cleanup_started
            ):
                cleanup_after_leader_exit = True
                cleanup_started = True
                term_sent = signal_group(process_group, signal.SIGTERM)
                term_deadline = now + TERM_GRACE_SECONDS
                final_drain_deadline = term_deadline + FINAL_DRAIN_SECONDS
            if term_deadline is not None and now >= term_deadline and not kill_attempted:
                kill_attempted = True
                kill_sent = signal_group(process_group, signal.SIGKILL)
            leader_code = process.poll()
            if cleanup_started and kill_attempted and leader_code is not None and not streams:
                loop_cleanup_complete = True
                break
            if (
                final_drain_deadline is not None
                and kill_attempted
                and now >= final_drain_deadline
            ):
                for name, _ in streams.values():
                    truncated[name] = True
                loop_cleanup_complete = True
                break

            if cleanup_started:
                deadlines = [final_drain_deadline]
                if not kill_attempted:
                    deadlines.append(term_deadline)
                next_deadline = min(
                    deadline for deadline in deadlines if deadline is not None
                )
            else:
                next_deadline = started + args.wall_seconds
            wait = max(0.0, min(0.05, next_deadline - now))
            if streams:
                events = selector.select(wait)
            else:
                time.sleep(wait)
                events = ()
            for key, _ in events:
                file_number = key.fd
                name, stream = streams[file_number]
                remaining = args.max_output_bytes - sum(emitted.values())
                read_size = min(READ_CHUNK_BYTES, max(1, remaining + 1))
                try:
                    chunk = os.read(file_number, read_size)
                except BlockingIOError:
                    continue
                if not chunk:
                    selector.unregister(file_number)
                    stream.close()
                    streams.pop(file_number, None)
                    continue
                observed[name] += len(chunk)
                retained = chunk[:remaining]
                if retained:
                    captured[name].extend(retained)
                    emitted[name] += len(retained)
                if len(chunk) > len(retained):
                    truncated[name] = True
                    stop_reason = "output_limit"
    finally:
        if selector is not None:
            close_registered(selector, streams)
            selector.close()
        for stream in (process.stdout, process.stderr):
            if stream is not None and not stream.closed:
                stream.close()
        if not loop_cleanup_complete:
            emergency_cleanup(process, process_group)

    if process.poll() is None:
        emergency_cleanup(process, process_group)
    try:
        exit_code = process.wait(timeout=FINAL_DRAIN_SECONDS)
    except subprocess.TimeoutExpired:
        kill_sent = signal_group(process_group, signal.SIGKILL) or kill_sent
        exit_code = process.wait(timeout=FINAL_DRAIN_SECONDS)

    ended = time.monotonic()
    if stop_reason == "timed_out":
        status = "timed_out"
        runner_exit = EXIT_TIMEOUT
    elif stop_reason == "output_limit":
        status = "output_limit"
        runner_exit = EXIT_OUTPUT_LIMIT
    elif exit_code == 0:
        status = "completed"
        runner_exit = 0
    else:
        status = "failed"
        runner_exit = (
            exit_code
            if 0 < exit_code <= 255
            else min(255, 128 - exit_code)
            if exit_code < 0
            else EXIT_RUNNER_ERROR
        )

    receipt: dict[str, object] = {
        "schema_version": 1,
        "status": status,
        "started_at": started_utc,
        "ended_at": utc_now(),
        "duration_seconds": round(ended - started, 6),
        "cwd": str(args.cwd),
        "argv_recorded": bool(args.record_argv),
        "wall_seconds_limit": args.wall_seconds,
        "output_bytes_limit": args.max_output_bytes,
        "stdout_bytes_observed": observed["stdout"],
        "stderr_bytes_observed": observed["stderr"],
        "stdout_bytes_captured": emitted["stdout"],
        "stderr_bytes_captured": emitted["stderr"],
        "stdout_truncated": truncated["stdout"],
        "stderr_truncated": truncated["stderr"],
        "exit_code": exit_code if exit_code >= 0 else None,
        "signal": -exit_code if exit_code < 0 else None,
        "timed_out": stop_reason == "timed_out",
        "output_limit_reached": stop_reason == "output_limit",
        "termination": {
            "sent_term": term_sent,
            "sent_kill": kill_sent,
            "descendant_cleanup_attempted_after_leader_exit": cleanup_after_leader_exit,
        },
        "scope": "explicit_child_process_group_only",
        "model_tokens": "UNKNOWN",
        "model_cost": "UNKNOWN",
    }
    if args.record_argv:
        receipt["argv"] = args.command
    return receipt, runner_exit, {
        "stdout": bytes(captured["stdout"]),
        "stderr": bytes(captured["stderr"]),
    }


def forward_captured(captured: dict[str, bytes]) -> dict[str, object]:
    """Forward already-bounded output after the owned process group is cleaned up."""

    results: dict[str, object] = {}
    for name, destination in (
        ("stdout", sys.stdout.buffer),
        ("stderr", sys.stderr.buffer),
    ):
        try:
            destination.write(captured[name])
            destination.flush()
            results[name] = "forwarded"
        except OSError as exc:
            results[name] = f"failed_errno_{exc.errno}"
            try:
                null_fd = os.open(os.devnull, os.O_WRONLY)
                try:
                    os.dup2(null_fd, destination.fileno())
                finally:
                    os.close(null_fd)
            except OSError:
                pass
    return results


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        receipt, exit_code, captured = run_bounded(args)
        forwarding = forward_captured(captured)
        receipt["output_forwarding"] = forwarding
        atomic_write_new(args.receipt, receipt)
        if any(str(value).startswith("failed_") for value in forwarding.values()):
            return EXIT_RUNNER_ERROR
        return exit_code
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f"run_bounded: {exc}", file=sys.stderr)
        return EXIT_RUNNER_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
