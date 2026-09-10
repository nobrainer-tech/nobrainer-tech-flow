#!/usr/bin/env python3
"""Format an observed session start; never rename or invent a missing date."""
from datetime import datetime
import json
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def format_title(title: str, started_at: str, timezone: str = 'UTC') -> dict:
    if not isinstance(title, str) or not title.strip():
        raise ValueError('missing_title')
    if not isinstance(started_at, str):
        raise ValueError('missing_verified_start')
    started = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
    if started.tzinfo is None:
        raise ValueError('start_requires_offset')
    zone = ZoneInfo(timezone)
    base = re.sub(r'(?: \| started \d{2}-\d{2})+$', '', title.strip()).strip()
    if not base:
        raise ValueError('missing_title_base')
    return {'title_base': base, 'started_at': started.isoformat(),
            'timezone': timezone,
            'display_title': f'{base} | started {started.astimezone(zone):%d-%m}'}


def main() -> int:
    try:
        raw = sys.stdin.buffer.read(8193)
        if len(raw) > 8192:
            raise ValueError('input_too_large')
        state = json.loads(raw)
        output = format_title(state['title'], state['started_at'], state.get('timezone', 'UTC'))
    except (ValueError, KeyError, TypeError, AttributeError, ZoneInfoNotFoundError):
        print(json.dumps({'status': 'TITLE_UNAVAILABLE'}))
        return 2
    print(json.dumps(output))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
