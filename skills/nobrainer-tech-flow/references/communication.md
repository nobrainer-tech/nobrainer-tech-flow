# Default communication

Use a plain technical style for operational messages: assignments, questions
between agents, plans, progress, findings, reports and handoffs. State the task
or result, the relevant evidence, and any condition or uncertainty that changes
the next action. Small messages stay small; no extra skill call or report form
is required. Stages use skill names internally; do not announce routine entry.

## Choose the recipient's language

- **Between agents:** use plain technical English by default. State the output
  artifact's requested language separately when it differs from the report.
  An explicit owner, recipient or task language requirement overrides this default.
- **To the user:** write directly in the requested language, or the conversation's
  language when none is specified. Use the same clarity principles with natural
  grammar. A Polish request normally receives a Polish answer even when workers
  coordinate in English. An English deliverable does not change the language of
  the surrounding user update unless requested.
- **Existing formats:** preserve the caller's schema, field names, enums and
  required output format. Apply the style to new prose only. Do not translate
  machine-readable values or literal source text to satisfy the English default.

The clarity default applies to ordinary replies too. Adapt warmth, detail and
structure to the audience. Requested marketing, fiction, dialogue or author
voice keeps its purpose and style; a technical product does not turn its ad
into a procedure. Use Writing for material prose work, not every short message.

## Keep one factual contract

Preserve names, commands, code, paths, identifiers, quotes, numeric values,
units, conditions, permissions, negation, uncertainty, source attribution and
evidence limits. Keep the original text beside an explanation when exact wording
matters. Never silently translate a quote or normalize an identifier.

Use one term per concept and direct verbs. Name the actor when known; preserve
an unknown actor instead of inventing one to force active voice. Put conditions
near the actions they restrict. Preserve the difference between necessary and
sufficient conditions, `and` and `or`, and `may`, `must` and `should`.

Keep sentences short when that improves understanding. Do not cut safety
conditions or acceptance criteria to hit a word limit. A report must distinguish
observed results, inferences, proposed actions and checks that did not run.
A confident worker summary is not an acceptance decision.

## Explain across languages without adding a pipeline

Use the same facts, requirements and evidence for agent messages and the user's
answer. Produce that answer directly in its target language. Do not require an
English draft, a translation provider, another model call or a second stored
copy of the execution state. If translation is actually requested or necessary,
compare its meaning with the source and preserve exact literals separately.

This policy governs visible messages and artifacts. It does not prescribe a
language for hidden reasoning or ask agents to reveal private deliberation.

## Example: one result, two recipients

Example worker report in English:

> Four local cases passed. Production behavior is unverified. Deployment is
> not authorized.

The same facts for a Polish user:

> Cztery lokalne przypadki przeszły testy. Działanie na produkcji pozostaje
> niesprawdzone. Nie ma zgody na wdrożenie.

These are sample messages, not test results. Keep the actual task's required
fields, evidence references and language overrides.

## Relationship to ASD-STE100

This is independently written guidance inspired by selected clarity principles
of [ASD-STE100](https://www.asd-ste100.org/about_STE.html). The standard concerns
controlled English technical writing; a Polish answer is not an ASD-STE100
conformance result. Writing's `TECHNICAL` mode adds procedure and explanation
profiles for English artifacts. Neither mode certifies the standard, ships its
dictionary or proves lower token costs, safer operation or better model results.
