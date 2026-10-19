#!/usr/bin/env python3
"""Local, unsigned execution evidence for an explicit input scope.

Capture reuses run_bounded; check never executes the recorded command. Neither
mode decides test coverage, task acceptance or human approval.
"""
from __future__ import annotations

import argparse
import errno
import base64
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import secrets
import sys

MAX_ENTRIES = 1000
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_RECEIPT_BYTES = 4 * 1024 * 1024
MAX_OUTPUT_BYTES = 256 * 1024


class EvidenceError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or len(value.encode('utf-8')) > 512:
        raise EvidenceError('invalid relative input path')
    if '\\' in value or any(ord(c) < 32 for c in value):
        raise EvidenceError('unsafe input path')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or str(path) != value or len(path.parts) > 32:
        raise EvidenceError('input paths must be normalized and relative to root')
    return value


def scope_paths(values: object) -> list[str]:
    if not isinstance(values, list) or not 1 <= len(values) <= 64:
        raise EvidenceError('input scope must contain 1..64 relative paths')
    paths = [relative_path(p) for p in values]
    if len(set(paths)) != len(paths):
        raise EvidenceError('duplicate input scope')
    return sorted(paths)


def require_posix() -> None:
    if os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW'):
        raise EvidenceError('unsupported platform: POSIX no-follow file access is required')


def snapshot(root: Path, scope: list[str]) -> dict[str, dict[str, object]]:
    """Walk selected entries through directory descriptors, never through links."""
    require_posix()
    entries: dict[str, dict[str, object]] = {}
    total = 0
    file_count = 0
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    root_fd = os.open(root, directory_flags)

    def visit(parent_fd: int, name: str, relative: str, depth: int) -> None:
        nonlocal total, file_count
        if relative in entries:
            return
        relative_path(relative)
        if depth > 32 or len(entries) >= MAX_ENTRIES:
            raise EvidenceError('input entry/depth limit exceeded')
        info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if stat.S_ISDIR(info.st_mode):
            fd = os.open(name, directory_flags, dir_fd=parent_fd)
            try:
                entries[relative] = {'type': 'directory', 'mode': stat.S_IMODE(os.fstat(fd).st_mode)}
                with os.scandir(fd) as iterator:
                    names = []
                    for entry in iterator:
                        if len(names) + len(entries) >= MAX_ENTRIES:
                            raise EvidenceError('input entry limit exceeded')
                        names.append(entry.name)
                names.sort()
                for child in names:
                    child_relative = child if relative == '.' else relative + '/' + child
                    visit(fd, child, child_relative, depth + 1)
            finally:
                os.close(fd)
        elif stat.S_ISREG(info.st_mode):
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
            try:
                before = os.fstat(fd)
                if not stat.S_ISREG(before.st_mode):
                    raise EvidenceError('input is not a regular file')
                checksum = hashlib.sha256(); size = 0
                while True:
                    chunk = os.read(fd, 65536)
                    if not chunk:
                        break
                    size += len(chunk); total += len(chunk)
                    if total > MAX_INPUT_BYTES:
                        raise EvidenceError('input byte limit exceeded')
                    checksum.update(chunk)
                after = os.fstat(fd)
                identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns)
                if identity(before) != identity(after) or size != after.st_size:
                    raise EvidenceError('input changed while being fingerprinted')
                entries[relative] = {'type': 'file', 'mode': stat.S_IMODE(after.st_mode), 'bytes': size, 'sha256': checksum.hexdigest()}
                file_count += 1
            finally:
                os.close(fd)
        else:
            raise EvidenceError('symlinks and special input files are unsupported')

    try:
        for relative in scope:
            parts = PurePosixPath(relative).parts
            parent_fd = os.dup(root_fd)
            try:
                for part in parts[:-1]:
                    child_fd = os.open(part, directory_flags, dir_fd=parent_fd)
                    os.close(parent_fd); parent_fd = child_fd
                visit(parent_fd, parts[-1] if parts else '.', relative, len(parts))
            finally:
                os.close(parent_fd)
    finally:
        os.close(root_fd)
    if not file_count:
        raise EvidenceError('input scope contains no regular files')
    return dict(sorted(entries.items()))


def load_runner():
    path = Path(__file__).with_name('run_bounded.py')
    spec = importlib.util.spec_from_file_location('flow_evidence_runner', path)
    if spec is None or spec.loader is None:
        raise EvidenceError('bundled bounded runner is unavailable')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError('duplicate JSON object key')
        result[key] = value
    return result


