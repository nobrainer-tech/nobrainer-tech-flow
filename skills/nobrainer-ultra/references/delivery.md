# Deliver the agreed outcome

Read for non-trivial delivery and before reporting a blocker. Ordinary autopilot
uses this contract. `yolo` or `yolo mode`, when explicitly requested for this
workflow, is an alias for persistent execution of authorized work. It changes
neither permissions, model, budget nor the host's safety controls. It is not a
CLI flag or another skill.

## Establish the goal without another prompt

For substantial implementation, automatically derive an observable outcome and
DoD from the owner's request before editing. Reuse the existing tracker; if work
needs durable state, write a short task-local Markdown goal. Keep only acceptance,
current progress, authority and the next useful step. Do not ask the owner to
name the file or restate an already clear goal. Small answers need no artifact.

A native goal is separate: create it only when explicitly requested and supported
under the host tool contract. Reuse an existing goal; never replace an unfinished
goal or invent a token budget. Read back native goal creation before claiming it.
A Markdown goal does not promise scheduled continuation or automatically press
START. When START is owner-only, explain that requirement once; never claim it
was resumed. Within available execution time, continue useful authorized work.

When the owner says "execute the whole SDD", bind one overarching goal to all
of that SDD's acceptance IDs. Do not substitute a local milestone, plan approval,
or test suite for the whole outcome. Automatically maintain a visible TODO:
`[x] accepted with evidence`, `[>] executing`, `[ ] remaining`, `[!] blocked`.
After each accepted stage, update the canonical tracker, show the changed TODO
items and move to the next ready stage without requesting "continue". Keep
blocked IDs open while independent stages advance. Use short stage labels; link
long evidence. No phase silently disappears from the full-scope acceptance set.

A request to set a goal or execute the whole SDD with a goal authorizes native
goal creation when the host permits it. If the host requires an explicit native
goal request and the wording does not meet that requirement, maintain the
Markdown goal and ask once in BUDDY if native continuation is wanted. Never imply
that a Markdown file activated host scheduling. Update the file after each stage;
use native updates only for operations the actual tool supports. A host that only
supports complete/blocked must not receive invented native progress updates.

Carry authority across turns. Translate "go ahead" against the immediately
proposed concrete action and preserve its target and exclusions. Do not ask for
permission again for that action. New consequences outside that scope still need
approval. A worker's completion is one milestone, not completion of the goal.

## BUDDY: collect the permission package once

After initial read-only discovery, identify the concrete actions needed to finish
the whole scope. Classify each as already authorized, routine/reversible within
scope, or requiring a missing owner decision. Resolve routine implementation
choices yourself. Ask one bundled, plain-language question only for missing
consequential permissions. Name exact projects/targets and effects: for example
merge these changes, deploy this service, or create this paid resource within a
specified ceiling. Include browser actions when they carry those effects; merely
opening a page is not a separate permission category.

Record the answer and any exclusions in the existing tracker. Do not seek a blank
check to spend, message people, delete data or bypass controls. Unforeseen new
consequences still need consent. Preserve refusals and ceilings across stages.
If a late gate is unavoidable, finish its preparation first and continue any
independent work while the question is pending.

## Short work communication

Use terse, natural progress text: result, TODO delta, next action. Avoid repeated
skill announcements, schema dumps and unchanged polling narration. Do not enforce
a word count that loses conditions, errors, commands or required human actions.
Keep authored documents and product copy complete and natural.

For a true owner blocker, say: `Blocked: <acceptance item>. Tried: <method/result>.
You: <exact action and destination>. Then: <how work can resume>.` Include an
exact link or copy-ready command when verified. Do not ask the owner to invent
the next diagnostic step. A paused native goal with an owner-only START requires
an explicit START callout, not a claim of automatic resumption.

## Resolve an obstacle before escalating it

Separate authority from capability: a permitted action may lack a tool, and an
available tool may not authorize an action. Before saying BLOCKED, identify the
exact failed operation and the acceptance item it prevents. Then:

1. Check related instructions and current evidence, including prior permission.
2. Discover the relevant supported API, CLI or browser capability. An authenticated
   UI step is agent work when its action and target are already authorized. Inspect
   the UI, perform the step and read back the result rather than asking the owner
   to click merely because it is in a browser.
3. If the preferred method is technically unavailable, try a relevant permitted
   alternative within the same scope. Never evade an access denial, approval
   rejection, sandbox or an explicit channel restriction through another method.
4. A missing credential means inspect the documented credential location or normal
   login flow without exposing secrets. Human MFA, unavailable entitlement and
   an owner-only decision remain genuine blockers for dependent work.
5. Continue independent acceptance items. One blocked integration cannot turn
   an entire backlog into BLOCKED or justify unrelated speculative work.

