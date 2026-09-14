#!/usr/bin/env python3
"""Read-only instruction inventory. Candidates require semantic review."""
import argparse
import hashlib
import json
import os
import re
from pathlib import Path

SKIP = {'.git', 'node_modules', 'vendor', '.venv', 'venv', 'dist', 'build', '__pycache__', 'work', 'outputs', 'review', 'backups', 'backup', 'preimages', '.next', '.cache', '.staging'}
NAMES = {'AGENTS.md', 'AGENTS.override.md', 'CLAUDE.md', 'SKILL.md'}
PATTERNS = {
    'broad-trigger': r'(?i)use.*(?:any task|every task|always|whenever|ANY task)',
    'unconditional-reading': r'(?i)(?:before every|before any|at.*start|przed każd).*(?:read|czyta)|read.*before.*(?:implementation|edit)',
    'approval-boundary': r'(?i)(?:approval|permission|authorization|zgod|potwierdz)',
    'model-policy': r'(?i)(?:MAIN|default|use|uses).*(?:gpt-|luna|astra|opus)',
    'mandatory-process': r'(?i)(?:MUST|mandatory|always|required|obowiązk)',
    'managed-pane': r'pane-agent-context:start',
}

def scan(root):
    root = Path(root).expanduser().resolve()
    result = {'root': str(root), 'status': 'inventoried', 'files': [], 'skipped': []}

    def record_skip(path, reason):
        result['skipped'].append({'path': str(path), 'reason': reason})

    def record_walk_error(exc):
        record_skip(getattr(exc, 'filename', None) or root, type(exc).__name__)

    if not root.exists():
        result['status'] = 'missing'
        return result
    if root.is_file():
        paths = [root]
    else:
        paths = []
        try:
            for directory, dirs, files in os.walk(
                root, followlinks=False, onerror=record_walk_error
            ):
                directory_path = Path(directory)
                symlink_dirs = sorted(
                    d for d in dirs
                    if d not in SKIP and (directory_path / d).is_symlink()
                )
                for name in symlink_dirs:
                    record_skip(directory_path / name, 'symlink directory; not followed')

                symlink_files = sorted(
                    f for f in files if (directory_path / f).is_symlink()
                )
                for name in symlink_files:
                    record_skip(directory_path / name, 'symlink; resolve explicitly')

                dirs[:] = sorted(
                    d for d in dirs
                    if d not in SKIP and not (directory_path / d).is_symlink()
                )
                paths.extend(
                    directory_path / f
                    for f in sorted(files)
                    if f in NAMES and not (directory_path / f).is_symlink()
                )
        except OSError as exc:
            record_walk_error(exc)
    for path in paths:
        if path.is_symlink():
            record_skip(path, 'symlink; resolve explicitly')
            continue
        try:
            if path.stat().st_size > 1_000_000:
                raise ValueError('over 1 MB read limit')
            raw = path.read_bytes()
            content = raw.decode('utf-8')
        except (OSError, UnicodeError, ValueError) as exc:
            record_skip(path, type(exc).__name__)
            continue
        lines = content.splitlines()
        candidates = [{'line': n, 'code': code} for n, line in enumerate(lines, 1)
                      for code, pattern in PATTERNS.items() if re.search(pattern, line)]
        result['files'].append({'path': str(path), 'bytes': len(raw), 'lines': len(lines),
                                'sha256': hashlib.sha256(raw).hexdigest(), 'candidates': candidates})
    if result['skipped']:
        result['status'] = 'partial'
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+')
    parser.add_argument('--summary', action='store_true')
    args = parser.parse_args()
    targets = [scan(p) for p in args.paths]
    if args.summary:
        for target in targets:
            target['file_count'] = len(target['files'])
            target['bytes'] = sum(f['bytes'] for f in target['files'])
            target['files'] = [{'path': f['path'], 'lines': f['lines']} for f in target['files']]
    print(json.dumps({'method': 'static inventory, not a semantic verdict; generated/artifact directories excluded',
                      'targets': targets}, ensure_ascii=False, indent=2))
