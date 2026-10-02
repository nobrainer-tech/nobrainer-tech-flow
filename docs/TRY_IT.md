# Try nobrainer-tech-flow on one task

Install from the [reviewed source and dry-run](INSTALL.md), restart your client,
and check that it can discover `nobrainer-tech-flow`. A successful file installation
is not a successful model run. Pick one small trial and inspect the artifact.

## An everyday task

In an ordinary empty folder, ask:

> Use NBFlow. Create invitation.md for a free board-game evening on 18 September
> at 18:00, ending at 21:00, at the community room. Bring a game if you have one;
> newcomers are welcome. Also make checklist.md with the organizer's preparation
> tasks. Use only these supplied details. Do not initialize Git or add frameworks.

Accept when both files exist, the invitation preserves every supplied fact and
the checklist is usable. Reject invented addresses, prices or contact details,
unrequested project scaffolding, and claims about checks that were not performed.

## A small code correction

In a disposable copy of a project with a known failing test, ask:

> Use NBF. Reproduce the failing test, find the cause and make the smallest
> correction. Run the affected test and the project's required checks. Keep
> unrelated files unchanged. Report the actual results and remaining uncertainty.

Accept when the original failure is reproduced, the correction addresses it,
the relevant checks pass and the diff stays in scope. A plausible explanation
or a green unrelated test is insufficient. Do not use a live incident as a demo.

## From an idea to a working result

In a disposable folder, ask:

> Use NBFlow. I have an idea for an offline CLI that turns Markdown meeting
> notes into an action-item list. Use SDD and deliver it end to end. Use Python
> standard library only, keep input files unchanged, and make no network calls.
> Choose routine reversible details. Ask only when a missing choice changes
> scope or acceptance. Do not initialize Git, publish or send messages.

Accept when the reviewed spec connects each requirement to an observable check,
the CLI works on the agreed examples, and every required acceptance ID has
inspected evidence. Assumptions must be visible. A spec alone is not delivery;
a spec-only request must not start implementation.

## Make a technical procedure easier to follow

> Use nb-write in TECHNICAL mode. Rewrite this English runbook as a procedure.
> Keep commands and identifiers exact. Preserve prerequisites, permissions,
> uncertainty and safety conditions. Return the finished text.

Accept when the instructions are easier to follow and no material meaning has
changed. Test conditions and exceptions, not just sentence length. This mode
uses selected clarity principles informed by ASD-STE100, not a full compliance
checker. It does not replace qualified review of safety-critical instructions.

## Carry an approved plan through autopilot

Use a small, approved plan in a disposable project. Give each task a checkable
result, name the required validation commands, and state any commit or publication
authority separately. Then ask:

> Use nobrainer-tech-flow in autopilot to execute this approved plan through its
> full acceptance criteria. Keep the goal and remaining work in the existing plan.
> Execute the next ready unit, run its relevant checks, fix confirmed defects and
> continue without asking me to say "continue". Use independent native workers
> and review when useful and available. Keep unrelated work unchanged. Ask only
> for a material missing decision or an action that still needs authorization.
> Finish with the delivered result, actual checks and anything still unverified.

Accept when every required result has inspected evidence, corrections have been
rechecked, and no required task quietly disappears. If one unit is blocked,
independent ready work should continue. An exhausted retry or missing approval
keeps the affected result incomplete; it is not a reason to invent success.

Autopilot guides the active client. It does not install an unattended runner,
reopen a closed client or create a scheduler. Checkpoints support a later resume;
automatic continuation needs a supported host mechanism and its own authorization.
See [delivery](../skills/nobrainer-tech-flow/references/delivery.md) and
[long-run state](../skills/nobrainer-tech-flow/references/long-run-state.md).
The [autopilot loop](../skills/nobrainer-tech-flow/references/autopilot.md) defines
the next-unit decisions and whole-goal completion check.

## Evaluate the result

Record the client and version, model and effort, source commit, task, files
changed, human interventions, checks and elapsed time. Record tokens or cost
only when the client reports them; otherwise use UNKNOWN.

Compare the same task with the same client/model/settings without this suite.
Keep failed runs and repeated trials. A single satisfying result is useful
feedback, not evidence of universal superiority or cheaper-model equivalence.

If a task hangs or floods output, see the optional [bounded command runner](BOUNDED_RUNNER.md).
It controls a command's execution; the task's acceptance still needs inspection.
