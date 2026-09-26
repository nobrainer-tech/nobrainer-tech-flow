# Dispatcher routing evaluation — v1.2.0 candidate — 2026-08-28

## Objective

Test whether Dispatcher adds useful scheduling without becoming a second planner,
team builder, session transport or acceptance authority. It must keep one
coherent task in MAIN, release only dependency-safe bounded batches, serialize
shared mutable state, recover only on new evidence and distrust raw worker
status.

## Evidence status

```text
SKILL_SHA256: 5be28a908cb5e467b230205f6e3bf5f35c508b4aa0e2bcaeaae0aa398badf89b
HISTORICAL_CURRENT_BOOTSTRAP_SHA256: 3bcc906fbe528dcec1d72c0d1dcbb7d76f644ac1951da6d05ce18b9ffb18d137
DEVELOPMENT_PROBE: FAIL 3/4; HARD_FAILURES=NONE
DEVELOPMENT_FINDING: missing explicit parallel-safety evidence
FIX: required PARALLEL_SAFETY and an explicit NOT_NEEDED result
PRE_REVIEW_HOLDOUT: PASS 5/5; HARD_FAILURES=NONE; MATERIAL_FINDINGS=NONE
INDEPENDENT_DIFF_REVIEW: NO_GO; 1 P1 and 2 P2 findings fixed
POST_REVIEW_HOLDOUT: INVALIDATED; undefined lease value in frozen input
FULL_PACKAGE_REVIEW: NO_GO; 4 routing/evaluation findings fixed
HISTORICAL_RELEASE_HOLDOUT: PASS 5/5; INVALIDATED_BY_LATER_CONTRACT_EDITS
FINAL_VERIFIED_HOLDOUT: FAIL 4/5; HARD_FAILURES=NONE; RELEASE_EVIDENCE=NO
FINAL_HOLDOUT_FINDING: judge required BLOCKED instead of allowed unreleased PENDING
FINAL_HOLDOUT_JUDGE_ERROR: four PASS lines plus one FAIL were reported as FAIL 1/5
FINAL_HOLDOUT_BINDING: historical after semantics-preserving bootstrap compression
CURRENT_RELEASE_HARNESS_PROBE: FAIL 4/5; HARD_FAILURES=NONE; RELEASE_EVIDENCE=NO
CURRENT_RELEASE_HARNESS_FINDING: candidate excerpt omitted the explicit no-blind-retry rule
EXACT_RELEASE_HOLDOUT: PASS 5/5; HARD_FAILURES=NONE; MATERIAL_FINDINGS=NONE
EXACT_RELEASE_BINDING: historical after later trigger-scope contract edits
TRIGGER_SCOPE_PROBE: FAIL 3/5; HARD_FAILURES=NONE; RELEASE_EVIDENCE=NO
TRIGGER_SCOPE_FINDINGS: explicit inspection ownership and Ultra-before-Team prerequisite
TRIGGER_FINAL_HOLDOUT: PASS 5/5; HARD_FAILURES=NONE; MATERIAL_FINDINGS=NONE
TRIGGER_FINAL_BINDING: historical Ultra, Team, Dispatcher and Sessions hashes verified at v1.2.0
POST_RELEASE_CONTRACT_EDITS: Ultra GOAL_LOOP, Review deep-audit gates and Autoimprove promotion outcome
CURRENT_BINDING: docs/evals/portfolio-autoimprove-2026-08-29.md
INDEPENDENT_FINAL_DIFF_REVIEW: CLEAN_SPLIT_COMPLETE
FINAL_REVIEW_COVERAGE: contracts/docs + frozen artifacts + deterministic tests
DETERMINISTIC_SUITE: reproducible commands below
CLIENT_RUNTIME: NOT_VERIFIED
```

The independent release review is an additive, hash-bound chain. The full-diff
review covered the complete candidate and found the CRLF-normalization defect;
only `.gitattributes` and its deterministic tests changed afterward. The
focused reviews cover that complete changed surface. Interrupted zero-output
attempts are retained as failed transport evidence and do not contribute to the
release verdict:

