# Pull request Definition of Done

A project-agnostic Definition of Done (DoD) for any pull request (PR): code, tests,
tooling or docs. Each repository keeps its own project profile. Everything else stays
the same in every repository.

Review reads this file and reports the gates. It does not sync, fix or merge: fixes
go through `nobrainer-build`, and the merge stays an owner gate. The texts these gates
ask for (PR description, task, commit and comments) have their formats in the
`nobrainer-writing` `BRIEF` mode.

A small PR stays small: mark a gate that does not apply `N/A` with its scope reason
instead of producing evidence for it.

## Project profile

Keep these keys in the project's `REVIEW.md` or nearest instructions, not in this file.

| Key | Example |
|---|---|
| Target branch | `main` / `master` / `develop` |
| Git host | GitHub / Bitbucket / GitLab / Azure DevOps |
| Issue tracker | Jira / GitHub Issues / Linear / Azure Boards |
| Test case store (optional) | TestRail / Xray / Zephyr / none |
| Local checks | `npm run lint && npm run typecheck && npm test` |
| Acceptance run | CI job / local suite / cloud grid |
| Verification environment | staging / preprod / local |
| Merge strategy | merge commit / squash / rebase |

If a key does not apply, write `none` and the reason. Never leave a blank and assume.
When the project has no profile, derive each key from the PR and the repository without
writing anything. A key you cannot resolve makes the gates that depend on it `UNKNOWN`.

## Status vocabulary

Report every DoD check with exactly one status:

- `VERIFIED`: evidence was inspected and satisfies the check. Name the evidence.
- `GAP`: an observed mismatch or a missing item. Give the next action.
- `UNKNOWN`: no access, or the available evidence cannot prove it either way. Give
  the next action.
- `N/A`: not applicable to this scope. Give the scope-based reason. Missing access
  is never `N/A`.

`GAP` and `UNKNOWN` are never a pass. "Ready" means every applicable check is
`VERIFIED`.

Keep three outcomes apart. Never report one as another:

1. **Technically mergeable:** no conflicts, CI green.
2. **Ready for merge:** every applicable check in gates 1 to 8 is `VERIFIED` for the
   reviewed HEAD.
3. **Done:** merged, with the merge read back, task records updated and the task closed.

## The gates

The nine gates are requirements coverage, target freshness, local checks, tests executed, test evidence, PR description, review, tracker records, and merge and closeout.

### Gate 1: Requirements coverage

The PR must deliver what the requirement asks for. Not what the code happens to do,
and not what a green run implies.

1. Read the source requirement: user story or issue, acceptance criteria (AC),
   approved comments, attachments, and linked tasks or PRs.
2. List every AC item and every required variant (role, locale or country, platform,
   data shape, negative path).
3. Map each item to the actual change: the test scenario and its assertions, or the
   code path.
4. Give each item a verdict:

| AC | Requirement (short) | Covered by | Verdict |
|---|---|---|---|
| AC01 | <behavior> | `<path>::<test or function>` | Covered |
| AC02 | <behavior> | `<path>` (happy path only) | Partial: <what is missing> |
| AC03 | <behavior> | none | Out of agreed scope: <decision link> |

- An assertion must actually check the AC's expected outcome. A step that only
  navigates is not coverage.
- A matching ID or tag, or a green run, does not prove coverage. Read the assertions.
- `Missing` or `Partial` blocks readiness unless the scope decision is recorded and
  linked.
- A change that does not trace to the requirement needs its own one-line
  justification, or goes to a separate PR.
- Do not change expected results to match the implementation. A mismatch is either a
  requirement change (get it approved) or a defect (report it).

### Gate 2: Target branch freshness and conflicts

The PR source must contain the **current** target branch, and nothing may conflict.

```bash
git fetch origin
git switch <feature-branch>
git merge origin/<target>            # or rebase, only if the branch is not shared
# resolve conflicts by intended behavior, not by "take mine"
git merge-base --is-ancestor origin/<target> HEAD && echo "target included"
git diff --check                     # no whitespace errors or conflict markers
git push                             # the remote PR head must contain the merge
```

- [ ] `origin/<target>` is an ancestor of the **published** PR head. A local-only
      merge does not count.
- [ ] No conflict markers are left anywhere.
- [ ] Semantic conflicts are resolved and both sides' intent is kept. When unsure,
      stop and ask.
- [ ] After the sync, local checks and affected tests are **re-run**. Evidence from
      before the sync is stale when the merge touched affected code.
- [ ] The reviewed SHAs are recorded: `source <sha7>`, `target <sha7>`.

### Gate 3: Local checks

- [ ] Build, lint, format, type check and unit tests pass on the synced HEAD.
- [ ] No debug leftovers: `console.log`, `print`, `.only`, `fdescribe`, skipped tests
      or commented-out code.
- [ ] No secrets, tokens or personal data in the diff, fixtures, screenshots or logs.
- [ ] Dependencies changed on purpose, and the lockfile is consistent.

Local checks are hygiene, not acceptance. They do not replace Gate 4.

### Gate 4: Tests executed (acceptance)

- [ ] The tests that cover the requirement ran on the **final code**: the synced HEAD,
      or a HEAD whose diff from the tested code does not touch the tested scope.
