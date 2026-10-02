# Research basis for high-signal writing

Research question: which current writing methods best reduce generic AI prose
and word count without losing meaning, evidence, audience fit or safety?

Decision supported: define one portable writing skill for messages, comments,
documentation, reports and longer content. Every source was accessed on
2026-08-28. Repository sources are pinned below; publisher documentation remains
a live URL, so no immutable snapshot or unshown publication date is claimed.

## Ten approaches reviewed

| # | Source and provenance | Useful approach | Limitation carried into the skill |
|---|---|---|---|
| 1 | [blader/humanizer 2.11.2](https://github.com/blader/humanizer/blob/38b88903a5080c72a8c0472e79dcc9ffbf07938b/SKILL.md); commit `38b8890` dated 2026-08-19, Git blob `c9c2242`, accessed 2026-08-28 | Preserve every claim, never invent facts, and let a real writing sample override generic style rules. | A long pattern catalogue is useful for audit but too heavy for every ordinary draft; punctuation and vocabulary are contextual, not proof of authorship. |
| 2 | [hannsxpeter/humanizer 1.2.1](https://github.com/hannsxpeter/humanizer/blob/c35d49f5d57ed6e2222c23fab22b30e34ffa79e5/SKILL.md); commit `c35d49f` dated 2026-08-16, Git blob `b5bad0d`, accessed 2026-08-28 | Treat voice matching and conservative editing as the goal, with explicit false-positive restraint. | Do not frame quality work as beating detectors or disguising authorship. |
| 3 | [Concise Output 1.2.0](https://github.com/jagreehal/jagreehal-claude-skills/blob/810e8d69ef23476f15f3f5ee1044b9552a9fdba0/skills/concise-output/SKILL.md); commit `810e8d6` dated 2026-07-29, Git blob `f0e528f`, accessed 2026-08-28 | Put the point first, delete filler and test whether each sentence earns its place. | Extreme brevity needs exceptions for teaching, trade-offs, safety and long-form argument. |
| 4 | [Microsoft: simple words and concise sentences](https://learn.microsoft.com/en-us/style-guide/word-choice/use-simple-words-concise-sentences); live publisher page accessed 2026-08-28 | Use precise simple words, remove words without substance and keep text scannable. | Simple must not become abrupt, vague or less accurate. |
| 5 | [Google developer documentation: voice and tone](https://developers.google.com/style/tone); live publisher page accessed 2026-08-28 | Write clearly, directly and naturally for a global audience; avoid buzzwords, canned phrases and unnecessary entertainment. | Conversational writing is not a transcript of speech and should not import slang or cultural references by default. |
| 6 | [Digital.gov plain-language guide](https://digital.gov/guides/plain-language/writing) and [18F plain language](https://guides.18f.org/content-guide/our-approach/plain-language/); both live publisher pages accessed 2026-08-28 | Start from the specific audience, use active responsibility where useful, short sections and familiar literal terms. | Plain language is audience-relative; specialist readers may need precise technical terms. |
| 7 | [Mailchimp content style guide](https://styleguide.mailchimp.com/grammar-and-mechanics/); live publisher page accessed 2026-08-28 | Build an information hierarchy, lead with the main point, stay specific and adapt tone to the reader and channel. | Friendly voice never outranks clarity, truth or the reader's emotional context. |
| 8 | [GitLab documentation style guide](https://docs.gitlab.com/development/documentation/styleguide/); live publisher page accessed 2026-08-28 | Make documentation concise, direct, precise, task-oriented and easy to search or scan; avoid sales claims and self-reference. | Documentation structure differs from email, social and long-form prose, so one fixed template would overfit. |
| 9 | [IBM Carbon writing style](https://carbondesignsystem.com/guidelines/content/writing-style/); live publisher page accessed 2026-08-28 | Trim to as few words as possible without becoming terse, and vary tone with the user's journey and task. | Word count alone cannot judge usefulness; context and comprehension remain the acceptance test. |
| 10 | [W3C writing for web accessibility](https://www.w3.org/WAI/tips/writing/); live publisher page accessed 2026-08-28 | Use clear sentences, meaningful headings and links, expanded acronyms and structure that remains understandable to assistive technology. | Compression must not remove orientation or make meaning depend on visual layout. |

## Facts, inference and decision

`FACT`: Across maintained corporate, government and accessibility guidance, the
recurring practices are audience-first purpose, front-loaded information,
simple precise language, useful structure, active responsibility, consistent
terms and removal of unsupported or repetitive prose.

`FACT`: The reviewed humanizer skills add two valuable safeguards: preserve a
meaning ledger and use an authentic voice sample instead of injecting generic
"human" quirks.

`INFERENCE`: AI slop is primarily a relevance, structure and evidence problem.
A word blacklist can help detect clusters, but it cannot establish quality and
creates false positives when applied as a hard ban.

`INFERENCE`: A literal 80% reduction is unsafe as a universal acceptance rule.
The transferable Pareto principle is to protect decision-relevant value and
remove low-value ceremony until every remaining sentence earns its place.

`DECISION`: Use one lightweight protocol with a frozen content contract, a
structure-first compression pass, an integrity checksum, artifact-specific
shapes and final-only output. Keep detailed research outside `SKILL.md` so an
ordinary invocation pays only for operational guidance.

## Rejected patterns

- deliberate grammar errors, fake anecdotes or random slang as evidence of
  humanity;
- optimizing for an AI detector or claiming human authorship;
- hard bans on punctuation, sentence length or individual vocabulary;
- a mandatory before/after report that makes every short answer longer;
- compression ratios that override facts, caveats, accessibility or action.


## Plain technical English adaptation — 2026-10-02

[Karpathy's original post](https://x.com/karpathy/status/2105819303471976479)
recommends the existing ASD-STE100 method for readable explanations, and choosing
diagrams or interactive artifacts when they aid understanding. It is a writing
suggestion, not a measured performance result for Flow.

The [official overview](https://www.asd-ste100.org/about_STE.html) describes a
controlled language with rules and a dictionary. The
[official FAQ](https://www.asd-ste100.org/STE_faq.html) distinguishes procedural
and descriptive text, including passive descriptions when the actor is unknown.
Writing adopts independently phrased clarity guidance in
[plain technical English](plain-technical-english.md), with a meaning ledger and
explicit limits. It does not ship the dictionary, certify conformance or infer
token/cost savings. The existing contextual anti-slop rules remain in force for
other modes and languages.


### Default communication refinement — 2026-10-02

Owner-requested policy: use plain technical English for operational exchanges
between agents, while user-facing replies keep the requested language. This is
a design default, not evidence that English improves every model or reduces
tokens. The factual contract is shared; a second translation call is not required.
English technical artifacts select TECHNICAL when no mode is requested. Other
languages use natural plain language with the same meaning-preservation checks.
Caller schemas, quoted text and explicit language/voice requests remain binding.
