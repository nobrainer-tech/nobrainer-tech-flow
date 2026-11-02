# Closing the loop after delivery

Use when a delivered system needs ongoing maintenance: a production signal should
start diagnosis and a proposed fix without someone noticing it first. The loop
finds, diagnoses and proposes. Nothing in it merges, deploys, mutates production
or changes credentials on its own; those stay the normal owner gates.

## Detect against a stable baseline

1. Pick one metric with a stable rolling baseline, such as CI failure rate,
   post-deploy 5xx rate or PR cycle time. Add a second metric only after the
   first one produces findings people act on.
2. Detect with a deterministic script the project owns: version-controlled,
   unit-tested, and based on mean and standard deviation or Western Electric
   rules. A model may explain a breach; it does not decide whether one happened.
3. Keep the tiers in a project config file, `bands.yaml` by default:

   | Band | Action |
   | --- | --- |
   | 1σ | log only |
   | 2σ | read-only diagnosis through `nobrainer-rca` |
   | 3σ | propose a fix as a PR through `nobrainer-build` behind the normal PR gate, or run a pre-approved runbook |

   A runbook is pre-approved only when the owner approved that exact runbook and
   its effects; a breach never widens it.

## Run unattended, verify like any unattended run

Each run is stateless. A schedule, a webhook or a control-band breach starts it,
with no human in the invocation path. The baseline, bands and last-processed
marker live in the repository or the metric store, never in a session.
A trigger, log line or exit code is only an observation: check every run with
[unattended-run evidence](routing.md#unattended-run-evidence) before calling it
healthy.

## Turn each finding into an intent record

Write every 2σ or 3σ finding as an intent record with the sections from
[record the intent](idea-to-delivery.md#record-the-intent): Problem, Proposed
outcome, Affected users and systems, Constraints, Open questions. Attach the
metric window, the band and the RCA evidence reference.

Triage each record as one of:

- **fix now**: a bounded fix through Build and the normal PR gate;
- **schedule**: keep the record open in the project's existing tracker;
- **dismiss**: close it with a reason, and use that reason to tune `bands.yaml`
  through a reviewed change, so the same noise stops recurring.

Every shipped fix adds a frozen scenario (eval) and a regression test that would
have caught the breach. Without both, the fix is not done.

## Recurring security scan

Schedule `nobrainer-security` `SECURITY_REVIEW` scoped to the changes since the
last scanned commit SHA. Record the new SHA only after a complete scan; a partial
scan keeps the old one. Dedupe candidates against earlier findings by location
and causal path, not by wording. A bounded patch goes through Build and the PR
gate; a larger finding becomes an intent record. The scan stays read-only and
never tests a live target without the authority Security already requires.

## On call

A channel message or ticket starts the same path: route it to `nobrainer-rca`
with the frozen incident statement. Persist the post-mortem as the RCA skill
describes, under `docs/incidents/` or the project's existing incident home.
Confirm recovery by reading back the metric, endpoint or state that failed,
never from a message saying it is fixed. Containment that changes production
needs its owner gate.

## Measures

Leading:

- breach-to-intent time: from a 2σ breach to its committed intent record;
- share of repositories on the scan schedule.

Lagging:

- share of findings merged as fixes, against scheduled and dismissed;
- repeat-incident rate: incidents whose fingerprint matches an earlier one.

A rising dismissal share means the bands need tuning, not a quieter channel.