- [ ] They ran in the agreed verification environment.
- [ ] Each test result was read one by one. Do not trust the run total alone.
- [ ] Failures, skips and flaky retries are reported as they are, never rounded up to
      "green".
- [ ] Each code change after the run triggers a rerun of the affected tests.
- [ ] Data the test created was cleaned up. Shared accounts and other people's data
      were left intact.

Not a fresh pass: an old green result before later changes, a skipped test, a
"previously passed" reporter shortcut, or a retry-only pass with no note.

### Gate 5: Test evidence

Evidence must let a reviewer confirm the result without rerunning anything.

| Item | Required |
|---|---|
| Run link (CI job, report or test management run) | yes |
| Date of execution | yes |
| Environment (name and URL) | yes |
| Count: passed / total, and the unit (tests, cases, examples) | yes |
| Per-test detail: screenshot or report entry with readable steps (UI), request and response summary (API) | yes for UI and API tests |
| Trace, video or log for every failure | yes if any failed |
| Tested revision (SHA) | in the private review record, not in a public comment |

- Use the original report output. A summary rebuilt from raw JSON does not count.
- One evidence item per executed test or variant. One aggregate dashboard screenshot
  is not enough.
- Redact credentials, tokens and personal data before attaching.
- Name files `<issue>-<env>-<case>-<variant>.png`.

### Gate 6: PR description

- [ ] It follows the `nobrainer-writing` `PR` format, or the repository's own PR
      template when one exists. Each fact appears once.
- [ ] Each link resolves: the issue, the test cases, the changed files, the run.
- [ ] It describes the **final** behavior, not the history of attempts.
- [ ] It includes at least one real, dated execution row with a count. A row is never
      invented to fill the format.
- [ ] The saved PR is read back after publishing: it renders, lists nest, links work.

### Gate 7: Review

- [ ] Self-review of the full diff after the sync: correctness, edge cases, naming,
      duplicated code.
- [ ] Every review comment was answered or resolved. Each fix was pushed and the
      evidence rechecked.
- [ ] The required approvals are present.

### Gate 8: Tracker records (automation or QA task)

These checks can pass before the merge. The records that depend on it are in Gate 9.

- [ ] The task description is accurate. It is written once, up front, and only stale
      facts are corrected later.
- [ ] The task links the PR and its requirement.

### Gate 9: Merge and closeout

- [ ] The merge happens only with the owner's authorization. Readiness alone is
      advice, not permission.
- [ ] After the merge, the target branch contains the merge commit (read it back).
- [ ] The task holds the completion comment with evidence attached, showing `Merged`.
- [ ] The parent story or issue references the task and its coverage.
- [ ] The task is transitioned only after the merge is verified, and the transition
      is read back.
- [ ] Records are updated in this order: merge, task comment, parent comment, task
      transition.
- [ ] Temporary branches, worktrees and test data owned by this task are cleaned up
      after the evidence is saved.

## DoD report

Give this to the owner before the merge decision. It covers gates 1 to 8; gate 9
happens after the decision.

```markdown
**DoD <PR link>** - source `<sha7>` / target `<target> <sha7>`

- Requirements coverage: VERIFIED - AC01-AC03 mapped to `<file>`; no gaps
- Target freshness: VERIFIED - `origin/<target>` included in the pushed head, no conflicts
- Local checks: VERIFIED - lint, types, unit 142/142
- Tests executed: GAP - AC03 test not rerun after commit `<sha7>`; rerun `<command>`
- Evidence: UNKNOWN - no access to the CI report; need a link from <owner>
- PR description: VERIFIED - read back, links OK
- Review: VERIFIED - 2 approvals, 0 open threads
- Tracker records: N/A - docs-only change, no task

**Verdict:** Not ready - 1 gap, 1 unknown. Next: rerun AC03, attach the report.
```

The verdict is one of `Ready`, `Not ready` or `Readiness unknown`, followed by the
single next action. Use `Readiness unknown` when nothing is `GAP` but something is
`UNKNOWN`.

## Execution order

1. Read the requirement and the task. Build the AC-to-change map (Gate 1).
2. Fetch, sync the target into the branch, resolve conflicts and push (Gate 2).
3. Run the local checks on the synced HEAD (Gate 3).
4. Run the acceptance tests on the final code in the agreed environment, and read each
   result (Gate 4).
5. Collect the original evidence, then redact and name it (Gate 5).
6. Write or refresh the PR description and read it back (Gate 6).
7. Self-review, answer the review threads and push the fixes. If the code changed, go
   back to step 3 (Gate 7).
8. Post the DoD report and wait for the owner's merge decision.
9. After the authorized merge: read the merge back, add the task comment, add the
   parent comment, transition the task and clean up (Gate 9).

## Red flags

Stop and fix these before calling a PR ready:

- "CI is green" offered as the only proof of requirement coverage.
- The branch is behind `<target>`, or the merge exists only locally.
- The test evidence is older than the last change in the tested scope.
- A skipped or retried test is reported as passed.
- The PR description lists tests that do not exist in the diff, or skips tests that do.
- Case titles or IDs were typed from memory instead of read from the source.
- The task description was rewritten with results after the fact.
- The task was closed before the merge was verified.
