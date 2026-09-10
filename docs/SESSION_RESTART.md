# Adaptive session restart

Development source adds automatic Flow startup care to the v1.8.1 restart
protocol. Published tags remain unchanged; v1.8.1 is the rollback baseline.

Invoke NoBrainer.Tech Flow with your task. Flow runs startup naming and health assessment
without a separate restart command. It records adaptive policy within the task's
authorization, preserves an existing `off` policy and obeys stricter host consent
rules. Installation or incidental skill loading alone authorizes no mutation.
Explicit automatic-restart consent remains valid for later rotations in scope;
archival needs its own recorded authorization. Ordinary delegation uses native
subagents; creating a separate visible conversation requires an explicit owner
request or an explicitly authorized MAIN restart.

On entry, supported clients name the session `<task title> | started DD-MM` using
its actual creation timestamp and owner/task timezone (recorded UTC fallback).
Resume preserves that date; a successor receives its own creation date. Missing
metadata is unavailable, never replaced with today's date. Supported mutations
are read back. Session IDs, goal identity and checkpoint digest remain authoritative.

Flow assesses available context measurements and the complete next startup,
including required skills, metadata, tools, checkpoint and necessary re-reads.
It records measured versus estimated inputs and keeps missing values unknown.
The agent performs the check at entry, after compaction and accepted milestones;
there is no new daemon or timer-only model call.

Health and economic benefit are independent reasons to rotate. A current pressure
signal or at least 70% observed context occupancy, together with a complete fresh
startup at most 80% of current input, qualifies the health path. Those are policy
heuristics, not measured optima. Remaining work, progress since the last restart,
verified checkpoint and safe native ownership transfer are still required.
Two compactions and optional daily age of 24 hours trigger assessment only.
A small post-compaction context or equally large startup can make continuing wiser.

Routine care stays quiet. Report one successful continuation or an actionable
capability failure. After takeover, compare observed startup and missing-context
rework with the estimate in the same task state.

The core is the [Sessions protocol](../skills/nobrainer-sessions/references/session-restart.md),
usable as instructions in any capable client. An optional deterministic helper
can be invoked by hooks. There is no universal hook event or universal archive
API: adapters must verify capabilities and map their actual lifecycle events.
A client without safe native transport prepares a manual continuation packet.

For the independent economic path, the helper calculates a conservative raw token proxy over at most three future
calls. Its defaults are heuristics, not an optimum or a billing forecast. Current
input, fresh startup and restart overhead can be observations or explicitly
labelled estimates. Missing metrics remain unknown. Large fixed instructions,
cache reuse and necessary re-reads may make restarting more expensive.

Quality is protected by checking the handoff before transfer, not by assuming
fresh sessions are smarter. Do not restart if acceptance, decisions or required
evidence cannot be reconstructed reliably. Do not archive the old session after
mere creation or a read-only ACK. Verify takeover first; archive failure never
returns implementation ownership to the old session.

## Proof and remaining limits

The shipped helper is tested with real CLI invocations and deterministic failure
cases. It only chooses actions from supplied observations. It does not collect
usage, authenticate an ACK, implement a lock, run a model, create sessions or
archive them. Native transport requires separate adapter runtime evidence.
No all-client automation, token-saving percentage or quality improvement has
been measured for this feature.

No new permanent module, scheduler, background service or global hook is added.
Existing `nobrainer-sessions`, `session-handoff` and manual recovery stay available.
Disable further rotation with policy `off`; a committed transfer never permits
both old and new sessions to resume writing.
