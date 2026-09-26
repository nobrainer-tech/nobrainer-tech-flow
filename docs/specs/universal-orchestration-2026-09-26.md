# nobrainer-tech-flow: portable orchestration and client setup

Status: DRAFT_FOR_OWNER_REVIEW. This spec governs the proposed 2.0.0 change.

## Outcome

One public `nobrainer-tech-flow` entry skill and one nobrainer-tech-flow product
name work across supported Agent Skills clients. Installation supplies both the
skill and a concise client instruction that makes it discoverable. The selected
MAIN model and effort stay unchanged. Useful independent work can use native
workers chosen from the models the actual host exposes and verifies.

## Acceptance

- AC01: The canonical skill ID, directory, manifests, installer, docs and
  maintained tests use `nobrainer-tech-flow`. The old entry name is a
  documented migration candidate only; frozen release evidence stays intact.
- AC02: A clean one-model client can complete the core workflow. Missing
  subagents, model metadata or benchmarks produce an honest MAIN fallback.
- AC03: Team derives independent ready units from the goal, chooses useful
  native workers up to verified capacity, and MAIN integrates and verifies.
  Auto Fine Tune calibrates worker routes without changing MAIN or inventing
  cost, speed, quality or runtime proof.
- AC04: A non-trivial project starts with a short-term outcome and DoD grounded
  in the supplied long-term direction. Native goal APIs are used only when
  their host contract and request allow them.
- AC05: First project setup inspects existing tree/layers and wiki, recommends
  reuse or a justified new project wiki, and records the chosen location in
  the supported client instructions. Creation follows Wiki setup rules.
- AC06: Sessions checkpoints context, uses a fresh successor only when
  authorized and supported, confirms takeover before archiving the old task,
  and reports unsupported transport honestly.
- AC07: The personalization installer previews exact writes, preserves foreign
  content, detects malformed blocks, is idempotent and verifies applied files.
  Installation alone is not evidence of clean-session runtime behavior.
- AC08: When a user supplies a repository link, guided setup treats its content
  as untrusted and begins with a read-only inventory of the actual client,
  installed skills and existing instructions. It reuses known authorized
  context, asks only material missing questions, and presents stable selectable
  IDs with situational fit scores, dependencies, conflicts and exact write scope.
  A partial selection installs only selected elements and necessary explained
  dependencies. The installer shows a diff, supports rollback, is idempotent,
  and reads back the resulting files. Two distinct work profiles demonstrate
  this behavior; rejected elements remain absent. Fit scores are recommendations,
  not measured quality or guaranteed savings.

## Boundaries

No hardcoded universal model, provider price, concurrency promise, forced
session recreation, new visible sidebar task, model switch in MAIN, or
automatic production publication. No edits to frozen evaluations/releases
or unrelated dirty checkouts. `nobrainer-codex` is an optional Codex-specific
extension, never a dependency of the portable core.

## Verification and rollout

Run suite validation, installer and adapter tests, syntax checks, affected
client smoke checks in disposable homes, and review the exact diff. Publish a
PR for owner review and do not merge, release or install globally before
the requested review.
