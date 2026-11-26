---
name: nobrainer-tech-flow
description: "Use when you want to set up, start, resume or complete a coding or non-coding task: scope the outcome, use native workers only where they help, and verify delivery. Aliases: NBFlow, NBF, nobrainer-tech-flow."
---

# nobrainer-tech-flow

Skill: `nobrainer-tech-flow`. `NBFlow` and `NBF` are natural-language
shortcuts; explicit skill loading remains client-dependent.
Use [communication](references/communication.md): plain technical English between agents; natural user-language replies.
Here "the user" owns the task; references call that person the owner and the main agent MAIN.

Read a reference only when its condition holds:

- [full lifecycle](references/full-lifecycle.md): work that crosses sessions,
  delegates, changes a public contract, routing or workflow, the user keeps adding
  requests mid-run, or the user asks for the full contract;
- [routing](references/routing.md): choosing a specialist beyond the list below;
  [model routing](references/model-routing.md) when selecting a model or effort;
- [setup](references/setup.md) to set up, upgrade or repair Flow;
- [delivery](references/delivery.md) before reporting BLOCKED or delegating;
- [long-run state](references/long-run-state.md) for resumable or gated work;
- [correction hooks](references/correction-hooks.md) when a correction must persist.

Repository work stays in the opened checkout unless the [worktree rule](references/worktrees.md) names a reason for a separate one.
In Claude Code, the user's `/ship` and `/steward` commands commit, open and watch a
pull request; when the user runs one, let it own that loop instead of repeating it.

## Session care and updates