def read_receipt(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise EvidenceError('receipt must be a regular file, not a symlink')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise EvidenceError('receipt must be a regular file')
        with os.fdopen(fd, 'rb', closefd=False) as handle:
            raw = handle.read(MAX_RECEIPT_BYTES + 1)
    finally:
        os.close(fd)
    if len(raw) > MAX_RECEIPT_BYTES:
        raise EvidenceError('receipt byte limit exceeded')
    try:
        value = json.loads(raw, object_pairs_hook=unique_keys)
    except (ValueError, RecursionError) as exc:
        raise EvidenceError('invalid receipt JSON') from exc
    if not isinstance(value, dict) or type(value.get('schema_version')) is not int or value.get('schema_version') != 1 or value.get('kind') != 'flow-command-evidence':
        raise EvidenceError('unsupported receipt shape')
    return value


def validate_snapshot(value: object) -> None:
    if not isinstance(value, dict) or not 1 <= len(value) <= MAX_ENTRIES:
        raise EvidenceError('invalid snapshot')
    for name, record in value.items():
        relative_path(name)
        if not isinstance(record, dict) or record.get('type') not in ('file', 'directory'):
            raise EvidenceError('invalid snapshot entry')
        if type(record.get('mode')) is not int or not 0 <= record['mode'] <= 0o7777:
            raise EvidenceError('invalid mode')
        if record['type'] == 'file':
            if type(record.get('bytes')) is not int or not 0 <= record['bytes'] <= MAX_INPUT_BYTES:
                raise EvidenceError('invalid file size')
            if not isinstance(record.get('sha256'), str) or len(record['sha256']) != 64 or any(c not in '0123456789abcdef' for c in record['sha256']):
                raise EvidenceError('invalid fingerprint')


def assess(value: dict, root: Path) -> dict:
    scope = scope_paths(value.get('input_scope'))
    validate_snapshot(value.get('before'))
    if 'after' not in value:
        raise EvidenceError('missing after snapshot')
    if value.get('after') is not None:
        validate_snapshot(value['after'])
    run = value.get('execution')
    if not isinstance(run, dict) or run.get('status') not in ('completed', 'failed', 'timed_out', 'output_limit'):
        raise EvidenceError('invalid execution record')
    if run.get('exit_code') is not None and type(run['exit_code']) is not int:
        raise EvidenceError('invalid exit code')
    for stream in ('stdout', 'stderr'):
        if type(run.get(stream + '_bytes_captured')) is not int or type(run.get(stream + '_truncated')) is not bool:
            raise EvidenceError('invalid captured-output metadata')
        try:
            output = value['output'][stream]
            encoded = output['base64']
            if not isinstance(encoded, str) or len(encoded) > 4 * MAX_OUTPUT_BYTES:
                raise EvidenceError('invalid output size')
            raw = base64.b64decode(encoded, validate=True)
            if len(raw) > MAX_OUTPUT_BYTES or digest(raw) != output['sha256'] or len(raw) != run[stream + '_bytes_captured']:
                raise EvidenceError('output integrity mismatch')
        except (KeyError, TypeError, ValueError) as exc:
            raise EvidenceError('invalid or inconsistent captured output') from exc
    label = value.get('label')
    if not isinstance(label, str) or not 1 <= len(label) <= 120 or any(ord(c) < 32 for c in label):
        raise EvidenceError('invalid check label')
    if run['status'] == 'completed' and (run.get('exit_code') != 0 or run.get('timed_out') is not False or run.get('output_limit_reached') is not False or run.get('signal') is not None or run.get('stdout_truncated') is not False or run.get('stderr_truncated') is not False):
        raise EvidenceError('completed command metadata is inconsistent')
    try:
        current = snapshot(root, scope)
        inputs = 'CURRENT' if current == value['after'] else 'STALE'
    except (OSError, EvidenceError):
        inputs = 'UNAVAILABLE'
    if value['after'] is None:
        inputs = 'UNAVAILABLE'
    elif value['before'] != value['after']:
        inputs = 'CHANGED_DURING_RUN'
    return {
        'label': label,
        'inputs': inputs,
        'input_scope': scope,
        'execution': run['status'],
        'exit_code': run.get('exit_code'),
        'output_integrity': 'CONSISTENT_NOT_AUTHENTICATED',
        'test_counts': 'UNKNOWN',
        'coverage': 'UNKNOWN',
        'task_acceptance': 'NOT_EVALUATED',
        'human_approval': 'NOT_RECORDED',
        'authenticity': 'NOT_VERIFIED',
    }


def render_card(report: dict) -> str:
    def safe(value):
        return html.escape(str(value)).replace('|', '&#124;').replace('`', '&#96;')
    rows = [('Check', report['label']), ('Input freshness', report['inputs']),
            ('Command', report['execution']), ('Exit code', report['exit_code']),
            ('Test counts / coverage', 'UNKNOWN'), ('Task acceptance', 'NOT_EVALUATED'),
            ('Human approval', 'NOT_RECORDED'), ('Authenticity', 'NOT_VERIFIED')]
    return '# Execution evidence\n\n| Field | Observed scope |\n|---|---|\n' + ''.join(
        f'| {label} | {safe(value)} |\n' for label, value in rows
    ) + '\nCheck the logs, actual criteria and selected input scope before accepting the task.\n'


def write_receipt(parent_fd: int, name: str, encoded: bytes) -> None:
    """Atomically create evidence in the pinned directory without replacement."""
    temporary = '.flow-evidence-' + secrets.token_hex(16)
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=parent_fd)
    try:
        with os.fdopen(fd, 'wb') as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd,
                follow_symlinks=False)
        try:
            os.fsync(parent_fd)
        except OSError as exc:
            if exc.errno not in {errno.EINVAL, errno.ENOTSUP, errno.EPERM}:
                raise
    finally:
        os.unlink(temporary, dir_fd=parent_fd)


