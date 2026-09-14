---
name: nobrainer-writing
description: "Use when the owner says nb-write, nb-brief, nobrainer-writing, nobrainer-style, or nobrainer-human-like, or asks for prose quality work on a user-facing artifact, such as drafting, rewriting, compressing, humanizing, editing, or reviewing it; maximize useful information per word without dropping facts, evidence, caveats, voice, or required action."
---

# NoBrainer Writing

Produce high-signal prose that helps a specific reader understand, decide or act.
Treat the Pareto idea as a direction: preserve nearly all decision-relevant value
while using far fewer words. It is not permission to remove evidence, conditions
or nuance merely to hit an arbitrary ratio.

The protocol, field names and examples in this public skill are written in
English. Match the requested output language; when English is requested, use
plain, idiomatic English rather than a literal translation.

This skill owns prose quality. `nobrainer-research` owns missing or current
external facts, `nobrainer-decide` owns consequential choices, and
`nobrainer-build` owns behavioral code changes and repository integration. A
small text-only edit can stay here. Do not invoke this skill for a one-sentence
answer that is already clear, specific and complete.

Use `BRIEF` for a short actionable artifact: a comment, bug report, feature
issue, user story, status update or one clear request. It is a mode of this
skill, not a new skill. Read [references/brief-artifacts.md](references/brief-artifacts.md)
for the matching shape and examples before drafting.

Read [references/research.md](references/research.md) only when changing this
protocol, auditing its rationale or comparing another writing method. Ordinary
writing runs should not spend context on the research record.

## Choose one mode

- `DRAFT`: create prose from an established brief and verified source material.
- `COMPRESS`: shorten existing prose while preserving its material meaning.
- `REWRITE`: improve clarity, structure, voice and naturalness without changing
  the factual contract.
- `REVIEW`: identify only material prose defects and propose the smallest useful
  correction; do not rewrite merely to express a preference.
- `BRIEF`: create or compress one short actionable artifact. Choose exactly one
  shape from the reference: `COMMENT`, `BUG`, `ISSUE`, `USER_STORY` or `REQUEST`.

If the user did not name a mode, infer the smallest one that satisfies the
request. A request to "humanize" means `REWRITE`, not detector evasion or the
injection of fake mistakes.

## Freeze the content contract

Before drafting, resolve internally:

```text
PURPOSE:
AUDIENCE:
USE_AFTER_READING:
ARTIFACT_AND_CHANNEL:
LANGUAGE_AND_TONE:
VOICE_SOURCE: supplied sample | project guide | inferred neutral | NONE
MUST_PRESERVE: facts | names | numbers | dates | links | quotations | terms |
               commands | conditions | uncertainty | caveats | requested action
SOURCE_STATUS: VERIFIED | PROVIDED | RESEARCH_REQUIRED | UNKNOWN
LENGTH_OR_FORMAT_CONSTRAINT:
```

Infer obvious fields from the request and current project. Ask one focused
question only when the answer changes factual meaning, audience fit, material
tone or safety. In a larger Ultra run, use the approved BUDDY brief and do not
re-open settled requirements.

For `BRIEF`, additionally freeze the observed problem or desired outcome, the
reader's next action, the smallest useful evidence, and the pass/fail condition
when one exists. If a missing fact would make the artifact misleading or
non-actionable, ask one precise question or return `INPUT_REQUIRED`; do not fill
the gap with a plausible cause, metric, user or environment.

Preserve every material input detail, including onset, negation, current status,
condition and uncertainty. Do not turn a fear, hypothesis or requested decision
into an observed fact or an invented acceptance rule. If the desired behavior is
not specified, keep the decision open or write `UNKNOWN` rather than choosing a
warning, retry policy, UI state or technical solution.

For `COMPRESS` and `REWRITE`, make a private meaning ledger before changing the
text. Track every material claim, number, name, date, URL, quotation,
attribution, identifier, command, negation, condition, uncertainty marker,
caveat and call to action. Never add a source, experience, opinion, metric or
detail that the input does not support. Route a material knowledge gap to
`nobrainer-research`; do not cover it with fluent prose.

## Write in six passes

1. **Outcome:** state the answer, decision, result or requested action in the
   first useful sentence. Keep background only when the reader needs it to
   interpret that outcome.
