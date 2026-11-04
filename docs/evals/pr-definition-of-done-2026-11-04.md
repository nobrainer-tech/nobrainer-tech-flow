# PR Definition of Done scenarios — 2026-11-04

Verify that a reader who has Flow's review and writing skills reports a pull request's
readiness by gate, instead of accepting "CI is green", and writes the PR texts in the
agreed formats, while the existing artifact shapes keep their contracts.

Changed skills under test: `nobrainer-review` (`SKILL.md`,
`references/pr-definition-of-done.md`), `nobrainer-writing` (`SKILL.md`,
`references/brief-artifacts.md`). One-line field or routing additions, read for
coherence and not behavior-tested here: `nobrainer-build` (`SKILL.md`),
`nobrainer-spec-driven-development` (`references/spec-template.md`), `nobrainer-team`
(`references/team-plan.md`), `nobrainer-sessions` (`references/protocol.md`),
`nobrainer-tech-flow` (`SKILL.md` routing line, `references/routing.md`, `VERSION`).

## Method

The scenarios and a deterministic scorer were written and hashed before any skill
changed: [pressure](artifacts/pr-definition-of-done/pressure.md),
[holdout](artifacts/pr-definition-of-done/holdout.md) and
[scorer](artifacts/pr-definition-of-done/score.py). The
[regression cases](artifacts/pr-definition-of-done/regression.md) and their
[scorer](artifacts/pr-definition-of-done/score_regression.py) came later and are
described below, and [discovery](artifacts/pr-definition-of-done/discovery.py) has its own
section. Each run was one fresh reader on a
mid-tier model, loading only the two skills and what they link. The baseline read
frozen copies of those skills from `origin/main` at `f7f8972`; the candidate read the
working tree. MAIN did not edit any answer.

The pressure case is an owner asking whether a PR is ready because CI is green, while the
merge of the target exists only locally, a commit landed after the run, one test passed
only on retry, one was skipped, one only navigates, and the CI report and the tracker are
inaccessible. The holdout has six requests that the candidate was not tuned against: a
docs-only PR, a tracker the reader cannot open, a prospective task, a plain code review
comment, a bug with an unverified cause and a one-line review reply.

## Scorer correction

The scorer as first frozen left out `re.M`, so `^` matched only at the start of a section:
P13 could never pass, H06 failed on a correct answer and H11 checked nothing. The copy
stored here adds that one flag. Both scores are below. Nothing else in the scorer or
scenarios changed, and the holdout answer was not rewritten.

## Results

| Run | First-frozen scorer | Corrected scorer |
|---|---|---|
| Baseline pressure, `origin/main` | 6/16 | 6/16 |
| Candidate pressure, first run | 14/16 | 15/16 |
| Candidate pressure, after the status format fix | 14/16 | 15/16 |
| Candidate holdout | 11/12 | 12/12 |
| Pressure, after the review fixes | 14/16 | 15/16 |
| Holdout, after the review fixes | 10/12 | 11/12 |
| Regression, after the review fixes | not applicable | 9/9 |
| Pressure, after the discovery edits | 15/16 | 16/16 |
| Holdout, after the discovery edits | 11/12 | 12/12 |
| Regression, after the discovery edits | not applicable | 8/9 |
| **Pressure, shipped text** | 14/16 | 15/16 |
| **Holdout, shipped text** | 10/12 | 11/12 |
| **Regression, shipped text** | not applicable | 8/9 |

The baseline already refused to call the PR ready and named the stale run, the unpushed
merge, the retry and the unproven AC03. It failed on the shape: no gate statuses, no single verdict, a status
comment longer than the format, SHAs in the description. The behavior gap is in the
report and the texts, not in the judgment.

The first candidate run failed P15: the PR status format had no not-ready variant, so the
reader wrote four sentences. The fix adds that one variant to `DELIVERY_COMMENT`, and the
rerun passed P15.

An independent closeout review then found four defects the scenarios had missed, all
from carrying the source text over too literally:

1. Gate 8 asked for post-merge records while the pre-merge report covers gates 1 to 8, so
   a PR with a readable tracker task could never reach `Ready`. Those checks moved to
   Gate 9.
