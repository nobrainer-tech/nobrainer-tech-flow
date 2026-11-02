# Session transport

Sessions owns delivery of a task to a session in another client (Claude, Codex,
Muse, OpenCode or any other harness). Dispatcher decides what is ready; Team
picks the capability; this contract only moves the message and proves it moved.
Nothing here needs a specific tool: any local adapter that satisfies it is
valid, and its absence means remain in MAIN.

## Operations

| Operation | Result |
|---|---|
| `capabilities` | Backends present, versions, auth state as metadata only. |
| `list` | Sessions with exact id, title, cwd/branch and active-turn state. |
| `send` | `PREVIEW` by default; `QUEUED` or `SENT` only with a receipt. |
| `start` | New session id for a workspace and prompt, with the same receipt rule. |
| `status` / `result` | Turn state; final report text read back from the target. |

## Rules

- Resolve the target by exact id. A title or name is a hint, never identity;
  ambiguous or stale identity stops the send.
- Default to `PREVIEW`. Deliver only on an explicit execute flag from MAIN.
- Pass the body on stdin or as a structured argument, never through a shell.
  Reject bodies over 64 KiB and bodies containing credentials.
- `QUEUED` means the target accepted the message for a later turn; `SENT` means
  the target's own readback shows it. A zero exit code proves neither.
- Completion needs `result` readback from the target, not the sender's log.
- Respect the one-writer rule: do not send write work to a session whose
  repository or worktree lease is held by another writer.
- Never log, store or forward secrets; never use or borrow the owner's login.
  `capabilities` reports only whether auth exists.
- Transport failure after a retryable error is retried once with the same
  idempotency key; a second failure returns the task to MAIN.

## Choosing a backend

Flow model routing chooses backend and model; the adapter only delivers. An
unavailable backend is reported, not silently replaced.

## Short-lived CLI workers

For bounded implementation or review that needs no visible session, MAIN may
run a worker CLI once and read only its final report and the resulting diff.
This spends the cheaper worker's tokens instead of MAIN's. Use it only when the
owner allows that backend; Flow never enables a backend on its own.

- **When:** a scoped unit with a clear contract and checks. Keep planning,
  integration and acceptance in MAIN. Do not use it for work that needs the
  owner's session, a shared live context or an unclear scope.
- **Backend and model:** Flow routing picks them; the adapter only runs the
  command. Verify the binary and model ID are present before dispatch.
- **Invocation:** argv without a shell, prompt from a file or stdin, final
  message written to a file. Examples (check each CLI's current flags first):
  `codex exec -m <model> -C <repo> -s <sandbox> --output-last-message <file> -`
  and `muse exec --json --workspace <repo> --prompt-file <file>`.
- **Muse report:** with `--json` stdout is JSONL; the final report is
  `payload.text` of the `run.terminal.completed` record. `--provider echo`
  runs without an account and is the hermetic smoke test. Visible Muse
  sessions map to `list`/`send` through
  `muse session-message list --json` and `send --target <uuid> < body`.
- **Sandbox:** `workspace-write` only for an implementer with an exclusive
  write scope; `read-only` for review and diagnosis. Muse has no `-s` flag:
  use a read-only `--permission-profile` when one is configured, otherwise
  isolate the run with `--worktree create`.
- **Timeout:** wrap the call in
  [`run_bounded.py`](../scripts/run_bounded.py) for a wall-time and output cap;
  a hung proxy otherwise blocks MAIN. A timeout returns the unit to MAIN.
- **Prompt:** goal, context, exclusive write scope, acceptance checks, stop
  conditions and a short report format (changed files, checks run, blockers).
- **Verify:** the report is a claim. MAIN reads the diff, runs the checks and
  rejects out-of-scope edits before accepting. A zero exit code proves nothing.
- **Hygiene:** no secrets in the prompt or report; one writer per checkout;
  delete the prompt and report files after the unit is verified.
