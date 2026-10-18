#!/usr/bin/env python3
"""Propose repeated context from an explicitly supplied local JSON file.

Only supplied role=user/kind=instruction records qualify. Those labels are not
authenticated; output always requires human review and never updates instructions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

MAX_BYTES = 2 * 1024 * 1024
MAX_RECORDS = 10000
FIELDS = ('conversation_id', 'message_id', 'scope', 'role', 'kind', 'text')


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON object key')
        result[key] = value
    return result


def read_input(path: Path):
    if path.is_symlink():
        raise ValueError('input symlinks are not supported')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(path, flags)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError('input must be a regular file')
        with os.fdopen(fd, 'rb', closefd=False) as handle:
            raw = handle.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('history exceeds 2097152 bytes')
        data = json.loads(raw, object_pairs_hook=unique_keys)
        if not isinstance(data, list) or len(data) > MAX_RECORDS:
            raise ValueError('history must be an array of at most 10000 records')
        return data, hashlib.sha256(raw).hexdigest()
    finally:
        os.close(fd)


def short_text(value, limit):
    return isinstance(value, str) and bool(value.strip()) and len(value.encode('utf-8')) <= limit


def analyze(records: list, input_hash: str) -> dict:
    identities = {}
    groups = {}
    excluded = []
    duplicates = 0
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            excluded.append({'row': index, 'reason': 'NOT_AN_OBJECT'}); continue
        if not all(short_text(row.get(key), 200) for key in ('conversation_id', 'message_id')):
            excluded.append({'row': index, 'reason': 'MISSING_OR_INVALID_IDENTITY'}); continue
        identity = (row['conversation_id'], row['message_id'])
        record = {key: row.get(key) for key in FIELDS}
        if identity in identities:
            if identities[identity] != record:
                raise ValueError('conflicting duplicate conversation/message identity')
            duplicates += 1; continue
        identities[identity] = record
        if not short_text(row.get('scope'), 200):
            excluded.append({'row': index, 'reason': 'MISSING_OR_INVALID_SCOPE'}); continue
        if row.get('role') != 'user' or row.get('kind') != 'instruction':
            excluded.append({'row': index, 'reason': 'NOT_LABELLED_USER_INSTRUCTION'}); continue
        if not short_text(row.get('text'), 8192):
            excluded.append({'row': index, 'reason': 'MISSING_OR_INVALID_TEXT'}); continue
        # Only remove surrounding whitespace. Code, quoted literals and casing
        # inside the instruction remain distinct; preserve every original below.
        normalized = row['text'].strip()
        key = (row['scope'], normalized)
        group = groups.setdefault(key, {'scope': row['scope'], 'text': normalized, 'sources': []})
        group['sources'].append({'row': index, 'conversation_id': row['conversation_id'],
                                 'message_id': row['message_id'], 'text': row['text']})
    candidates = []
    single = 0
    for key in sorted(groups):
        group = groups[key]
        count = len({row['conversation_id'] for row in group['sources']})
        if count < 2:
            single += 1; continue
        group['conversation_count'] = count
        group['status'] = 'REVIEW_REQUIRED'
        candidates.append(group)
    return {
        'schema_version': 1,
        'input_sha256': input_hash,
        'input_authority': 'UNVERIFIED',
        'project_write': 'NONE',
        'conflict_analysis': 'HUMAN_REVIEW_REQUIRED',
        'normalization': 'SURROUNDING_WHITESPACE_ONLY',
        'records': len(records),
        'duplicate_records': duplicates,
        'single_conversation_groups': single,
        'excluded': excluded,
        'candidates': candidates,
        'limitations': [
            'Roles, instruction labels and scope come from input and are not authenticated.',
            'Repeated text is a candidate, not proof of a durable preference or authorization.',
            'No semantic equivalence, contradiction detection, scraping or automatic promotion.',
            'Review each original source and existing instruction owner before any separate change.',
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='explicitly selected, authorized and redacted JSON records')
    args = parser.parse_args(argv)
    try:
        records, input_hash = read_input(args.input)
        print(json.dumps(analyze(records, input_hash), ensure_ascii=False, indent=2))
        return 0
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        print('context_candidates: invalid UTF-8 JSON input', file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f'context_candidates: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
