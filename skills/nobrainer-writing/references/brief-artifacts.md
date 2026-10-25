# Brief artifacts

Use this reference only for the `BRIEF` mode of `nobrainer-writing`. Pick one
artifact and keep the output small enough that a busy reader can decide or act
without reconstructing the story.

## The common shape

```text
Title: <observable failure or user outcome>
Problem or goal: <one sentence>
Impact or value: <who is affected and why it matters>
Evidence or context: <reproduction, example, link, version, or UNKNOWN>
Acceptance or question: <how we know what to do or what answer is needed>
Next action: <one owner/action, if relevant>
```

Use only fields that change triage or implementation. Do not add a history
section, root-cause theory, solution design or generic closing unless the reader
needs it to act. Facts from the requester outrank polished wording; unknowns
stay visible.

Task-shaped artifacts (`BUG`, `ISSUE`, `USER_STORY` and `REQUEST`) always expose
two fields:

- `Description`: what is wrong, needed or intended.
- `Definition of Done (DoD)`: the observable closure condition and required proof.

Keep `Acceptance` for observable product behavior; do not hide the description or
DoD inside `Problem`, `Context`, `Done when` or a generic paragraph. `COMMENT`
is intentionally smaller and does not need task fields.

Number every acceptance criterion sequentially as `AC01`, `AC02`, `AC03` and so
on. Start at `AC01`, do not leave gaps, and do not use anonymous bullets or
checkboxes under `Acceptance`. DoD remains separate and may reference the AC IDs.

Before compressing, keep a private ledger of material facts: when it started,
what did or did not happen, exact statuses/errors, conditions, uncertainty and
the requested action. A concern is not proof of a failure, and a request to know
whether something is safe is not permission to invent the policy that decides
it. If the source does not define the desired behavior, write the open decision
or `UNKNOWN` instead of adding a warning, retry rule, UI state or implementation.

## COMMENT

Use for code review, issue updates, decisions, questions and status. Start with
the observation or decision, then the impact, evidence and one request.

```text
ENV: <Name> | URL: <route or N/A> | User: <role or redacted alias>
<Observation or decision>. <Why it matters or what changed>.
<Requested action or question>.
Evidence: <file, line, test, link or concrete example>.
```

Good code-review comment:

> ENV: TEST | URL: N/A | User: reviewer
>
> This returns `200` when the provider times out, so the caller treats a failed
> sync as success. Return the error or mark the result `UNKNOWN`, and add a
> timeout test; evidence: `sync_provider()` line 84 and the missing-timeout test.

Good status comment:

```text
ENV: QA | URL: https://demo.example.test/runs/42 | User: qa-operator
The timeout is now reported as a failed sync, and test `provider_timeout_marks_failure` passes. Next: review the PR.
```

Do not turn a comment into a mini-report. If there is no concrete observation,
write a direct question instead of praise followed by a vague suggestion.

## BUG

Title the observable failure, not a guessed cause.

````text
Title: [Bug] <what fails> when <condition>

Description: <one sentence describing the failure>

ENV:
- Name: <QA | DEV | TEST | PROD | PREPROD | BETA | UNKNOWN>
- URL: <exact non-secret route or page, or N/A when no URL applies>
- User: <role or redacted/synthetic alias, never a credential>
- Build/client: <release, client, OS, deployment or UNKNOWN, when useful>

Steps to reproduce:
1. <setup>
2. <action>
3. <result>

Current behavior: <what happens now>
Expected behavior: <what should happen>

API request (cURL), when applicable:
```bash
# Complete redacted curl command: method, URL, headers and body.
```

API response, when applicable:
```http
# Status, headers and body.
```

Database query (read-only), when applicable:
```sql
-- Read-only query.
```

Database result, when applicable:
```text
# Observed result; use its actual format when useful.
```

Evidence, for a UI screenshot or MP4 recording, when applicable: <attach file>
HAR, only when the page-load/request chain matters: <attach file or N/A>

Definition of Done (DoD): <observable regression proof and required checks>
````

