---
name: nobrainer-wiki
description: "Use when the owner says nb-wiki, nb-add, nb-get, nb-tidy, or llm-wiki; asks to create or query a wiki, save durable knowledge, or safely audit and maintain a Markdown knowledge base across projects or sessions; do not use for transient task state."
---

# NoBrainer Wiki

Build and use a small, trustworthy knowledge system only when information should
compound across tasks. This skill is explicitly inspired by Andrej Karpathy's
[LLM wiki concept](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
and is an independent portable adaptation, not an official Karpathy project.

Read [references/setup.md](references/setup.md) before creating or reconnecting a
wiki. One skill owns all wiki behavior so setup, query, capture and maintenance
cannot drift into competing wrappers.

## Select one mode

- `SETUP`: decide whether a wiki is justified, then create/connect/govern it.
- `GET`: read-only targeted retrieval. This is the default for a question.
- `ADD`: explicit ingestion or promotion of durable knowledge.
- `TIDY_AUDIT`: inspect trust, links, freshness and backlog without writing.
- `TIDY_APPLY`: apply only deterministic approved maintenance after an audit.

Do not combine modes invisibly. A `GET` that discovers a durable insight does
not authorize `ADD`; a tidy audit does not authorize semantic rewrites.

## Decide whether a wiki is justified

Prefer normal repository documentation when knowledge is local to one codebase
and already discoverable. A wiki is justified when durable decisions, sources,
research, explicit owner preferences or operational knowledge must be queried
across tasks/sessions and would otherwise be repeatedly reconstructed.

Do not store live execution state, leases, current hashes, transient blockers,
credentials or secrets. A spec defines a contract; a plan orders work; a wiki
preserves reusable knowledge. One fact has one canonical owner.

## Shared safety and knowledge contract

Resolve the wiki root from project instructions or the owner; never guess a
destination. Read its rules, index, classification boundary, relevant pages and
dirty/writer state before any operation.

Classify source and destination:

- `PUBLIC`: safe for intentional disclosure;
- `INTERNAL`: non-public operating knowledge without restricted personal data;
- `CONFIDENTIAL`: explicitly restricted, minimum necessary content;
- `SECRET`: credentials, keys, tokens, cookies, seed phrases or equivalents.

Never write `SECRET` material to source captures, pages, inboxes, logs, prompts
or Git history. Never promote private personalization into a public repository.
Respect copyright/access constraints and prefer concise synthesis plus provenance
over copying an external work.

Separate observed fact, attributed claim, inference, recommendation and
forecast. Every durable entry needs source, date, scope, classification and
certainty; dates are absolute. Preserve contradictions and stale-risk markers
rather than silently choosing a convenient version.

## `SETUP`

Run a read-only preflight:

- inspect existing instructions, wiki/map/rules, folder conventions and Git
  state;
- detect sources/pages/inbox/log, writers, sync and automation;
- classify the target and compare it with the minimal model in the setup
  reference;
- check every managed marker pair and overlapping dirty file.

Create only missing pieces and preserve established conventions. Use one source
of truth and one inbox per independent writer/machine. Do not initialize a
repository, pull/rebase, relocate, truncate or overwrite existing content just
because a template differs. Unknown classification, malformed markers,
conflicting writer or dirty overlapping scope is `BLOCKED`.

## `GET` — read-only retrieval

1. Rewrite the question into concepts, aliases, languages and freshness needs.
2. Use the index as a map, then `rg` exact/relevant terms. Follow only useful
   links and cited sources; do not load the whole vault by default.
3. Prefer curated pages and inspect raw sources when a claim, conflict or exact
   wording needs verification.
4. Enforce the requester's access boundary and redact unsafe paths/details.
5. Return `WIKI_FACT`, `INFERENCE`, `RECOMMENDATION` and `UNKNOWN` distinctly,
   with page/source provenance and freshness.

An absent lexical hit is not proof of absence. Search synonyms and related map
entries before declaring a gap. `GET` never repairs, updates freshness, captures
the answer, commits or pushes.

## `ADD` — durable capture or promotion

1. Confirm the owner requested persistence or that the project's explicit
   `LEARNING_WRITE_POLICY: AUTO_SCOPED` covers this durable event, then resolve
   one writer for the target files.
2. Read the complete allowed input; record provenance, date, classification and
   capture method. Keep verbatim source separate from synthesis.
3. Extract only reusable facts, decisions, definitions, evidence and procedures.
   Exclude transient status and unsupported conclusions.
4. Search existing pages by terms/aliases/languages before creating anything.
5. Prepare one scoped write set: allowed source capture, pages, index, log and
   exact inbox items to promote.
6. Apply minimal edits with citations and relative links.
7. Verify target content, index reachability, source links, classification and
   secret boundaries before marking inbox items processed.
8. Append one meaningful change-log entry only after successful promotion.

A mixed sensitive source requires an explicit sanitization list and destination
approval. Do not mass-rewrite, resolve owner decisions, commit, push or publish
unless those actions were separately authorized.

For video or recorded-session knowledge, preserve the complete available
timestamped transcript or caption stream as the raw source before synthesis.
Keep source capture separate from curated knowledge, cite timestamp ranges, and
use articles or summaries only as secondary cross-checks. If the complete
stream is unavailable, mark the capture partial rather than reconstructing
missing speech from surrounding context.

## `TIDY_AUDIT` and `TIDY_APPLY`

Audit exact dangling links, index drift, stale/time-sensitive claims, uncited
material claims, contradictions, duplicate candidates, orphans, inbox backlog,
classification leaks and secret/PII risk. Every finding needs file/line, evidence,
confidence and one recommended action. An orphan may be intentional; a fuzzy
title match is not permission to merge.

`TIDY_APPLY` may automatically perform only deterministic reversible work in the
approved scope: an exact link correction with a proven target, missing index
link, format normalization, or removal of a processed inbox item whose payload
is proven present and retention allows removal. Semantic merges, page/source
deletion, contradiction choice, reclassification and broad rewrites require an
owner decision. Re-read before each write, rerun checks after, and preserve a
scoped rollback.

## Durable personalization without hidden memory

Preserve only explicit reusable preferences, corrections, decisions and verified
working patterns. At task start retrieve only relevant pages; at close capture
only information likely to matter again. Do not infer a permanent trait from one
interaction. The owner must be able to inspect, correct and remove personalized
knowledge.

An external memory or retrieval service must earn its place with a representative
task set and a measured recall, context and latency target. Before adoption,
define project/account scope, source provenance, freshness and expiry, conflict
handling, correction/deletion/export, privacy, cost and a file-readable fallback.
Treat an injected profile or recalled item as context to verify, never as current
state or authority. Keep this policy in `nobrainer-wiki`; do not create another
permanent skill merely for a provider integration.

## Automation and close gate

Manual capture/promotion is the default. Schedule it only when measured volume
justifies a bounded trigger/input/output, one state owner, idempotence, retry
budget, conflict stop, secret filtering, dry run, logs and rollback. Scheduler,
credentials, commit/push and publishing remain owner gates.

Finish with mode, root/classification, exact pages/sources/inbox/log touched,
provenance, checks, contradictions, omitted sensitive material, uncertainty,
rollback and one next action. Never claim a clean or synchronized wiki when a
scan/source was partial or inaccessible.