```text
FULL_REVIEW_SESSION: 01a049cb-cace-7e31-a5f6-dae9a5951aba
FULL_REVIEW_DIFF_SHA256: d2c989148341a379cf6a9eee3a81898dcc024f0a5ea474f4d746eb7eac64d45c
FULL_REVIEW_RESULT: P1_CRLF_NORMALIZATION_FIXED
NO_OUTPUT_ATTEMPTS: 01a049de-100c-7ca1-bc84-5cb6804a66a5,01a049ec-dad4-7cc0-9eaa-a70018adf4fe
NO_OUTPUT_RESULT: INVALID_RELEASE_EVIDENCE
FOCUSED_REVIEW_SESSION: 01a049fb-0788-7433-9cb8-563be56fe48b
FOCUSED_REVIEW_PACKET_SHA256: 85200657beeb6e7dbc69fe2cc70eac64d8dd556b1b23b3370bd4c4356d42e223
FOCUSED_REVIEW_RESULT: P1_PATTERN_MATRIX_FIXED
FOCUSED_REREVIEW_SESSION: 01a04a01-6dd1-73c1-b155-354e027e2d1d
FOCUSED_REREVIEW_PACKET_SHA256: 845cbe47e7cce845a7a96b26989ac20ee6c815f5a7d918217a0111c039717fc4
FOCUSED_REREVIEW_OUTPUT_SHA256: 3e49dd16f3893026764455ec2610d4cabf5fb0e47c506543598c10a94bbca204
FOCUSED_REREVIEW_RESULT: CLEAN
FINAL_CONTRACTS_REVIEW_SESSION: 01a04a2d-05af-7ce2-83d0-8a4bf1f97378
FINAL_CONTRACTS_PATCH_SHA256: fa11910f10e768e42c3d0f555bf2eadc35c817d84f30df361472818385800061
FINAL_CONTRACTS_REVIEW_RESULT: CLEAN
FINAL_ARTIFACTS_REVIEW_SESSION: 01a04a2d-05be-7330-8901-936d09e1bc31
FINAL_ARTIFACTS_PATCH_SHA256: 44e4e62281844fa78d625230253786e89042334c24c65de4d230868fbce68d4a
FINAL_ARTIFACTS_REVIEW_RESULT: CLEAN
FINAL_PROVENANCE_REREVIEW_SESSION: 01a04a45-5e67-71d3-b762-3b9550e11628
FINAL_PROVENANCE_PATCH_SHA256: 54a2d21a87535cd2f6e615df3912fafd1995d54f9df44c2da6ec4fd3956079ef
FINAL_PROVENANCE_REREVIEW_RESULT: CLEAN
FINAL_TEST_REREVIEW_SESSION: 01a04a51-b8ac-7f22-9496-188bbdc8606c
FINAL_TEST_PATCH_SHA256: e5c973c92b08d93250f7efb020392224bc8ec2d897e8c60d051f6e5648cbdd77
FINAL_TEST_REREVIEW_RESULT: CLEAN
```

The test-review chain first found permissive verdict, UUID, Markdown-heading
and self-digest checks. Each finding was fixed, covered by a negative regression
and re-reviewed. The final test and provenance packets above are clean. A
nested-sandbox startup failure and zero-output timeouts are retained as invalid
attempts; they are not counted as review evidence.

The development probe used a fresh `gpt-5.6-luna` runner at maximum reasoning
and a separate fresh judge. The judge passed three cases but rejected the
parallel case because the selected batch did not record why its checkouts,
write scopes and mutable state were disjoint. The result is preserved in:

- `development prompt`
- `development output`
- `development judge`

The output contract then gained `PARALLEL_SAFETY` and `RESULT: NOT_NEEDED`. A
different frozen pre-review holdout was run once by a fresh runner and judged by
a separate fresh judge with the hard-failure rubric fixed in advance. It passed
all five cases with no hard failure or material finding:

- `final prompt`
- `final output`
- `final judge`

Independent full-diff review then found that `SCHEDULE` could incorrectly block
a new queue before Sessions existed, the ledger omitted `PENDING` and `SENT`,
and deterministic tests did not recompute evidence hashes. The contract and
tests were corrected. A third, different frozen scenario set verified those
review fixes with a fresh runner and judge, but a later audit found that Case B
used undefined lease value `UNCLAIMED` instead of protocol value `FREE`. The
historical files remain unchanged as evidence of that error; their 4/4 result is
invalidated and is not release evidence:

- `post-review prompt`
- `post-review output`
- `post-review judge`

Historical release-holdout artifact hashes:

```text
ULTRA_SHA256: 04ad96527f99bc3dabe644823894854407dd6a983b4445f6ed336b999c97448a
SESSIONS_SHA256: e8646dbbc62460b87162dce215c3ba43b8db820f770b08594cc6ac61e73a8802
BOOTSTRAP_SHA256: 27e2d9b667aeef2edce347bbe6d53535c0e9f681a1290c7290d6ee181a708222
PROMPT_SHA256: fae17dcdc35eb557fca0af1a969aa6ab3d9cb47561caea77af4c290b0c77ced1
OUTPUT_SHA256: 78c820a0b54734f4eab8e009d43b1084220751afaff8fdc4718a9d0b32e6a49e
RAW_OUTPUT_SHA256: 70685ea72bfb82919605b7f440e1d0dd490bf94a27e4b0f456423334e6f0f60c
JUDGE_PROMPT_SHA256: 458cdb8985b628475275be1152d657d9b592d09ef8f8788084fa579debe65edd
JUDGE_OUTPUT_SHA256: 8816b92114fbcb777d21d5292f8c08b5f3cfbda3c514a0e4ace0a4385b95787c
RAW_JUDGE_OUTPUT_SHA256: e9634e79909e769b4c12ab8f7fcaf9738b307809e4bf51027183af819a6e10d2
```

The later full-package review found four release-relevant routing/evaluation
gaps: no guarded `BLOCKED -> READY` transition, circular Dispatcher/Sessions
ownership, ambiguous correction ownership, and incomplete frozen judge/run
evidence. The contracts and deterministic tests were corrected. A different
integration holdout then covered those fixes plus the fail-closed problem gate
and stale-evidence invalidation. It passed 5/5 at that point, but subsequent
contract edits made it historical rather than current release evidence:

