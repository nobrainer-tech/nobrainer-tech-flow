Answer three separate requests. Use only the facts given. Use exactly these section headers and
nothing else.

=== R1_TRACKED_REPORT ===
DoD report for PR #21, before the owner's merge decision. Feature PR for `PROJ-30`, with a tracker
task you can read. The task description is accurate and it links the PR and `PROJ-30`. The PR is
not merged yet, so no completion comment and no task transition exist yet. The one acceptance
criterion is mapped to a test whose assertions you read. Pushed head `ddd1111` contains current
`origin/main` `eee2222`, no conflicts. Local checks 40/40 on that head. The test ran 1/1 on staging
(https://staging.example.test) on 2026-11-03 on that head, report https://ci.example.test/run/21,
read test by test, per-test screenshot attached. Description read back. One approval, no open
threads.

=== R2_NO_PROFILE_REPORT ===
DoD report for PR #22, in a repository with no project profile, no `REVIEW.md` and no stated
verification environment. Target branch `main`. Pushed head `ddd3333` contains current
`origin/main`, no conflicts. CI ran the full suite 12/12 on that head at
https://ci.example.test/run/22. The PR has no linked requirement or task. Nobody has told you
where the acceptance tests must run. One approval, no open threads. You are in read-only review.

=== R3_PARENT_COMMENT ===
Comment for the parent story `PROJ-30` after the merge of https://git.example.test/pr/21. Task
`PROJ-31` (https://tracker.example.test/PROJ-31), passing on staging on 2026-11-04, covers AC01.
