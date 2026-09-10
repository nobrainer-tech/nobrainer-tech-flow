import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

PATH = Path(__file__).resolve().parents[1] / 'skills/nobrainer-sessions/scripts/session_title.py'
spec = importlib.util.spec_from_file_location('session_title', PATH)
titles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(titles)


class SessionTitleTests(unittest.TestCase):
    def test_actual_start_and_timezone_across_midnight(self):
        result = titles.format_title('Task', '2026-09-05T23:30:00Z', 'Europe/Warsaw')
        self.assertEqual(result['display_title'], 'Task | started 06-09')
        self.assertEqual(titles.format_title('Task', '2026-09-05T23:30:00Z')['display_title'],
                         'Task | started 05-09')

    def test_resume_preserves_date_and_retries_replace_suffix(self):
        original = titles.format_title('Task', '2026-09-01T10:00:00Z')
        resumed = titles.format_title(original['display_title'], original['started_at'])
        self.assertEqual(original, resumed)
        successor = titles.format_title(resumed['display_title'], '2026-09-06T10:00:00Z')
        self.assertEqual(successor['display_title'], 'Task | started 06-09')
        self.assertEqual(titles.format_title('Task | started 01-09 | started 02-09',
            '2026-09-06T10:00:00Z'), successor)

    def test_unknown_start_or_timezone_never_becomes_today(self):
        for payload in ({'title': 'Task'}, {'title': 'Task', 'started_at': '2026-09-06'},
                        {'title': 'Task', 'started_at': '2026-09-06T10:00:00Z', 'timezone': 'No/SuchZone'}, []):
            run = subprocess.run([sys.executable, str(PATH)], input=json.dumps(payload),
                                 text=True, capture_output=True)
            self.assertEqual(run.returncode, 2)
            self.assertEqual(json.loads(run.stdout), {'status': 'TITLE_UNAVAILABLE'})

    def test_cli_formats_without_mutating_host(self):
        run = subprocess.run([sys.executable, str(PATH)], input=json.dumps({
            'title': 'Task', 'started_at': '2026-09-06T10:00:00Z'}), text=True, capture_output=True)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(json.loads(run.stdout)['display_title'], 'Task | started 06-09')