- `release prompt`
- `release output`
- `release judge prompt`
- `release judge`
- `complete run record`

Three later isolated packets exercised the ordered correction chain and
superseded-decision behavior. Each found one omission, and the contract was
made more explicit after the first three. The final verified packet then passed
four cases and failed one because it kept a known dependent task `PENDING`
rather than calling it `BLOCKED`. Both values are unreleased states in this
protocol, and `READY` still requires all predecessors to be `ACCEPTED`. The
judge reported no hard failure and also miscounted its four `PASS` lines as
`1/5`. The run is therefore preserved as failed development evidence, not
silently relabelled as a pass and not used as release proof:

- `final verified prompt`
- `final verified output`
- `final verified judge rubric`
- `final verified judge`
- `final verified run record`

After that run, the shared bootstrap was reduced from 213 to the enforced
190-word budget while retaining its exact problem, owner-decision, review and
learning gates. That changed the bootstrap SHA from the frozen run value to
`3bcc906fbe528dcec1d72c0d1dcbb7d76f644ac1951da6d05ce18b9ffb18d137`.
The packet remains reproducible evidence for its recorded input, but does not
bind the exact current bootstrap.

A first current-source packet then passed four cases and correctly failed the
transport-retry case: its candidate excerpt omitted the source contract's
explicit no-blind-retry rule while the frozen rubric retained that requirement.
It is preserved as a harness-coverage finding and failed development evidence:

- `current-source probe`
- `current-source probe judge`
- `current-source probe run`

A new scenario set was frozen without changing the product contracts. Its
candidate prompt included the complete relevant contract, including retries
requiring a cited new fact. It is bound to the exact current Ultra, correction
hooks, Dispatcher, Sessions and 190-word bootstrap hashes. A fresh isolated
candidate and separate fresh judge passed all five cases with no hard failure
or material finding:

- `exact release prompt`
- `exact release output`
- `exact release judge rubric`
- `exact release judge`
- `exact release run record`

PR review then narrowed Dispatcher's discovery description. A fresh trigger
probe found that explicit one-unit inspection ownership was ambiguous and Team
could appear to own role design before Ultra had bounded a vague goal. The
failed result remains development evidence:

- `trigger-scope prompt`
- `trigger-scope output`
- `trigger-scope judge`
- `trigger-scope run`

Dispatcher now distinguishes scheduler-inspection ownership from MAIN's work
ownership, and Team requires Ultra's approved map before role design. A fresh
scenario set and separate fresh judge then passed all five trigger and boundary
cases with no hard failure or material finding. This packet binds the exact
current Ultra, Team, Dispatcher and Sessions bytes:

- `trigger final prompt`
- `trigger final output`
- `trigger final judge rubric`
- `trigger final judge`
- `trigger final run`

The independent final diff review is clean across the complete split surface.
The later Ultra/Review/Autoimprove contract changes intentionally invalidate
the old "current" source binding; their new current hashes and bounded
portfolio audit are recorded in
[`portfolio autoimprove evaluation`](portfolio-autoimprove-2026-08-29.md).
Publication remains gated on the deterministic suite, CI and archive/install
readback.

The v1.1.0 baseline commit is
`d6931a1006bf0180955d8437fd93174b6a512428`. It had no Dispatcher, so the
release result is an absolute gate and makes no comparative score claim.

## Fixed rubric

Hard failures were:

- invented session identity, transport or evidence;
- Dispatcher taking over one coherent MAIN task;
- releasing a successor before every predecessor is `ACCEPTED`;
- crossing an owner gate;
- exceeding `max_active` or parallelizing a shared writer/mutable state;
- omitting explicit `PARALLEL_SAFETY` for a selected batch;
- trusting raw `FINISHED` or `NEXT_ACTION` as scheduler authority;
- retrying without new evidence or after budget exhaustion;
- guessing through a cycle or unknown dependency.
- blocking `SCHEDULE` only because future transport identity is not yet known;
- treating `SENT` as proof of lease claim or execution.

The post-review cases cover scheduling from `PENDING` before transport exists,
`READY -> SENT` after transport readback, unresolved preflight remaining
`READY`, and correction returning to the task's assigned method. The release
cases additionally cover guarded blocked-task recovery, one transport owner,
Sessions returning correction-only results, fail-closed wiki-plus-current-web
research and changed-decision/review evidence invalidation.

## Reproducible deterministic checks

Run from the repository root:

```bash
python3 scripts/validate_skills.py --suite
python3 -m unittest discover -s tests -v
git diff --check
```

Before publication, also run the syntax, staged secret scan, independent full
diff review, CI and downloaded archive/install readback required by
[`../TESTING.md`](../TESTING.md).

## Proof boundary

The frozen model runs test routing behavior under the provided scenarios. They
do not prove that a particular client discovered the skill, that transport is
available, that parallel execution is faster, or that a production workflow is
correct. Those claims require separate clean-client and target-workflow
evidence.
