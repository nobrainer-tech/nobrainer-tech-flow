from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ROOT / 'skills/nobrainer-sessions/scripts/evidence_receipt.py'




class ReceiptTests(unittest.TestCase):
    def invoke(self, *args: str):
        result = subprocess.run([sys.executable, str(RECEIPT), *args], capture_output=True, text=True, timeout=15)
        self.assertNotIn("can't open file", result.stderr)
        return result

    def capture(self, root: Path, receipt: Path, code: str = "print('one local check')", *extra: str):
        return self.invoke('capture', '--root', str(root), '--input', 'src', '--receipt', str(receipt),
                           '--label', 'local check', '--wall-seconds', '2', '--max-output-bytes', '4096',
                           *extra, '--', sys.executable, '-c', code)

    @unittest.skipUnless(os.name == 'posix', 'capture requires POSIX process groups')
    def test_real_capture_current_and_stale_after_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'src').mkdir(); (root/'src/a.txt').write_text('before')
            receipt = root/'proof.json'
            result = self.capture(root, receipt)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(receipt.read_text()); self.assertNotIn('argv', data['execution'])
            checked = self.invoke('check', '--root', str(root), '--receipt', str(receipt))
            self.assertEqual(checked.returncode, 0, checked.stderr)
            report = json.loads(checked.stdout)
            self.assertEqual(report['inputs'], 'CURRENT')
            self.assertEqual(report['task_acceptance'], 'NOT_EVALUATED')
            self.assertEqual(report['test_counts'], 'UNKNOWN')
            self.assertEqual(report['human_approval'], 'NOT_RECORDED')
            (root/'src/a.txt').write_text('after')
            stale = self.invoke('check', '--root', str(root), '--receipt', str(receipt))
            self.assertEqual(stale.returncode, 1, stale.stderr)
            self.assertEqual(json.loads(stale.stdout)['inputs'], 'STALE')

    @unittest.skipUnless(os.name == 'posix', 'capture requires POSIX')
    def test_added_file_and_changed_during_run_invalidate_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'src').mkdir(); (root/'src/a.txt').write_text('before')
            receipt = root/'proof.json'
            run = self.capture(root, receipt, "from pathlib import Path; Path('src/b.txt').write_text('new')")
            self.assertEqual(run.returncode, 1, run.stderr)
            checked = self.invoke('check', '--root', str(root), '--receipt', str(receipt))
            self.assertEqual(json.loads(checked.stdout)['inputs'], 'CHANGED_DURING_RUN')

    @unittest.skipUnless(os.name == 'posix', 'capture requires POSIX')
    def test_failure_and_timeout_remain_distinct_from_current_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'src').mkdir(); (root/'src/a').write_text('stable')
            failed = root/'failed.json'
            self.assertEqual(self.capture(root, failed, 'raise SystemExit(7)').returncode, 7)
            result = self.invoke('check', '--root', str(root), '--receipt', str(failed))
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)['execution'], 'failed')
            timed = root/'timed.json'
            result = self.capture(root, timed, 'import time; time.sleep(5)', '--wall-seconds', '0.1')
            self.assertEqual(result.returncode, 124, result.stderr)
            checked = self.invoke('check', '--root', str(root), '--receipt', str(timed))
            self.assertEqual(json.loads(checked.stdout)['execution'], 'timed_out')

    @unittest.skipUnless(os.name == 'posix', 'capture requires POSIX')
    def test_corrupt_output_and_forged_scope_are_rejected_without_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'src').mkdir(); (root/'src/a').write_text('stable')
            receipt = root/'proof.json'; self.assertEqual(self.capture(root, receipt).returncode, 0)
            original = receipt.read_text(); data = json.loads(original)
            data['output']['stdout']['sha256'] = '0'*64; receipt.write_text(json.dumps(data))
            self.assertEqual(self.invoke('check', '--root', str(root), '--receipt', str(receipt)).returncode, 2)
            data = json.loads(original); data['input_scope'] = ['../outside']; receipt.write_text(json.dumps(data))
            self.assertEqual(self.invoke('check', '--root', str(root), '--receipt', str(receipt)).returncode, 2)

    @unittest.skipUnless(os.name == 'posix', 'capture requires POSIX')
    def test_existing_receipt_and_symlink_scope_stop_before_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'src').mkdir(); (root/'src/a').write_text('stable')
            receipt = root/'proof.json'; receipt.write_text('owner work')
            code = "from pathlib import Path; Path('executed').write_text('bad')"
            self.assertEqual(self.capture(root, receipt, code).returncode, 2)
            self.assertEqual(receipt.read_text(), 'owner work'); self.assertFalse((root/'executed').exists())
            receipt.unlink(); (root/'src/link').symlink_to(root/'src/a')
            self.assertEqual(self.capture(root, receipt, code).returncode, 2)
            self.assertFalse((root/'executed').exists()); self.assertFalse(receipt.exists())

    @unittest.skipUnless(os.name == 'posix', 'capture requires POSIX')
    def test_receipt_inside_scope_and_directory_escape_are_refused(self):
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory); (root/'src').mkdir(); (root/'src/a').write_text('stable')
            self.assertEqual(self.capture(root, root/'src/proof.json').returncode, 2)
            (root/'src/a').unlink(); (root/'src/out').symlink_to(outside, target_is_directory=True)
            self.assertEqual(self.capture(root, root/'proof.json').returncode, 2)

    @unittest.skipUnless(os.name == 'posix', 'capture requires POSIX')
    def test_command_cannot_redirect_receipt_into_selected_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); project = root/'project'
            (project/'src').mkdir(parents=True); (project/'src/a').write_text('stable')
            (root/'out').mkdir()
            code = "from pathlib import Path; p=Path('../out'); p.rmdir(); p.symlink_to('project/src', target_is_directory=True)"
            result = self.capture(project, root/'out/proof.json', code)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn('command ran but evidence was not written', result.stderr)
            self.assertEqual(sorted(p.name for p in (project/'src').iterdir()), ['a'])

    @unittest.skipUnless(os.name == 'posix', 'capture requires POSIX')
    def test_output_limit_and_malformed_completion_are_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'src').mkdir(); (root/'src/a').write_text('stable')
            receipt = root/'proof.json'
            result = self.capture(root, receipt, "print('x'*10000)", '--max-output-bytes', '64')
            self.assertEqual(result.returncode, 125, result.stderr)
            checked = self.invoke('check', '--root', str(root), '--receipt', str(receipt))
            self.assertEqual(checked.returncode, 1)
            self.assertEqual(json.loads(checked.stdout)['execution'], 'output_limit')
            receipt.unlink(); self.assertEqual(self.capture(root, receipt).returncode, 0)
            original = json.loads(receipt.read_text())
            for field, value in [('exit_code', False), ('signal', 9), ('stdout_truncated', True)]:
                data = json.loads(json.dumps(original)); data['execution'][field] = value
                receipt.write_text(json.dumps(data))
                self.assertEqual(self.invoke('check', '--root', str(root), '--receipt', str(receipt)).returncode, 2)

    @unittest.skipUnless(os.name == 'posix', 'capture requires POSIX')
    def test_detached_child_holding_output_leaves_a_checkable_incomplete_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'src').mkdir(); (root/'src/a.txt').write_text('before')
            receipt = root/'proof.json'
            code = ("import subprocess, sys; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(4)'], "
                    "start_new_session=True); print('ok')")
            self.capture(root, receipt, code)
            self.assertTrue(receipt.exists())
            checked = self.invoke('check', '--root', str(root), '--receipt', str(receipt))
            self.assertNotEqual(2, checked.returncode, checked.stderr)
            self.assertNotEqual('completed', json.loads(checked.stdout)['execution'])

    @unittest.skipUnless(os.name == 'posix', 'capture requires POSIX')
    def test_special_file_scope_is_refused_before_running(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'src').mkdir(); os.mkfifo(root/'src/pipe')
            code = "from pathlib import Path; Path('executed').write_text('bad')"
            self.assertEqual(self.capture(root, root/'proof.json', code).returncode, 2)
            self.assertFalse((root/'executed').exists())

    @unittest.skipUnless(os.name == 'posix', 'capture requires POSIX')
    def test_markdown_card_keeps_unknowns_and_escapes_label(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'src').mkdir(); (root/'src/a').write_text('stable')
            receipt = root/'proof.json'
            self.assertEqual(self.capture(root, receipt, "print('ok')", '--label', '<script>bad</script>').returncode, 0)
            card = self.invoke('check', '--root', str(root), '--receipt', str(receipt), '--format', 'markdown')
            self.assertEqual(card.returncode, 0)
            self.assertIn('NOT_EVALUATED', card.stdout); self.assertIn('NOT_RECORDED', card.stdout)
            self.assertNotIn('<script>', card.stdout)


if __name__ == '__main__':
    unittest.main()
