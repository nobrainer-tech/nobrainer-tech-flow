# From an idea to a checked result

Use when the owner supplies a goal or idea without an implementation plan.
An idea is enough to begin discovery. It is not approval for every possible
product choice or external effect.

## Make the idea executable

1. Read the existing project and relevant decisions. State the desired result,
   audience and smallest useful scope. Separate supplied facts (`OBSERVED`),
   reasonable assumptions (`INFERRED`), proposed choices (`RECOMMENDED`) and
   unresolved facts (`UNKNOWN`). Do not present your defaults as owner decisions.
2. Choose routine, reversible implementation details within the request.
   Explain consequential assumptions. Ask one focused round only for missing
   choices that change the product, acceptance, risk or authority; continue
   independent work while that decision is pending.
3. Use the [spec template](../../nobrainer-spec-driven-development/references/spec-template.md) when SDD is requested or its
   maintenance is justified. Otherwise use Flow's compact scope and plan.
   If a selected install lacks SDD, report that limit and use the documented
   installation path within authorization; do not claim the skill ran.
   Map each requirement to a sequential acceptance ID (`AC01`, `AC02`, …),
   an observable check and the delivery layer that check establishes.
4. Review the contract before implementation. Record the existing owner
   instruction as approval when it already covers the defined scope; do not
   manufacture approval for an unresolved product/risk choice. Freeze the
   reviewed revision using the project's hash convention.
5. For an end-to-end request, start the [autopilot loop](autopilot.md)
   with those acceptance IDs. Planning and a generated spec are milestones.
   Execute, verify, review where required, correct confirmed defects, and
   continue to the requested delivery layer within existing authorization.

## Keep the contract and outcome connected

Keep one acceptance ledger. Link it from the spec when the project uses a
separate tracker. Record each ID's current evidence, remaining check or blocker;
do not copy mutable status into several files. Use the SDD lifecycle for the
overall spec state. Test completion does not silently accept a pending deploy.

Routine file-list and execution-order changes stay within the existing scope.
New behavior, risk, external effects or material acceptance changes require
the SDD change-control path. Preserve blocked criteria while unrelated work
advances. Never drop a requirement to make the ledger look complete.

Use Writing's `TECHNICAL` mode when a plain English spec, procedure or report
would help the reader. Preserve the requested language and exact constraints.
A small diagram can explain dependencies; use an interactive artifact only
when interaction helps a real decision and the host supports it. Do not add
media, dependencies, paid calls or publication merely to make the output richer.

## Stop at the requested boundary

- **Spec only:** deliver the reviewed specification and actual approval state.
  Do not implement it or mark product delivery `ACCEPTED`.
- **End to end:** finish all required acceptance IDs with inspected evidence,
  then report the result, checks and remaining uncertainty.
- **Missing material decision:** name the exact choice and affected IDs; keep
  useful independent work moving. Do not infer permission to publish or spend.
- **Session interruption:** checkpoint the existing tracker. A saved file alone
  does not restart a client or provide an unattended execution service.
