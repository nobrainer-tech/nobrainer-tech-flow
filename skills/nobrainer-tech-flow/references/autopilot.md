# Autopilot: carry the approved plan to a checked result

Read when the owner asks for autopilot, execution of an approved plan, or work
through the whole outcome. This is the active agent's execution loop, not a
separate skill or a promise of an unattended process. Keep the host-selected
MAIN model, effort and existing authorization.

## Bind the finish line

Use the existing plan and acceptance criteria as the single state owner. Bind
the actual inputs, dependencies, write scopes and required checks. Do not
replace a supplied plan with a new one or stop after planning when execution
is already authorized. Resolve only a missing decision that changes the work.
Persist state only under the [detailed-ledger gate](../SKILL.md#show-human-progress).

## Run the next ready unit

1. **Select.** Choose work with accepted dependencies, available inputs, a free
   write scope and the necessary authorization. Use useful native workers for
   independent ready work; if unavailable, MAIN continues. A blocked unit does
   not stop another ready unit.
2. **Execute.** Perform the bounded change through `nobrainer-build`. A worker
   acknowledgement, generated plan or intended command is not execution.
3. **Check.** Run the relevant proof and required project checks. Inspect the
   changed artifact and the actual result at the promised delivery layer.
   Neither a green unrelated test nor a completion message accepts the unit.
4. **Review.** Use `nobrainer-review` where the risk, owner or project requires
   it. Bind findings to the current diff. Inspect worker output before using
   it; missing independent review stays explicit and never becomes a pass.
5. **Correct.** Confirm a defect before changing code. Invalidate its affected
   proof, make the smallest correction and rerun the relevant check and review.
   Follow the [existing corrective budget](../SKILL.md#autopilot-execute-the-bounded-scope)
   and [proportional review](delivery.md#keep-review-proportional-to-progress);
   repeated no-progress attempts require diagnosis or a concrete incomplete state.
6. **Advance.** Mark the unit accepted only from its inspected evidence, update
   the existing TODO and immediately select the next ready unit. Carry valid
   commit, PR or publication authority forward; a plan checkbox never grants it.
   Do not end the task with a milestone report while authorized ready work remains.

Use the [goal-driven state transitions](delivery.md#gdd-goal-driven-delivery-through-milestones)
when a multi-unit tracker is justified. Keep one owner for status and proof;
do not introduce another scheduler or duplicate ledger for this loop.

## Decide what happens next

- **Ready work exists:** continue the loop without asking for routine "continue"
  permission. Batch independent units only while write ownership is clear.
- **A worker is running:** advance independent work or wait for its bounded
  result. A timeout keeps the unit incomplete.
- **A result is reported:** audit its artifact, current checks and released
  writer state before accepting it.
- **A unit is blocked:** keep its requirement open, name the evidence and exact
  unblock action, and continue unrelated ready work. Ask only for the actual
  missing choice or action-time gate.
- **No required unit remains:** perform the integrated whole-goal check. Re-read
  the acceptance set and current artifacts; unresolved required checks or blocked
  items prevent completion. Stop adding work once this finish line passes.

After interruption, read the canonical plan and current artifacts before
choosing the next unit. Recheck stale dependencies and proof; never trust a
remembered Done signal or repeat already accepted work without a reason.
Checkpoint and release follow [long-run state](long-run-state.md).
Host pauses, quotas, restart and scheduling capabilities determine whether
execution can continue outside the current turn. Checkpoints alone do not
start sessions or guarantee a later wakeup.
