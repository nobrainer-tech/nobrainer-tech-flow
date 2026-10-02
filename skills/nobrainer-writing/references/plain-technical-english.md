# Plain technical English

Use Writing's `TECHNICAL` mode for English specifications, instructions,
runbooks and technical explanations. Infer the profile from the artifact:
`PROCEDURE` for actions, `EXPLANATION` for understanding. A mixed document can
use both. Keep ordinary replies, marketing and other languages in their
requested style; do not translate or switch modes merely because a topic is technical.

This is an independent writing adaptation informed by
[ASD-STE100](https://www.asd-ste100.org/about_STE.html) and
[Karpathy's suggestion](https://x.com/karpathy/status/2105819303471976479).
It does not reproduce the standard or dictionary, check all its rules, or
claim official approval, certification or full conformance. A formal STE
request requires the current official standard, domain terminology and
qualified review; this mode alone cannot establish compliance.

## Preserve meaning before simplifying

Use Writing's meaning ledger. Freeze commands, code, identifiers, quotations,
links, numbers, units, scope, sequence, permission strength, negation,
uncertainty and safety conditions. Keep `may`, `must` and `should` distinct.
Do not split a condition away from the action it restricts or change `and` to `or`.
Do not invent the actor, test result or missing step to make a sentence cleaner.
Mandatory quoted wording remains verbatim; simplify its surrounding explanation.

Choose one name per concept from the project's terminology. Define an unfamiliar
term once if the reader needs it. Keep precise domain terms and technical verbs;
do not replace them with a common but less accurate word. There is no automatic
forbidden-word list, synonym substitution or ban on words ending in `-ing`.

## PROCEDURE: make the next action clear

- Put prerequisites and safety conditions before the action they govern.
- Give each step one action. Use a direct command when the source is an
  instruction; preserve optional actions and permissions as optional.
- Prefer short sentences, with a 20-word target for newly written prose.
  Split for comprehension, never by cutting a command, condition or caveat.
- Keep the original order when it changes behavior. State the expected result
  only when supported. Keep recovery instructions with their trigger.

## EXPLANATION: make the mechanism clear

- State the result or concept, then explain the cause, limitation or consequence.
- Prefer short sentences, with a 25-word target and one topic per paragraph.
- Use active voice when the actor is known. Keep passive voice when the actor
  is unknown or naming one would invent a fact.
- Use a small example or diagram only when it resolves a concrete ambiguity.
  Do not produce a diagram, interactive page or video for every explanation.

Sentence targets are editing aids, not pass/fail limits for this adaptation.
Code, exact quotations and necessary technical terms can exceed them. Do not
claim official STE compliance from word counts or a few regex checks.

## Verify the rewrite

Compare every ledger item with the result. Check especially combined conditions,
exceptions, optional versus mandatory actions, unknown actors and unverified
outcomes. A shorter text fails if its meaning changes. Restore necessary detail
before returning it; ask only when the source itself is materially ambiguous.

Return the finished text by default. If an audit is requested, state the profile,
meaning-check result and any unresolved source ambiguity. Report words or tokens
only if measured. A word-count reduction does not prove cheaper tasks, better
models, safer operation or official conformance.

## Source boundaries

Reviewed 2026-10-02: [official FAQ](https://www.asd-ste100.org/STE_faq.html)
distinguishes procedures from descriptions and permits passive descriptions
when the actor is unknown. The [official tools page](https://www.asd-ste100.org/STEsoftware.html)
does not make a language checker a substitute for the standard. Karpathy
recommends an existing method; he did not invent it or supply a Flow benchmark.
