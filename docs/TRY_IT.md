# Try nobrainer-tech-flow on one task

Install from the [reviewed source and dry-run](INSTALL.md), restart your client,
and check that it can discover `nobrainer-ultra`. A successful file installation
is not a successful model run. Pick one small trial and inspect the artifact.

## An everyday task

In an ordinary empty folder, ask:

> Use nobrainer-tech-flow. Create invitation.md for a free board-game evening on 18 September
> at 18:00, ending at 21:00, at the community room. Bring a game if you have one;
> newcomers are welcome. Also make checklist.md with the organizer's preparation
> tasks. Use only these supplied details. Do not initialize Git or add frameworks.

Accept when both files exist, the invitation preserves every supplied fact and
the checklist is usable. Reject invented addresses, prices or contact details,
unrequested project scaffolding, and claims about checks that were not performed.

## A small code correction

In a disposable copy of a project with a known failing test, ask:

> Use nobrainer-tech-flow. Reproduce the failing test, find the cause and make the smallest
> correction. Run the affected test and the project's required checks. Keep
> unrelated files unchanged. Report the actual results and remaining uncertainty.

Accept when the original failure is reproduced, the correction addresses it,
the relevant checks pass and the diff stays in scope. A plausible explanation
or a green unrelated test is insufficient. Do not use a live incident as a demo.

## Evaluate the result

Record the client and version, model and effort, source commit, task, files
changed, human interventions, checks and elapsed time. Record tokens or cost
only when the client reports them; otherwise use UNKNOWN.

Compare the same task with the same client/model/settings without this suite.
Keep failed runs and repeated trials. A single satisfying result is useful
feedback, not evidence of universal superiority or cheaper-model equivalence.

If a task hangs or floods output, see the optional [bounded command runner](BOUNDED_RUNNER.md).
It controls a command's execution; the task's acceptance still needs inspection.