2. **Structure:** group each idea once. Put decision-relevant information first.
   Use headings, bullets or a table only when they make a real relationship
   easier to scan than short prose.
3. **Compression:** remove throat-clearing, repeated points, self-reference,
   empty transitions, generic summaries and decorative detail. Merge sentences
   only while the result remains easier to understand.
4. **Precision:** prefer concrete nouns and precise verbs. Name the actor when it
   clarifies responsibility. Use one term per concept and define necessary
   jargon for the actual audience.
5. **Voice:** match an authentic supplied sample or project guide when one
   exists. Otherwise use a direct, calm and natural neutral voice. Adapt tone to
   the reader's situation; technical, legal, error and safety text should not be
   made casual for entertainment.
6. **Integrity:** compare the final text with the meaning ledger and the user's
   requested action. Restore anything materially lost, and remove anything that
   cannot be traced to the input or a cited source.

Compress structure before swapping vocabulary. A shorter synonym cannot repair
a paragraph with no clear purpose.

For `BRIEF`, put the outcome or failure in the title/first sentence, keep one
problem or goal per artifact, and include only evidence that changes action or
triage. Use the fewest applicable fields. A comment is normally a few sentences;
an issue or story is normally one description, a short evidence/context block and
two to five testable criteria. Put long logs, transcripts and screenshots after
the concise core or link them; never hide them when they are needed for proof.
Return the finished artifact only unless the owner asks for an audit.

For task-shaped `BRIEF` artifacts (`BUG`, `ISSUE`, `USER_STORY` and `REQUEST`),
write `Description:` and `Definition of Done (DoD):` as explicit fields.
`Description` states what is wrong, needed or intended; `Acceptance` states
observable product behavior when applicable; `Definition of Done (DoD)` states
the closure condition and required proof. Do not hide either field inside a
generic paragraph or rename DoD to a vague `Done when`. `COMMENT` stays compact
and does not need task fields.

Number every acceptance criterion with a sequential two-digit ID: `AC01`, `AC02`,
`AC03` and so on. Start at `AC01`, do not leave gaps, and do not use anonymous
checkboxes under `Acceptance`; DoD remains a separate section and may reference
the acceptance IDs.

For both `BUG` and `COMMENT`, always provide one compact `ENV:` block with
`Name`, `URL` and `User`. `Name` is one of `QA`, `DEV`, `TEST`, `PROD`,
`PREPROD`, `BETA` or `UNKNOWN`; use `N/A` when a field genuinely does not
apply. `User` is a role or redacted/synthetic alias, never a credential.

For `BUG`, start with `Description`, then keep the diagnostic fields separate and
in this order: `ENV:`, `Steps to reproduce`, `Current behavior` and
`Expected behavior`; follow them with the applicable surface-proof sections:
`API request (cURL)`, `API response`, `Database query (read-only)`,
`Database result`, `Evidence` for a UI screenshot or MP4 recording and, only when
the page-load/request chain matters, `HAR`; finish with `Definition of Done (DoD)`.
Use `UNKNOWN` when a value is not known; never silently omit a required field or
invent its value.

For `ISSUE`, keep `Description` to one sentence, then use `Who is affected`,
`Desired outcome`, `Evidence`, `Acceptance` and `Definition of Done (DoD)` by
default. Add another field only when it changes triage or implementation.

Surface proof has a copyable artifact shape:

- **API:** put the complete redacted request in a fenced `bash` block as a
  `curl` command, including method, URL, all captured headers and body. Put the
  observed response in a separate fenced `http` block with status, all captured
  headers and body. Redact sensitive values without changing the request's
  material shape.
- **Database:** put the read-only query and its result in separate fenced code
  blocks, using `sql` for the query and the result's actual format when useful.
  Redact sensitive rows and values.
- **UI:** put a screenshot or MP4 recording under `Evidence`. If the failure
  depends on the page-load or request chain, attach a HAR as well; the exact URL
  and steps still belong in the report.

If several surfaces are involved, include each applicable proof pair or artifact.
Do not replace the API/DB proof pairs with generic prose. For a UI bug, `Evidence`
is the attachment field; a URL or prose description alone does not replace it.
If required proof is missing, return `INPUT_REQUIRED` and name the missing
artifact instead of drafting a weaker report.