`Description`, `ENV:`, `Steps to reproduce`, `Current behavior` and
`Expected behavior` are separate diagnostic fields. `ENV:` keeps the
environment name, exact URL and user used together; its optional `Build/client`
line preserves useful release or client context. Surface-proof sections remain separate
and appear only when applicable. Keep `URL` as `N/A` for a worker, CLI
or other flow with no page to open. Use `UNKNOWN` when the requester does not
know a value; do not replace a missing value with a guess.

Proof must match the affected surface:

- **API:** include a complete redacted `curl` request in one fenced code block
  and the response in a separate fenced `http` block. Keep method, URL, all
  captured headers, body, status and response body; redact sensitive values
  without changing the request's material shape.
- **Database:** include the read-only query and result in separate fenced blocks;
  use `sql` for the query and the result's actual format when useful.
- **UI:** put a screenshot or an MP4 recording in `Evidence`. If the failure
  depends on the page-load/request chain, attach a HAR too; keep the exact URL
  and reproduction steps in the report.

When a bug crosses more than one surface, include each applicable proof pair or
artifact. Do not collapse them into a generic `Evidence` paragraph. A URL or
prose description alone does not replace UI evidence. If required proof is not
supplied, return `INPUT_REQUIRED` and identify what is missing instead of drafting
a report with weaker substitute evidence.

Example:

````text
Title: [Bug] Sync reports success after a provider timeout

Description: A timeout leaves the sync marked as successful.

ENV:
- Name: TEST
- URL: N/A (worker-only reproduction)
- User: sync-test-user
- Build/client: release 1.3.0, local worker, macOS, staging provider

Steps to reproduce:
1. Start a sync against a provider that does not answer.
2. Wait for the request timeout.
3. Open the run history.

Current behavior: The UI shows “success” and no retry is scheduled.
Expected behavior: The run is marked failed or explicitly unknown.

Database query (read-only):
```sql
SELECT status, error FROM sync_runs WHERE id = 42;
```

Database result:
```text
status=success, error=timeout
```

Definition of Done (DoD): A regression test proves timeout is not reported as
success, and any retry behavior in scope is explicitly agreed and covered.
````

Leave the suspected root cause out unless it is verified. A useful bug report
lets another person reproduce the behavior without a meeting.

## ISSUE

Use for a feature, workflow improvement or change request. Keep `Description` to
one sentence, then use only the fields that help someone decide or build it.

```text
Title: [Feature] <user outcome>

Description: <what is hard, missing or unreliable today>
Who is affected: <specific user or workflow>
Desired outcome: <what the user can do or rely on afterwards>
Evidence: <example, frequency, user wording or link>

Acceptance:
- [ ] AC01: <observable pass/fail result>
- [ ] AC02: <observable edge case or failure result>
- [ ] AC03: <proof or compatibility condition, if relevant>

Definition of Done (DoD):
- [ ] <acceptance criteria pass in the affected surface>
- [ ] <required tests/checks and proof are attached or linked>
```

Example:

```text
Title: [Feature] Show why a sync was not retried

Description: A failed run only says “failed”, so it is unclear whether the next
run is safe to start.
Who is affected: Operators checking a failed scheduled sync.
Desired outcome: The run shows whether the failure is retryable and what to do.
Evidence: The current log contains the error, but the run history does not.

Acceptance:
- [ ] AC01: Retryable failures show “retryable” and the next retry time.
- [ ] AC02: Non-retryable failures show “manual action required”.
- [ ] AC03: The existing error detail remains available for diagnosis.

Definition of Done (DoD):
- [ ] The three acceptance criteria pass in the run-history UI.
- [ ] Automated coverage and the verification result are attached to the issue.
```

## USER_STORY

Use the user's goal, not a UI control or implementation task. The familiar
persona/goal/value sentence is useful, but the acceptance criteria decide what
counts as complete.

Derive acceptance from the stated goal. If the source gives only a concern or a
question, keep the criterion at that level and name the missing decision; do not
invent a product policy to make the story look complete. Use `Given/When/Then`
only when it improves verification or matches the team's existing language.