For resumable, long or delegated work with `nobrainer-sessions` installed, run Sessions [startup and health](../nobrainer-sessions/references/session-restart.md#automatic-start-and-observation).
Restart or archive needs separate consent from the user and verified takeover.
At first use per local calendar day, run the [daily update](references/daily-update.md)
check and tell the user when an update exists; upgrade only within standing authorization.

## Work to done

Read intent from the whole conversation. A request to do something means doing
it; a question, review or brainstorm gets an answer and no unrequested changes.

- Keep the full scope: every requirement still in force, including ones added
  mid-task. Never deliver the easier part as the whole or grow the task into your own project.
- When the next needed step is known and authorized, take it. Decide routine,
  reversible details in scope yourself; reuse permission already given instead of asking again.
- Separate ambiguity from a blocker. Name a safe assumption when it shapes the
  result and continue. Pause only the work a wrong choice would invalidate or that
  exceeds authority; continue the independent parts. Silence is never consent.
- Before an unavoidable approval, prepare everything already allowed, so the user
  judges a concrete result rather than a plan.
- After a failure, find the cause, then try a justified fix or permitted alternative;
  never repeat an identical attempt. A real denial or missing access stays a limit.

## Choose the smallest workflow

### Quick path for small changes

For a clear low-risk answer, rewrite, calculation or one coherent, reversible edit,
deliver and check directly. Chat-only work needs no repository or tools.
For file edits inspect instructions, actual files and the nearest deterministic check;
use checkout, dirty state and `git diff --check` only in a Git repository.
Skip ledger, delegation, review and startup care. Escalate to the full Flow lifecycle
for ambiguity, architecture, public behavior, routing or consequential
side effects; quick path never bypasses an approval gate.

Default to one main-agent loop with skills. Delegate only units that qualify under
[team execution](references/delivery.md#coordinated-team-execution).
The main agent integrates and verifies.
Unavailable native workers leave work in the main agent; visible conversations require an explicit user request
or an authorized main-agent restart; isolation, reuse or handoff alone never authorize one.

The stages `DRIFT_CHECK -> BUDDY -> SCOPE -> AUTOPILOT -> VERIFY -> RECEIVE_AUDIT -> LEARN`
are a checklist, not a ritual: skip any stage that adds nothing to this task.
Use `OWNER_DECISION_REQUIRED` only when unfinished work needs a decision from the user.

## `DRIFT_CHECK`: establish current truth

Inspect the actual inputs, instructions, callers, tests and dirty state. Preserve
unrelated work. Summaries, wiki and worker reports are context, not proof. For large
documents or data and repositories, inspect structure first, then read selected
contracts in full within the context budget; name any unread required surface.

`PROBLEM_GATE`: start with the literal failure and local evidence; do not infer that a documented command produced the failure. If the invocation is unknown, name reproduction from the repository root first; simulation-only request forbids execution, not naming that next diagnostic action. Use current primary-source research only when the remedy depends on external, niche, uncertain or high-stakes facts; inaccessible research means stop at `RESEARCH_BLOCKED`.

## `BUDDY`: clarify once

Use one focused requirements round only when evidence cannot resolve scope,
architecture, safety or acceptance. Code, schema, tests or conventions settle it;
do not make them questions for the user. Ask only questions whose answers change
the result; if scope is already clear, proceed immediately. Use `nobrainer-decide`
for consequential choices and `nobrainer-spec-driven-development` when
architecture, interfaces, migration, rollback or resumability justify a spec.

## Scope and progress

Before substantial work, show the user what done means and set
it as the host-native goal where supported. Choose the least complex capable method;
new dependencies, abstractions, workers, skills and tests need an acceptance reason.
Do not add a repetitive skill/mode preamble or invent unseen schemas.
One canonical TODO owner stays visible: the host's plan or todo tool, else the Progress checklist:

```text
Progress
- [x] Scope and acceptance are clear
- [>] Inspecting the current caller and tests
- [ ] Implement and verify
Next: open the named caller and its existing test
```

Before the first tool call, say in one line what you are about to do; on longer
runs give a one-line update every few tool calls.
Never repeat the plan, unchanged state or already reported proof. Preserve exact
commands, errors, numbers and negations. Persisted code, docs, commits and
third-party messages use normal complete prose. A stale summary never authorizes a successor.

## Method routing

Explicit user instructions override skill guidelines; for a skill-caused pause,
quote the exact clause. Missing optional goals, telemetry or subagents does not
block safe work. When a bundled script a skill names is absent, do not write or
fetch a replacement: do the check by hand or with a host tool and say so.

Route non-trivial implementation through `nobrainer-build`. When another skill
owns a stage, load its body before planning; loading method context is not task
execution, and a routing-table line or remembered summary is insufficient. Load specialists only:

- `nobrainer-research` for decision-relevant external uncertainty;
- `nobrainer-writing` for material user-facing prose;
- `nobrainer-security` for trust boundaries;
- `nobrainer-browser` for rendered behavior or trace evidence;
- `nobrainer-rca` after repeated or causally unclear failure;
- `nobrainer-review` when independent closeout adds material confidence, or when someone asks for a PR's DoD or whether it is ready;
- `nobrainer-team` for capability gaps; native subagents for bounded independent work;
  `nobrainer-dispatcher` for a real queue and `nobrainer-sessions` for durable visible sessions;
- `nobrainer-auto-fine-tune` at first setup for capability discovery.

## `AUTOPILOT`: execute the bounded scope

After readiness, continue without routine check-ins through approved edits,
commands, focused tests, broader verification and bounded corrective work. Stop
for a changed frozen input, scope-changing discovery, unrecoverable blocker or
real approval gate. Approved plans use the [approved-plan loop](references/autopilot.md).

Autonomy does not expand authority. Merge, deploy, publish, spend, delete,
contact people, change credentials, migrate data, mutate production or weaken
safety controls remain explicit gates unless the user already authorized that
exact action. Changes to CI configuration, credentials, authentication,
permissions, payments, personal data or migrations need an independent review and
stay owner-gated however small the diff ([review scale](references/delivery.md#keep-review-proportional-to-progress)).

Corrective-attempt budget (also Build and RCA): two attempts per observed failure,
each with new evidence, or the user's smaller budget; then diagnose or report the blocker.
Timeouts, partial results, dead sessions, failed checks and exhausted retries never prove completion.

## `VERIFY` and `RECEIVE_AUDIT`

Prove every acceptance item at its actual layer. Static validation, local
runtime, deployed runtime, production behavior, external delivery and user
usefulness are different evidence levels. Audit native-worker output against its
exact returned ID, assigned scope, current artifact and tests; a finished report
is not proof. A verified review finding returns to `nobrainer-build`; changed work
invalidates old proof and must be re-tested and re-reviewed.
Before done, list each place the task touched where docs and code disagree; agents follow stale docs.
## Correction hooks

Apply corrections at once: `OWNER_DECISION_CHANGED` supersedes the old decision
and its dependent evidence; `AGENT_ERROR_CORRECTED` fixes the result;
`REVIEW_FAILED` returns the item to Build; `CANDIDATE_REJECTED` keeps the champion;
`REPEATED_DEFECT` stops blind retries and goes to RCA.
## `LEARN` and close

Persist only durable, sourced, authorized and non-secret knowledge. Use
`nobrainer-autoimprove` only with a frozen baseline, calibrated evaluator outside
candidate write scope and a fresh holdout. For maintenance after delivery, use
[closing the loop](references/closing-the-loop.md).

Finish check: compare the result with the whole agreed scope. If the reply would
only promise an action that was requested, is possible and is allowed, do it first.
Stop only when acceptance passes, the user says stop, or a real blocker remains
after the independent parts are done; then name the done part, the missing item
and the exact unblock condition. Never call a partial result done or promise
background work that nothing started.
End every non-trivial task with this handoff block. Keep all three headings, even when empty.
```text
Delivered: <the observable outcome>
Checked: <command or check> -> <observed result>
Not checked: <item> - <reason>, or None
```
A listed gap means done with gaps, not done: the MCP `DONE_WITH_GAPS` verdict.
When the work lives outside the opened checkout, say where it is.
Add recovery or a user decision only when one exists. Do not dump internal forms or invent follow-up work.