def capture(args) -> int:
    require_posix()
    runner = load_runner()
    root = args.root.expanduser().resolve(strict=True)
    scope = scope_paths(args.input)
    receipt = args.receipt.expanduser().absolute()
    receipt = receipt.parent.resolve(strict=True) / receipt.name
    if receipt.exists() or receipt.is_symlink():
        raise EvidenceError('receipt already exists; not overwritten')
    if not args.label or len(args.label) > 120 or any(ord(c) < 32 for c in args.label):
        raise EvidenceError('label must be 1..120 printable characters')
    if args.max_output_bytes > MAX_OUTPUT_BYTES:
        raise EvidenceError('maximum captured output is 262144 bytes')
    for relative in scope:
        selected = root / relative
        if receipt == selected or receipt.is_relative_to(selected):
            raise EvidenceError('receipt must be outside every selected input path')
    parent_fd = os.open(receipt.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parent_info = os.fstat(parent_fd)
        before = snapshot(root, scope)
        command = args.command[1:] if args.command and args.command[0] == '--' else args.command
        if not command:
            raise EvidenceError('an explicit argv command is required after --')
        run_args = argparse.Namespace(command=command, cwd=root, wall_seconds=args.wall_seconds,
                                      max_output_bytes=args.max_output_bytes, record_argv=args.record_argv)
        execution, code, captured = runner.run_bounded(run_args)
        # The runner calls a run completed when the command exits 0, even if it had to cut
        # its output short, for example when a detached child keeps the pipe open. Such a
        # run did not deliver all of its output, so it is recorded as an output-limit run.
        if execution.get('status') == 'completed' and (execution.get('stdout_truncated') or execution.get('stderr_truncated')):
            execution = {**execution, 'status': 'output_limit'}
        after = None; snapshot_error = None
        try:
            after = snapshot(root, scope)
        except (OSError, EvidenceError) as exc:
            snapshot_error = type(exc).__name__
        value = {'schema_version': 1, 'kind': 'flow-command-evidence', 'label': args.label,
                 'input_scope': scope, 'before': before, 'after': after, 'snapshot_error': snapshot_error,
                 'execution': execution,
                 'output': {key: {'base64': base64.b64encode(raw).decode('ascii'), 'sha256': digest(raw)} for key, raw in captured.items()}}
        encoded = (json.dumps(value, sort_keys=True, indent=2) + '\n').encode('utf-8')
        if len(encoded) > MAX_RECEIPT_BYTES:
            raise EvidenceError('receipt byte limit exceeded; command ran but receipt could not be recorded')
        try:
            current_parent = os.stat(receipt.parent, follow_symlinks=False)
        except OSError as exc:
            raise EvidenceError('receipt directory unavailable; command ran but evidence was not written') from exc
        if not stat.S_ISDIR(current_parent.st_mode) or (current_parent.st_dev, current_parent.st_ino) != (parent_info.st_dev, parent_info.st_ino):
            raise EvidenceError('receipt directory changed; command ran but evidence was not written')
        # Checked before writing, so a receipt that a later check would reject is never left.
        report = assess(value, root)
        write_receipt(parent_fd, receipt.name, encoded)
        print(json.dumps(report, sort_keys=True))
        # A zero exit is success only for evidence that check would also accept.
        return code if code else (0 if report['inputs'] == 'CURRENT' and report['execution'] == 'completed' else 1)
    finally:
        os.close(parent_fd)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='mode', required=True)
    run = sub.add_parser('capture', help='run an already-authorized command and record local evidence')
    run.add_argument('--root', required=True, type=Path)
    run.add_argument('--input', action='append', required=True)
    run.add_argument('--receipt', required=True, type=Path)
    run.add_argument('--label', required=True)
    run.add_argument('--wall-seconds', required=True, type=lambda value: load_runner().positive_float(value))
    run.add_argument('--max-output-bytes', required=True, type=lambda value: load_runner().positive_int(value))
    run.add_argument('--record-argv', action='store_true')
    run.add_argument('command', nargs=argparse.REMAINDER)
    check = sub.add_parser('check', help='inspect an existing receipt; never execute its command')
    check.add_argument('--root', required=True, type=Path)
    check.add_argument('--receipt', required=True, type=Path)
    check.add_argument('--format', choices=['json', 'markdown'], default='json')
    args = parser.parse_args(argv)
    try:
        if args.mode == 'capture':
            return capture(args)
        require_posix()
        root = args.root.expanduser().resolve(strict=True)
        report = assess(read_receipt(args.receipt), root)
        print(render_card(report) if args.format == 'markdown' else json.dumps(report, sort_keys=True))
        return 0 if report['inputs'] == 'CURRENT' and report['execution'] == 'completed' else 1
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'evidence_receipt: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
