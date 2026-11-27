# NoBrainer Wiki setup reference

Adapt this reference to the target. Existing conventions win when they preserve
the same safety and information boundaries.

New wikis and new pages use the
[Open Knowledge Format (OKF) v0.3](https://github.com/open-knowledge-format/open-knowledge-format/blob/main/SPEC.md)
(version 0.3, 2026-10-23): Markdown files with YAML frontmatter, standard
Markdown links, and `index.md`/`log.md` files in a fixed form. A wiki is then an
OKF bundle that people, agents and other tools read without this skill.

## Minimal layout

```text
WIKI_ROOT/
  WIKI.md             durable rules and confidentiality boundaries
  index.md            map to curated knowledge (OKF §8); root carries okf_version
  log.md              dated meaningful changes, newest date first (OKF §9)
  sources/            raw captures with provenance and classification
  pages/              curated, linked, cited knowledge
  _inbox/WRITER.md    append-only candidates owned by one writer
```

Do not create empty layers that have no present use. A project-local wiki may
live under its existing docs structure.

`WIKI.md`, `README.md`, `AGENTS.md` and inbox files carry no `type`, so OKF
consumers skip them as non-concepts. Give every curated page and every Markdown
source capture frontmatter with a `type`; keep raw non-Markdown captures (JSON,
CSV, images) unchanged as assets.

## Existing wikis

An existing wiki keeps its own layout, link style, page format, index and log.
Do not mass-migrate it. Its `WIKI.md` rules decide the page format for new pages
there; when they define none, add OKF frontmatter to new pages and keep the
wiki's link style. Never add `okf_version` to a root `index.md` whose wiki does
not meet the conformance rule below. Conversion to an OKF bundle is the separate
export step at the end of this reference.

## Curated page contract (OKF v0.3)

```markdown
---
type: Decision
title: Human title
description: One durable statement a future reader can act on.
tags: [area, topic]
sources:
  - id: vendor-docs
    resource: https://example.com/docs/page
    title: Vendor documentation page
    last_modified: "2026-11-01"
  - id: meeting-notes
    resource: ../sources/2026-11-20-planning-meeting.md
    title: Planning meeting capture
generated: { by: "wiki-agent/1.4", at: "2026-11-27T10:00:00Z" }
verified:
  - { by: "human:owner", at: "2026-11-27T12:00:00Z" }
status: stable
x-nb-classification: INTERNAL
---

# Facts

- <observed or source-backed claim>.[^vendor-docs]

# Decisions and implications

- <decision, owner, date and scope>.[^meeting-notes]

# Contradictions / stale risk

- <conflict or freshness warning, or NONE>

# Related

- [Another page](/pages/area/another-page.md) - why it matters here

[^vendor-docs]: Vendor documentation page
[^meeting-notes]: Planning meeting capture
```

Use absolute dates. Mark observed fact, inference, recommendation and forecast
separately. Do not resolve conflicting sources by silently deleting one.

### Frontmatter fields

- `type` (required): the kind of page, for example `Decision`, `Reference`,
  `Playbook`, `Lesson`, `Source`. Reuse the types the wiki already uses; OKF has
  no central list.
- `title` and `description`: the display name and one sentence; index entries
  reuse the description.
- `tags`: a YAML list of short strings.
- `sources`: one entry per material the page derives from. `resource` is
  required: an absolute URL, a path in the wiki, or a scope description such as
  `all support tickets from 2026-10`. Give an `id` to every cited source. Add
  `author` or `last_modified` only when known, and `usage_count` only with the
  `usage_window: { from, to }` it was counted in.
- Per-claim citation: a footnote whose label is the source `id`, as in
  `claim.[^vendor-docs]`. Consumers join on the label, not on the footnote text.
  Do not add a separate citation list.
- `generated`: `by` (required) is the actor that wrote the current content; `at`
  is the time of the last meaningful content change. Formatting, whitespace or a
  link repair does not change `at`.
- `verified`: a list of `{ by, at }` events (both keys required), one per real
  check of the content against its sources or its `resource`. Write one only
  after the check happened. Keep older events as history.
- Timestamps are RFC 3339 strings: a date-time such as `"2026-11-27T10:00:00Z"`
  (preferred for `generated.at` and `verified[].at`) or a date such as
  `"2026-11-27"`.
- `status`: `draft` (incomplete or unreviewed), `stable` (the default) or
  `deprecated`. To retire or move a page, keep the file as `deprecated` and do
  not delete it; set `superseded_by` to the replacement path only when one
  exists.
- `stale_after`: only when a real review date is known, such as a contract end,
  an announced price change or a version end of life. Omit it otherwise; never
  invent one.
- `x-nb-classification`: `PUBLIC`, `INTERNAL` or `CONFIDENTIAL` on every page.
  `SECRET` material is never written, so it has no value here.

Actors (`generated.by`, `verified[].by`, `sources[].author`):

- `human:<id>` for a person, `team:<id>` for a group, `process:<id>` for an
  automated job, `<agent>/<version>` for an agent or tool.
- An agent records itself as `<agent>/<version>` in `generated`. It writes a
  `human:` event in `verified` only when that person confirmed the current
  content, and then uses the time of that confirmation.
- A `verified` event is current when `generated` is absent or its `at` is not
  earlier than `generated.at`; only current events count. After an agent
  rewrites reviewed content, the page is no longer
  human-reviewed until the person confirms it again.

Frontmatter syntax: the file starts with a line that is exactly `---`, the block
ends at the next such line, it parses as one YAML 1.2 (core schema) mapping
without duplicate keys or custom tags, and values that look like numbers,
booleans or dates are quoted. When editing an existing page, keep keys you do not know and
do not re-serialize values you did not change.

From the earlier inline contract: `CLASSIFICATION:` becomes
`x-nb-classification`; a `LAST_VERIFIED:` date becomes a `verified` event only
when the page or its log records who checked it, otherwise it stays as a body
note and no event is written (`UNKNOWN` means no event); `(source: X)` becomes a
`sources` entry with a footnote.

### Links

Write links as standard Markdown inline links. The target is relative
to the current file (`../data/orders.md`) or starts at the wiki root
(`/pages/data/orders.md`); OKF consumers resolve both. Percent-encode spaces and
other reserved characters (`my%20page.md`); paths are case-sensitive. OKF does not
treat `[[wikilinks]]` as links, so use them only in an existing wiki whose
convention already uses them. A link to a page not written yet is valid in OKF;
`TIDY_AUDIT` still reports it.

## Index and log files

Each directory may have an `index.md`. Only the root `index.md` may have
frontmatter:

```markdown
---
okf_version: "0.3"
title: Example team knowledge
description: Decisions, playbooks and sources for the example team; use it for operating questions.
---

# Decisions

* [Release cadence](/pages/release-cadence.md) - Releases ship weekly after a green suite.

# Playbooks

* [Data playbooks](/pages/playbooks/) - Incident and recovery procedures.
```

Group entries under `#` headings as `* [Title](/path/to/page.md) - description`,
reusing the linked page's `description` when it has one; a directory entry gets
a short written summary. When regenerating an index, keep the existing root
frontmatter.

`log.md` has no frontmatter. Group entries under `## YYYY-MM-DD` headings, newest
date first. Add today's entry under today's heading (create it at the top when
missing); never rewrite earlier entries.

```markdown
# Wiki update log

## 2026-11-27
* **Creation**: Added [Release cadence](/pages/release-cadence.md).

## 2026-11-20
* **Update**: Recorded the new review owner in [Playbooks](/pages/playbooks/).
```

`index.md` and `log.md` are reserved names at every level; never use them for a
page.

Conformance: every frontmatter block in a `.md` file of the wiki parses as a
YAML mapping, and every `index.md` and `log.md` follows the forms above. A `.md`
file without frontmatter or `type` is not a page for OKF and does not break
conformance. Declare `okf_version` only when both rules hold.

## Managed instruction block

Insert a project-specific block with a complete marker pair. Keep it concise so
instructions do not become a copy of the wiki protocol.

```markdown
<!-- NB-WIKI:START -->
## NoBrainer Wiki

Knowledge root: `WIKI_ROOT`. Rules: `WIKI_ROOT/WIKI.md`.
- At session start, read `WIKI_ROOT/index.md`, then search only relevant pages.
- Capture only durable facts in the current writer's inbox; never secrets.
- New pages follow the page format in `WIKI.md` (OKF v0.3 frontmatter and
  Markdown links unless it sets another).
- Use `nobrainer-wiki` mode `GET` for queries, `ADD` for explicit persistence,
  and `TIDY_AUDIT` before any maintenance write.
- Runtime state, leases and transient blockers stay in their canonical ledgers.
<!-- NB-WIKI:END -->
```

Before replacement, require exactly one START and one END in the correct order.
Zero markers means append at the repository's conventional location. Any other
count/order is a stop for manual repair. Verify a byte-level before/after diff
outside the managed block.

## Export to OKF

Converting an existing wiki into an OKF bundle is a separate task with its own
owner approval, never a side effect of `ADD` or `TIDY_APPLY`:

1. Write the bundle to a separate directory or branch; leave the source wiki
   unchanged.
2. Include only pages whose classification the destination allows; drop
   inbox files, raw private captures and anything the owner excludes.
3. Map inline metadata to frontmatter, wikilinks to Markdown links, and the
   index and log to the forms above; add `type` to every exported page.
4. Check that every frontmatter parses, every page has `type` and every
   in-bundle link resolves; report broken links instead of guessing targets.

## Setup report

```text
WIKI_DECISION: REUSE | CREATE | REPAIR | NOT_JUSTIFIED | BLOCKED
ROOT: <resolved path/reference>
CLASSIFICATION: <level>
PAGE_FORMAT: OKF_0.3 | EXISTING_CONVENTION
FILES_REUSED: <list>
FILES_CREATED: <list>
INSTRUCTIONS_UPDATED: <list>
AUTOMATION: NOT_CONFIGURED | PROPOSED | VERIFIED
CHECKS: <commands/readbacks>
UNCERTAINTY: <items or NONE>
ROLLBACK: <exact procedure and readback>
NEXT_ACTION: <one action>
```