```text
Title: <short user outcome>

Description: <real problem, context or constraint behind the goal>

As a <specific user>, I want <goal> so that <value>.

Context: <real situation or constraint, if needed>
Acceptance:
- AC01: Given <context>, when <action>, then <observable result>.
- AC02: <another independent pass/fail result>

Definition of Done (DoD):
- [ ] <the acceptance criteria pass for the named user>
- [ ] <required tests/checks and proof are attached or linked>

Out of scope: <important boundary, if needed>
```

Example:

```text
Title: Explain failed scheduled syncs

Description: Operators currently see a failed run without knowing whether it is
safe to retry.

As an operator, I want to know whether a failed sync can be retried so that I
do not duplicate data or leave a delivery gap.

Acceptance:
- AC01: Given a timeout, when I open the run, then it is marked retryable and shows
  the next retry time.
- AC02: Given an authentication failure, when I open the run, then it is marked
  “manual action required”.

Definition of Done (DoD):
- [ ] Timeout and authentication scenarios pass in the run-history UI.
- [ ] The verification result is attached and the existing error detail remains
  available.
```

Do not force the `As a / I want / so that` form when the real request is a bug,
decision or operational task. A plain one-sentence outcome is better than a
ceremonial story that hides the need.

## REQUEST

Use for a short ask to a person or team:

```text
Description: <what needs to change or be produced, and why>
Request: <one concrete action>
Why: <one sentence of context>
Input or location: <file, link, example or attachment>
Needed by: <date only when real>
Definition of Done (DoD): <the exact output and proof the requester can verify>
```

Example:

```text
Description: The issue template does not tell reporters what proof is required
for API, database and UI failures.
Request: Update the public bug template with separate copyable proof fields.
Why: Reporters should be able to paste the evidence without reconstructing it.
Input or location: .github/ISSUE_TEMPLATE/bug_report.md
Needed by: 2026-09-02
Definition of Done (DoD): The template has separate request/response, query/result
and UI/HAR fields, and the repository checks confirm their order.
```

## Human-feel and compression gate

Keep:

- exact product, file, error and user terms;
- the writer's real stance, uncertainty and concrete example;
- one clear ask or next action;
- enough context to reproduce or decide.

Cut:

- greetings, praise and “I would like to kindly…” before the point;
- “improve the experience”, “make it robust” and similar goals without a
  measurable result;
- invented metrics, root causes, personas, urgency or agreement;
- repeated summaries, generic conclusions and implementation detail the reader
  did not request.

Never add mistakes, random slang or fake personal experience to make text seem
human. Naturalness comes from concrete source material and restrained editing.

Before returning, check:

```text
ACTIONABLE: PASS | FAIL
FACTS_TRACEABLE: PASS | FAIL
EXPECTED_OR_DESIRED_CLEAR: PASS | FAIL
ACCEPTANCE_OR_QUESTION_CLEAR: PASS | FAIL | NOT_APPLICABLE
NO_INVENTED_CAUSE_OR_CONTEXT: PASS | FAIL
LOW_VALUE_SENTENCES_REMOVED: PASS | FAIL
```

Return `INPUT_REQUIRED` if a failed check would require invention.

## Research basis

Checked 2026-09-02. These are design inputs, not copied platform templates:

- [GitHub issue and pull request templates](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/about-issue-and-pull-request-templates) supports reusable guidance and structured issue forms.
- [GitHub issue form configuration](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/configuring-issue-templates-for-your-repository) shows required fields and separate expected/actual evidence; the public form schema is platform-specific, so this skill remains Markdown-first.
- [GitLab Documentation Style Guide](https://docs.gitlab.com/development/documentation/styleguide/) emphasizes concise, direct, precise, searchable and conversational-but-brief writing.
- [Digital.gov: Writing for understanding](https://digital.gov/guides/plain-language/writing) recommends audience-specific language, short sections and active responsibility.
- [Atlassian: User stories](https://www.atlassian.com/agile/project-management/user-stories) connects persona, goal, value and acceptance criteria; its 3 Cs are Card, Conversation and Confirmation.
- [hannsxpeter/humanizer](https://github.com/hannsxpeter/humanizer/blob/main/SKILL.md) recommends preserving an authentic voice and making minimal edits when the input already sounds human; it explicitly rejects detector gaming.