## Anti-slop gate

Remove these patterns when they add no information:

- praise, greetings, apologies or announcements before the actual point;
- inflated significance, sales language, vague attribution and unsupported
  certainty;
- headings that repeat the next sentence, repetitive transitions, forced groups
  of three and multiple labels that say the same thing;
- fake candor, invented objections, rejected options no reader proposed,
  dramatic fragments and generic optimistic endings;
- abstract metaphors, buzzwords or modifiers standing in for a concrete fact;
- formatting used as decoration, including excessive bold text, emoji and a
  list where one sentence is clearer;
- comments or documentation that restate visible code instead of explaining a
  non-obvious reason, constraint, risk or consequence.

These are contextual signals, not a forbidden-word list. Keep a transition,
technical term, passive construction, long sentence, repeated phrase or unusual
punctuation when it is accurate, natural for the writer and useful to the
reader. Professional grammar is not an AI tell.

Never simulate humanity with typos, missing punctuation, fabricated anecdotes,
random slang, artificial sentence fragments or opinions the author did not
express. Do not optimize for an AI detector or claim that prose is human-written.

## Match the artifact

- **Reply, comment or status:** outcome first, then only decisive evidence,
  blocker and next action.
- **Email or request:** purpose, essential context, one clear ask and timing when
  material.
- **README or instructions:** purpose, prerequisites, shortest successful path,
  verification and only likely failure recovery.
- **Pull request:** lead with why the change is needed, then describe only the net
  change against the actual PR base and the verification that helps review it.
  Remove abandoned approaches, local absolute paths and routine checks already
  evident from required CI; preserve still-relevant links, images and caveats.
- **Report or decision note:** answer, verified facts, inference or trade-off,
  decision and next action. Keep fact and inference visibly distinct.
- **Long-form content:** thesis, evidence and implications in a coherent arc.
  Concision removes repetition; it does not flatten a real argument into notes.
- **Code comment:** explain why, invariant, risk or surprising consequence.
  Delete comments that merely translate the code into English.
- **Marketing or social copy:** audience problem, concrete value or proof and one
  honest action. Do not manufacture urgency, authority or transformation.

For a natural human feel, preserve the author's actual nouns, stance, uncertainty
and occasional first-person phrasing when supplied. Prefer a specific example
over a polished generalization. Do not manufacture typos, slang, anecdotes,
opinions, emotional claims or "human" irregularity; do not optimize for an AI
detector or claim that a person wrote the result.

## Quality gate

Before returning the text, require:

```text
PURPOSE_CLEAR: PASS | FAIL
ANSWER_OR_ACTION_FRONT_LOADED: PASS | NOT_APPLICABLE | FAIL
MEANING_PRESERVED: PASS | NOT_APPLICABLE | FAIL
CLAIMS_TRACEABLE: PASS | NOT_APPLICABLE | FAIL
CAVEATS_AND_CONDITIONS_PRESERVED: PASS | NOT_APPLICABLE | FAIL
VOICE_AND_AUDIENCE_FIT: PASS | FAIL
VALUE_DENSITY: PASS | FAIL
SCAN_AND_ACCESSIBILITY: PASS | NOT_APPLICABLE | FAIL
```

`VALUE_DENSITY` passes when every sentence adds a distinct fact, implication,
instruction, decision, transition or intentional voice effect. Ask of each
sentence: if it disappears, does meaning, evidence, tone or action materially
change? If not, cut it.

A lower word count is diagnostic, not acceptance. Do not over-compress a short
source, remove a necessary example, collapse separate conditions or hide risk.
When accessibility matters, preserve descriptive headings, meaningful link text,
expanded acronyms and enough context to understand the text out of layout.

## Return the result

Return only the finished prose by default. Do not surround a two-line answer
with a process report. When the owner asks for an audit, comparison or measured
compression of the prose itself, add a compact block after the result:

```text
MODE:
WORDS: before -> after | NOT_MEASURED
MATERIAL_CHANGES:
PRESERVED_CONTRACT:
UNVERIFIED_OR_INPUT_REQUIRED:
```

Return `INPUT_REQUIRED` instead of drafting when a missing fact, source, voice
sample or constraint would force invention or materially change the result.
