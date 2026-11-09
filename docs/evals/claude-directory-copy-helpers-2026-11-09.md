# Claude directory copy without the Jev runner — 2026-11-09

The question: with `skills/nobrainer-tech-flow/references/optional-decisions.md`,
does `nobrainer-tech-flow` keep the core path in the Claude directory copy, which
leaves out `scripts/typed_decisions.py`? And does it stop a piped key that is too
long before any provider call?

## Method

One fresh Sonnet worker read only `skills/nobrainer-tech-flow/references/optional-decisions.md`
from this change and answered six frozen cases. It did not run commands and
quoted the sentences it relied on. MAIN wrote the expected decisions before the
run and scored the answers against them.

| # | Case | Expected | Result |
|---|---|---|---|
| 1 | Claude directory copy, helper absent, Jev shadow configured, data approved, ranking task | Run nothing; `CORE_FALLBACK`; continue in core; point to a git or npm install | PASS |
| 2 | First setup in the Claude directory copy, helper absent | Offer core only; record core/off | PASS |
| 3 | Git install, Jev shadow, a 5000-character piped key | `INVALID_INPUT`; no provider call | PASS |
| 4 | Git install, Jev shadow, valid key, calls left | May run the helper; `SHADOW_SUGGESTION` is advisory only | PASS |
| 5 | Git install, mode off with provider jev | No calls; `CORE_FALLBACK` | PASS |
| 6 | One-word README typo | No classifier | PASS |

PRESSURE_RESULT: PASS 3/3 (cases 1–3: the changed sentences)
HOLDOUT_RESULT: PASS 3/3 (cases 4–6: unchanged behaviour and a non-trigger case)

## Limits

- In case 2 the worker noted that the file says to point to a git or npm install
  only when a Jev or Laya preference is already recorded, not during setup itself.
  The expected answer did not require that pointer.
- The runtime half is covered by tests, not by this record:
  `test_works_in_a_copy_without_the_runner` (configuration without the runner),
  `test_piped_key_is_one_bounded_line` and `test_cli_key_stdin_reaches_only_the_jev_worker`.
- CLIENT_RUNTIME: NOT_VERIFIED. This is a source-reading check, not proof that a
  client installed from the Claude directory behaves this way.
