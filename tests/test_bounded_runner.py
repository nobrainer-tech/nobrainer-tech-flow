from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "skills" / "nobrainer-sessions" / "scripts" / "run_bounded.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("nobrainer_run_bounded", RUNNER)
assert RUNNER_SPEC is not None and RUNNER_SPEC.loader is not None
RUNNER_MODULE = importlib.util.module_from_spec(RUNNER_SPEC)
RUNNER_SPEC.loader.exec_module(RUNNER_MODULE)


@unittest.skipUnless(os.name == "posix", "process-group behavior is POSIX-only")
class BoundedRunnerTests(unittest.TestCase):
    def invoke(
        self,
        directory: Path,
        command: list[str],
        *,
        wall: str = "2",
        output: str = "4096",
        receipt_name: str = "receipt.json",
        extra: tuple[str, ...] = (),
    ) -> tuple[subprocess.CompletedProcess[bytes], Path]:
        receipt = directory / receipt_name
        result = subprocess.run(
            [
                sys.executable,
                str(RUNNER),
                "--wall-seconds",
                wall,
                "--max-output-bytes",
                output,
                "--cwd",
                str(directory),
                "--receipt",
                str(receipt),
                *extra,
                "--",
                *command,
            ],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
        )
        return result, receipt

    def read_receipt(self, path: Path) -> dict[str, object]:
        return json.loads(path.read_text(encoding="utf-8"))

    def wait_for_published_pid(self, path: Path, timeout: float = 5.0) -> int:
        # The child creates the file before writing it, so existence alone can
        # observe an empty file. Wait until the content parses as an integer.
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                return int(path.read_text(encoding="utf-8"))
            except (FileNotFoundError, ValueError):
                time.sleep(0.02)
        self.fail("child pid was not published")

    def assert_process_gone(self, process_id: int) -> None:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            try:
                os.kill(process_id, 0)
            except ProcessLookupError:
                return
            time.sleep(0.02)
        self.fail(f"descendant process {process_id} is still alive")

    def test_success_emits_output_and_omits_argv_from_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result, receipt_path = self.invoke(
                Path(temporary), [sys.executable, "-c", "print('ready')"]
            )
            receipt = self.read_receipt(receipt_path)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(b"ready\n", result.stdout)
            self.assertEqual("completed", receipt["status"])
            self.assertEqual(0, receipt["exit_code"])
            self.assertFalse(receipt["argv_recorded"])
            self.assertNotIn("argv", receipt)
            self.assertEqual("UNKNOWN", receipt["model_tokens"])

    def test_fast_success_is_not_timed_out_by_post_exit_cleanup_grace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result, receipt_path = self.invoke(
                Path(temporary),
                [sys.executable, "-c", "print('fast')"],
                wall="0.2",
            )
            receipt = self.read_receipt(receipt_path)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("completed", receipt["status"])
            self.assertFalse(receipt["timed_out"])

    def test_nonzero_exit_is_failed_and_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result, receipt_path = self.invoke(
                Path(temporary), [sys.executable, "-c", "raise SystemExit(7)"]
            )
            receipt = self.read_receipt(receipt_path)
            self.assertEqual(7, result.returncode)
            self.assertEqual("failed", receipt["status"])
            self.assertEqual(7, receipt["exit_code"])

    def test_combined_output_cap_stops_process_and_bounds_both_streams(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code = (
                "import os,time; "
                "os.write(1,b'o'*4000); os.write(2,b'e'*4000); time.sleep(5)"
            )
            result, receipt_path = self.invoke(
                Path(temporary), [sys.executable, "-c", code], output="100"
            )
            receipt = self.read_receipt(receipt_path)
            self.assertEqual(125, result.returncode)
            self.assertLessEqual(len(result.stdout) + len(result.stderr), 100)
            self.assertEqual(100, len(result.stdout) + len(result.stderr))
            self.assertEqual("output_limit", receipt["status"])
            self.assertTrue(receipt["output_limit_reached"])
            self.assertTrue(
                receipt["stdout_truncated"] or receipt["stderr_truncated"]
            )

    def test_timeout_terminates_process_group_descendant(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code = (
                "import subprocess,sys,time; "
                "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
                "print(p.pid,flush=True); time.sleep(30)"
            )
            result, receipt_path = self.invoke(
                Path(temporary),
                [sys.executable, "-c", code],
                wall="0.2",
            )
            receipt = self.read_receipt(receipt_path)
            child_pid = int(result.stdout.strip())
            self.assertEqual(124, result.returncode)
            self.assertEqual("timed_out", receipt["status"])
            self.assertTrue(receipt["timed_out"])
            self.assertTrue(receipt["termination"]["sent_term"])
            self.assert_process_gone(child_pid)

    def test_closed_output_fds_do_not_end_a_still_running_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code = "import os,time; os.close(1); os.close(2); time.sleep(0.3)"
            started = time.monotonic()
            result, receipt_path = self.invoke(
                Path(temporary), [sys.executable, "-c", code]
            )
            duration = time.monotonic() - started
            receipt = self.read_receipt(receipt_path)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertGreaterEqual(duration, 0.25)
            self.assertEqual("completed", receipt["status"])

    def test_term_ignoring_descendant_with_closed_pipes_is_killed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            ready = directory / "child.ready"
            child_code = (
                "import os,pathlib,signal,time; "
                "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
                "os.close(1); os.close(2); "
                f"pathlib.Path({str(ready)!r}).write_text('ready'); time.sleep(30)"
            )
            code = "\n".join(
                (
                    "import pathlib,subprocess,sys,time",
                    f"p=subprocess.Popen([sys.executable,'-c',{child_code!r}])",
                    f"ready=pathlib.Path({str(ready)!r})",
                    "deadline=time.monotonic()+2",
                    "while not ready.exists() and time.monotonic()<deadline:",
                    "    time.sleep(.01)",
                    "print(p.pid,flush=True)",
                )
            )
            result, receipt_path = self.invoke(
                directory, [sys.executable, "-c", code]
            )
            receipt = self.read_receipt(receipt_path)
            child_pid = int(result.stdout.strip())
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("completed", receipt["status"])
            self.assertTrue(receipt["termination"]["sent_kill"])
            self.assert_process_gone(child_pid)

    def test_leader_exit_with_inherited_pipe_gets_finite_descendant_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            code = (
                "import subprocess,sys; "
                "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); "
                "print(p.pid,flush=True)"
            )
            started = time.monotonic()
            result, receipt_path = self.invoke(
                Path(temporary), [sys.executable, "-c", code]
            )
            duration = time.monotonic() - started
            receipt = self.read_receipt(receipt_path)
            child_pid = int(result.stdout.strip())
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertLess(duration, 1.5)
            self.assertEqual("completed", receipt["status"])
            self.assertTrue(
                receipt["termination"][
                    "descendant_cleanup_attempted_after_leader_exit"
                ]
            )
            self.assert_process_gone(child_pid)

    def test_invalid_limit_is_rejected_without_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result, receipt_path = self.invoke(
                Path(temporary),
                [sys.executable, "-c", "print('must not run')"],
                wall="0",
            )
            self.assertEqual(2, result.returncode)
            self.assertIn(b"greater than zero", result.stderr)
            self.assertFalse(receipt_path.exists())

    def test_existing_receipt_is_not_overwritten_and_command_does_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            receipt = directory / "receipt.json"
            marker = directory / "ran"
            receipt.write_text("keep\n", encoding="utf-8")
            result, returned_receipt = self.invoke(
                directory,
                [sys.executable, "-c", f"open({str(marker)!r},'w').write('bad')"],
            )
            self.assertEqual(receipt, returned_receipt)
            self.assertEqual(2, result.returncode)
            self.assertEqual("keep\n", receipt.read_text(encoding="utf-8"))
            self.assertFalse(marker.exists())

    def test_dangling_receipt_symlink_is_rejected_without_running_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            receipt = directory / "receipt.json"
            missing = directory / "missing-target.json"
            marker = directory / "ran"
            receipt.symlink_to(missing)
            result, returned_receipt = self.invoke(
                directory,
                [sys.executable, "-c", f"open({str(marker)!r},'w').write('bad')"],
            )
            self.assertEqual(receipt, returned_receipt)
            self.assertEqual(2, result.returncode)
            self.assertTrue(receipt.is_symlink())
            self.assertFalse(missing.exists())
            self.assertFalse(marker.exists())

    def test_broken_stdout_is_reported_after_child_cleanup_and_receipt_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            receipt = directory / "receipt.json"
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(RUNNER),
                    "--wall-seconds",
                    "2",
                    "--max-output-bytes",
                    "4096",
                    "--cwd",
                    str(directory),
                    "--receipt",
                    str(receipt),
                    "--",
                    sys.executable,
                    "-c",
                    "print('captured')",
                ],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            assert process.stdout is not None
            process.stdout.close()
            _, stderr = process.communicate(timeout=3)
            saved = self.read_receipt(receipt)
            self.assertEqual(70, process.returncode, stderr)
            self.assertEqual("completed", saved["status"])
            self.assertTrue(
                str(saved["output_forwarding"]["stdout"]).startswith("failed_")
            )

    def test_keyboard_interrupt_during_capture_cleans_owned_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            child_pid_path = directory / "child.pid"
            receipt = directory / "receipt.json"
            child_code = "import time; time.sleep(30)"
            code = (
                "import pathlib,subprocess,sys,time; "
                f"p=subprocess.Popen([sys.executable,'-c',{child_code!r}]); "
                f"pathlib.Path({str(child_pid_path)!r}).write_text(str(p.pid)); "
                "time.sleep(30)"
            )
            runner = subprocess.Popen(
                [
                    sys.executable,
                    str(RUNNER),
                    "--wall-seconds",
                    "10",
                    "--max-output-bytes",
                    "4096",
                    "--cwd",
                    str(directory),
                    "--receipt",
                    str(receipt),
                    "--",
                    sys.executable,
                    "-c",
                    code,
                ],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            child_pid = self.wait_for_published_pid(child_pid_path)
            runner.send_signal(signal.SIGINT)
            runner.communicate(timeout=3)
            self.assertNotEqual(0, runner.returncode)
            self.assertFalse(receipt.exists())
            self.assert_process_gone(child_pid)

    def test_selector_setup_exception_cleans_process_started_by_popen(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            args = argparse.Namespace(
                command=[sys.executable, "-c", "import time; time.sleep(30)"],
                cwd=directory,
                receipt=directory / "receipt.json",
                wall_seconds=10.0,
                max_output_bytes=4096,
                record_argv=False,
            )
            started: list[subprocess.Popen[bytes]] = []
            original_popen = RUNNER_MODULE.subprocess.Popen

            def record_popen(*popen_args: object, **popen_kwargs: object) -> object:
                process = original_popen(*popen_args, **popen_kwargs)
                started.append(process)
                return process

            with (
                mock.patch.object(
                    RUNNER_MODULE.subprocess, "Popen", side_effect=record_popen
                ),
                mock.patch.object(
                    RUNNER_MODULE.selectors,
                    "DefaultSelector",
                    side_effect=RuntimeError("selector setup failed"),
                ),
            ):
                with self.assertRaisesRegex(RuntimeError, "selector setup failed"):
                    RUNNER_MODULE.run_bounded(args)

            self.assertEqual(1, len(started))
            self.assertIsNotNone(started[0].poll())


if __name__ == "__main__":
    unittest.main()
