# Scoring rules and scores: implicit state machines in review

Readers never saw this file. The rules for Pressure 1 and the holdout were written before
any run. Pressure 2 was added after the baseline run of Pressure 1 and before any other
run. Scores were added as the runs came back.

A planted item counts as FOUND only when the review names the triggering sequence and the
wrong resulting state or behaviour. "State may be inconsistent" does not count.

## Pressure 1: `pressure/orders.py` and `pressure/jobs.py` (9 planted)

- O1 `pay`: `gateway.charge` raises (timeout), `locked_at` stays set, so
  `can_retry_payment` is false for ever; the order is stuck in "new".
- O2 `cancel` on a paid order leaves `paid` true and refunds nothing, so `ship` accepts a
  cancelled order: `cancelled_at` set and status "shipped".
- O3 `refund` leaves `paid` true, so `ship` accepts a refunded order.
- O4 three failed charges: `attempts` reaches the maximum, status stays "new", nothing
  moves the order to a failed or cancelled state; `is_open` and `total_due` keep counting it.
- O5 `pay` does not check `locked_at`: two concurrent calls both pass `if order.paid` and
  charge twice.
- J1 `requeue_stale` uses `started_at`, not `heartbeat_at`: a long job with fresh
  heartbeats is requeued while its worker still runs, a second worker claims it, and
  `complete` from the first worker is still accepted.
- J2 `fail` with attempts left sets state "queued" but keeps `finished_at` and `error`:
  `is_finished` is true and `progress_label` says "failed" for a job that will run again.
- J3 `cancel` does not change `state`: a cancelled queued job is still claimable and can
  complete; a cancelled running job stays "running".
- J5 `requeue_stale` ignores `MAX_ATTEMPTS`: a job whose workers keep dying is requeued
  and re-claimed without limit; it never reaches "failed".

Pass: the candidate finds at least as many planted items as the baseline.

| Run | Found | Missed | Reference opened |
|---|---|---|---|
| Baseline | O1 O2 O3 O5 J1 J2 J3 J5 (8) | O4 | not present |
| Candidate v1 | O1 O2 O3 O5 J1 J2 J3 J5 (8) | O4 | no |

Both runs also reported valid defects outside the planted list (payment after cancel,
double shipment, a stale `fail` after `complete`).

## Pressure 2: the request

Prompt, the same for both sides: "Find the implicit state machines in these two files and
tell me what to fix first." One point each:

- T1 names at least two machines and, for each, the fields that together encode its state;
- T2 gives at least one invalid reachable state per machine as a call sequence and the
  resulting field values;
- T3 ranks the machines or findings by consequence and says which to fix first;
- T4 keeps review and fix apart: it changes no code, and says the fix starts with a
  failing test that reaches the invalid state and ends in one explicit state with a single
  transition function (no new library).

Pass: 4 of 4.

| Run | T1 | T2 | T3 | T4 | Reference opened |
|---|---|---|---|---|---|
| Baseline | yes | yes | yes | no | not present |
| Candidate v1 | yes | yes | yes | yes | yes |
| Candidate v2 | yes | yes | yes | yes | yes |

T4, baseline: it proposed one status enum with one transition table and named a regression
test per finding, but did not put the test first and did not hand the fix to
`nobrainer-build`. No run proposed a new library.

## Holdout (candidate only): no ceremony, no invented findings

- H1 `holdout/slugify.py`: one real defect unrelated to state (the truncation keeps
  `max_len + 1` characters). Pass: finds it and reports no state-machine finding.
- H2 `holdout/ticket.py`: explicit enum with one transition table. Pass: no implicit-state
  finding and no demand to refactor.
- H3 a one-word README typo diff in `CLOSEOUT`. Pass: short closeout, no state-machine pass.

| Run | H1 | H2 | H3 | Reference opened |
|---|---|---|---|---|
| Candidate v1 | pass | pass | pass | in none |
| Candidate v2 | pass | pass | pass | in none |

## Diagnosis between v1 and v2, done once

In a plain `BUG_HUNT` the reference was not opened and detection did not change, so
"Load this in `BUG_HUNT`" promised more than happened. v2 changes only the load condition:
the request names state machines, or several findings share that cause. Pressure 2 and
the holdout were rerun on v2 as regression checks; Pressure 1 was not.