2. The PR template's readiness block contradicted the `PR` format and named no reviewed
   head. The format now has an exception, and the template has a `Reviewed head` line.
3. The project profile had no home and a read-only reviewer could not fill it. It now
   lives in `REVIEW.md` or the nearest instructions, and an absent key is derived or
   reported `UNKNOWN`.
4. The `TASK` DoD put the completion comment on the parent too, against the parent comment
   format. The item is now split.

The regression cases were written after that review and before their first run: a tracked
PR that must reach `Ready` before the merge, a repository with no profile, and a parent
comment. They are not a sealed holdout, because they target known defects.

The review-fix runs predate the discovery edits to the skill descriptions and routing, so
all three scenarios ran again. The full test suite then rejected the cross-skill links:
the installer documents which skills depend on which, and a partial install must have no
dead link. Those links became plain skill names, and the scenarios ran once more on that
text, with the pressure reader told to start from `nobrainer-review` alone. It reached the
gates and the Writing formats without the links. The three bold rows are the results for
what ships.

Every miss in the bold rows is a scorer false positive, left as frozen and still counted.
The same kind of miss occurs in the baseline. P03, a case-insensitive check for `PASS` or
`FAIL` as a status, was tripped by prose: "unit tests pass 142/142" in a candidate line whose
status was `UNKNOWN`, and "not a pass" in the baseline. H04 was tripped by "(missing access
is not N/A)" in a line whose status was the correct `UNKNOWN`. R03 was tripped by "not done"
in a correct `Ready` verdict. P06 failed the baseline even though it flagged AC03 as
`NOT_PROVEN`, because the pattern did not list that wording. On that same reading the
candidate is 16/16, 12/12 and 9/9, and the baseline is 8/16.

PRESSURE_RESULT: 15/16 (baseline 6/16; each has scorer false positives, see above)
HOLDOUT_RESULT: 11/12 (the one miss is a scorer false positive; `COMMENT` and `BUG` kept their contracts)
REGRESSION_RESULT: 8/9 (the one miss is a scorer false positive)

## Discovery in a real client

Someone must be able to ask for a DoD and reach the gates. The script runs Claude Code
`-p` on the mid-tier model, with only this plugin, in an empty directory, and records every
skill the client loads. The baseline was `origin/main` at `f7f8972`; the candidate was the
working tree after the description and routing changes. The script's requests were
frozen before either run. Its turn limit and skill counting were corrected after a smoke
test on one request, before the first recorded run.

| Run | Should load Review | Must not load Review |
|---|---|---|
| Baseline | 0/7 | 5/5 |
| Candidate | 6/7 | 5/5 |

The 0/7 was checked before it was trusted: in one rerun the same client went straight to
`gh`, and an explicit "use the nobrainer-review skill" loaded it, so the measure can see a
load. Raw streams were not stored, so an empty row in the table cannot be told apart from
a client turn that failed for another reason. The candidate's miss is the Polish "Czy ten PR jest gotowy do merge?"; the other two
Polish requests hit. `NON_TRIGGER_EXACT_SKILL` stayed 0/5 in both runs: for the five
non-trigger requests the client did not load Writing or RCA on its own. This change does
not address that, and it is not what this measure is for.

DISCOVERY_RESULT: 6/7 hits, 5/5 clean (baseline 0/7, 5/5)

## Limits

- One reader per run, so this shows a shape change, not a rate.
- The scorer checks patterns. It cannot judge whether a gate's status is the right call.
  Some verdict lines did not match the number of `GAP` lines above them, and no check
  catches that. The four review findings show what this scorer cannot see.
- The candidate read the uncommitted working tree that became this change. This record
  changed after the shipped-text runs; no skill text did. Discovery ran before the links
  became names, but the descriptions and routing rows it depends on did not change.
- CLIENT_RUNTIME: PARTIAL. Discovery ran once per request in Claude Code only. Codex,
  the other clients and the MCP server were not exercised. The MCP guidance card can only
  be added after the tag, because cards quote the pinned release.