A failed test is a repair task. Missing evidence is a verification task when the
agent can obtain it. A missing optional helper is a MAIN fallback. Poll timeouts
are observations; preserve the same handle and use bounded waits. A terminal
worker failure requires reconciling writes before MAIN takes over. Do not use a
terminal failure to justify accepting unreviewed output.

When no permitted path remains, report only: the blocked acceptance item, attempted
method and observed error, why relevant alternatives cannot complete it, the exact
missing human action/access, and what independent work was completed. Distinguish
OWNER_ACTION, EXTERNAL_UNAVAILABLE, POLICY_DENIED and TECHNICAL_FAILURE. Apply
native goal blocked-state rules separately; do not mark a whole goal blocked while
useful authorized work remains. Never turn an unknown right/license into consent.

## Keep review proportional to progress

Review the next executable slice against concrete acceptance and failure paths.
For a stable slice, default to one review and one focused correction verification.
More review needs a newly evidenced material defect or changed risk, not a new
amendment number, stylistic preference or desire for perfect prose. Preserve
required independent/security gates; a review budget never makes a failed gate pass.

After repeated review without accepted progress, stop the whole-plan loop. Deduplicate
findings, retain blockers for the affected slice, defer non-blocking suggestions,
and implement an already-authorized independent slice or resolve the concrete
blocking defect in MAIN. Escalate only an actual unresolved owner choice. Do not
reset the review budget by renaming a plan or opening a new reviewer task.

Prefer maintainable code over line-count games. Honor real project limits by
cohesive decomposition; do not invent arbitrary caps or spend worker cycles on
blank-line shaving. Re-run only checks affected by the final change plus required
repository checks. Finish after acceptance, not after an arbitrary quantity of
reviews, tests or generated files.

## Coordinated team execution

MAIN owns the full outcome, dependencies, integration and acceptance. Before each
batch, identify independent ready work and available native delegation capacity.
Target concurrency is the minimum of the host/model limit, 15 live subagents
across the entire task tree, and the number of useful independent ready units.
The cap excludes MAIN. Count running reviewers and nested agents too. If native
capacity is unknown, dispatch useful units incrementally until the advertised
limit or a capacity refusal; never spawn dummy probes. Reconcile uncertain spawn
results by ID before retrying. If a send may have succeeded but returned no ID,
reserve its possible capacity and write scope; do not retry or run that unit in
MAIN until the host proves no worker is executing. Record delivery UNKNOWN in
the existing tracker. This differs from proven pre-send unavailability, which
permits MAIN fallback. A refusal reduces concurrency; it is not a goal
blocker. Never bypass a host restriction or substitute visible conversations.

Each assignment names the desired result, input sources, exact write scope,
dependencies, acceptance evidence and stop conditions. Schedule independent
implementation, research and verification together only when mutable state does
not overlap. Use isolated worktrees where appropriate, then integrate explicitly.
Workers do not recursively delegate unless MAIN grants a reservation under the
same global cap; when reliable cross-tree accounting is unavailable, use flat
MAIN-owned delegation. Apply the [model policy](model-routing.md), including its Codex delegated
preset; preserve explicit owner overrides.

Prioritize work that unblocks downstream stages. MAIN advances useful integration
or unresolved dependencies while workers execute; do not hold a meeting or poll
unchanged status as a substitute for work. Queue excess units. Review each result
against its artifact and required checks, release the worker's write ownership,
then fill the freed slot with ready work. Shared sequential work remains serial.
Do not split a tiny task merely to reach a number. Measure progress by accepted
outcomes and elapsed delivery, never by agent count or messages sent.

## GDD: goal-driven delivery through milestones

GDD is this workflow's execution pattern, not a new skill or a claim of inventing
Goal-Driven Development. SDD owns requirements; the existing task tracker owns
milestones and current state. For whole-SDD execution, derive milestones from its
acceptance set. Each milestone records an ID, observable outcome, acceptance IDs,
dependencies, owner, write scope, evidence and state. Every required acceptance ID
must be assigned; cross-cutting criteria need a final integrated check.

Use `PENDING -> READY -> RUNNING -> VERIFYING -> ACCEPTED`. `READY` requires
accepted dependencies, necessary permission and a free write scope. A failed
verification returns to repair; an external dependency marks only the affected
milestone `BLOCKED` with its evidence and unblock action. Resume after fresh
verification of that action. Superseded requirements invalidate only affected
milestones and downstream evidence. Completed workers never self-accept.

After each milestone, MAIN verifies evidence, updates the existing TODO and
selects the next ready work without waiting for a new user prompt. Independent
milestones may run together under the team cap. Keep one overarching goal open
until every required milestone and integrated DoD passes. Do not complete and
replace the native goal for each milestone. Native goals are optional mirrors;
Markdown remains the portable record. Host pauses or quotas can suspend execution,
so preserve the next action without promising an automatic wakeup.
