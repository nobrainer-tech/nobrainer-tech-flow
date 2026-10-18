# Evidence receipt

Optional local tool. Sessions owns the command capture; Review owns acceptance.
[`evidence_receipt.py`](../scripts/evidence_receipt.py) runs one command through
the bounded runner and records a declared input scope before and after it.
`check` is read-only and never re-executes a command from the receipt.

## Use

```bash
python3 skills/nobrainer-sessions/scripts/evidence_receipt.py capture \
  --root ./project --input src --input tests \
  --receipt ./check-evidence.json --label 'unit tests' \
  --wall-seconds 30 --max-output-bytes 65536 -- \
  python3 -B -m unittest discover -s tests -v

python3 skills/nobrainer-sessions/scripts/evidence_receipt.py check \
  --root ./project --receipt ./check-evidence.json --format markdown
```

The caller supplies the root on every check. Inputs are relative files or
directories without links or special files. The receipt must be new and outside
every input. Keep caches and outputs outside the scope (`-B` avoids bytecode).
An error after the command started can mean it already ran: reconcile effects
before retrying.

## Statuses

- `CURRENT`: the before, after and current snapshots agree.
- `STALE`: the selected scope differs now.
- `CHANGED_DURING_RUN`: before and after differ, so no single source version
  was established, even if the command returned zero.
- `UNAVAILABLE`: the scope or the after snapshot could not be read safely.

## Exit codes

Capture keeps the command's nonzero result; success with non-current inputs
returns 1. Check returns 0 only for current inputs and a completed command, 1 for
stale, unavailable or failed evidence, and 2 for invalid input or an unsupported
operation.

## Limits

- Python 3.11+ and POSIX only. Windows capture and check are unsupported.
- Unsigned: anyone who can rewrite the receipt and the files can forge a
  consistent record. Hashes do not prove a trustworthy observer or a sufficient test.
- Output is stored as base64 with hashes, which is not redaction. Do not capture
  commands that can emit secrets; inspect a copy before sharing.
- Caps: 64 selectors, 1,000 entries, 64 MiB input, 256 KiB output, 4 MiB receipt.
- A change and revert between snapshots can go undetected; the bounded runner is not a sandbox.

A receipt is evidence, not acceptance. Test counts stay `UNKNOWN`, task acceptance
`NOT_EVALUATED`, human approval `NOT_RECORDED`, authenticity `NOT_VERIFIED`.
STALE or CHANGED_DURING_RUN evidence does not prove the current artifact.
