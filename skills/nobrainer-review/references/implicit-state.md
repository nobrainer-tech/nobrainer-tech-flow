# Implicit state machines

Load this when someone asks for implicit or hidden state machines (`nb-auto-fix`), or
when a review finds several defects with one cause: a lifecycle kept in several loose
fields, such as a status, flags, timestamps, a counter and a lock.

An implicit state machine is one state spread over several fields that the code reads
together, with no single place that says which combinations are allowed. It lets the
program reach states nobody designed: a job both finished and queued, a cancelled order
that still ships, a lock nobody releases.

## 1. Find candidates

Read each hit in context; a field alone proves nothing.

| Signal | Example |
| --- | --- |
| Booleans that describe one thing | `is_loading`, `is_error`, `paid`, `refunded`, `cancelled` |
| Nullable fields read together | `started_at` + `finished_at` + `failed_at`; `data` + `error` |
| A status kept as free text | `status = "pending"` written in several places, compared with literals |
| Step or phase counters | `step += 1`, `attempts`, wizard indexes |
| Lock, lease and retry state | `locked_at`, `worker`, `heartbeat_at`, idempotency keys |
| State stored twice | a database column and a cache key, a URL parameter and server state |
| Derived labels | a function that turns the fields into a label in its own order of checks |

## 2. Map each machine

Write down, briefly:

- **Fields** that together encode the state, and the **states** the code means.
- **Writers**: every function that changes one of those fields, with `file:line`.
- **Readers**: every function that decides from them: guards, labels, counts.

## 3. Search for states nobody designed

For each writer, ask what the other fields look like afterwards, and which reader then
decides wrongly. Then walk the transitions nobody wrote:

- a failure or timeout between two writes, which leaves a lock or a start time behind;
- cancel, refund or undo after partial success;
- retry after failure, and the attempt limit being reached;
- the same call twice, or two callers at once;
- a stale actor finishing late, such as a worker that lost its lease and still completes;
- reload, a second session or out-of-order events, where state lives in two places.

A finding needs a concrete sequence of calls or events and the resulting field values,
proved by the code path, a test or a reproduction. "State may be inconsistent" is not a
finding.

## 4. Report

One row per machine, ranked by consequence: money or data loss first, then someone stuck
or misled, then cosmetic.

```text
MACHINE: <name> | fields | states | invalid reachable state (sequence -> result) | risk
```

Each row still passes the normal finding gate. Code that already keeps one explicit state
with one transition function has no finding here: do not ask for a rewrite.

## 5. The fix belongs to Build

Review reports; `nobrainer-build` fixes, one machine per change. First a failing test that
reaches the invalid state. Then one explicit state (an enum or a tagged value) with a
single function that performs every transition, in the project's own idiom and without a
new state-machine library. Behaviour stays the same except for the defect. A change to a
public API, a stored schema or user-visible behaviour needs the owner's approval first.
