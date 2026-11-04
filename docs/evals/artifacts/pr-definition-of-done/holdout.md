Answer six separate requests. Use only the facts given. Use exactly these section headers and
nothing else.

=== H1_TYPO_REPORT ===
DoD report for PR #7: a one-word typo fix in `README.md`, no ticket, no tests apply, no tracker task
exists for it. Pushed head `aaa1111` contains current `origin/main` `bbb2222`, no conflicts.
Link check run locally: 1/1. Self-reviewed, description read back, one approval, no open threads.

=== H2_ACCESS_REPORT ===
DoD report for PR #8: same facts as H1 except it is a feature PR for `PROJ-9` and it has a tracker
task, but you cannot open the tracker, so you cannot see whether the task records are right.
Its acceptance criterion is mapped to a test that ran 1/1 on staging on 2026-11-03 on the pushed
head, with report https://ci.example.test/run/9 read test by test.

=== H3_TASK ===
Write the automation task for story `PROJ-77` (https://tracker.example.test/PROJ-77): login with a
valid password opens the dashboard; login with a wrong password shows an error and stays on the
page. No work has started. The PR will target `main`, tests live in TestRail, environment staging.

=== H4_CODE_REVIEW_COMMENT ===
A code review comment: `sync_provider()` line 84 returns `200` when the provider times out, so the
caller treats a failed sync as success. Seen while reviewing in the test environment, no page URL.

=== H5_BUG ===
Bug report: on QA (https://qa.example.test/cart), as a guest user, adding the same item twice shows
quantity 1, and it should show 2. You reproduced it by hand. Evidence: `cart-qa.png` attached.
The request log suggests a cache may be involved, but nobody has verified that.

=== H6_REVIEW_REPLY ===
Reply to a review thread: you fixed the null check the reviewer asked for, in commit `ccc3333`.
