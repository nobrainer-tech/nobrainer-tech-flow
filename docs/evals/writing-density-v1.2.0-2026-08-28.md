# Writing density evaluation — v1.2.0 candidate — 2026-08-28

## Objective

Test whether `nobrainer-writing` maximizes decision-relevant information per
word without dropping facts, conditions, uncertainty, evidence boundaries,
privacy or the requested action, and without replacing AI slop with fabricated
"human" mistakes.

## Research basis

The protocol synthesizes ten recent or maintained approaches: two public
humanizer skills, one concise-output skill, Microsoft, Google, Digital.gov, 18F,
Mailchimp, GitLab, Carbon and W3C guidance grouped into ten reviewed entries.
Per-source access or immutable-ref status, extracted mechanisms, limits and
design decisions are preserved in
[`the research record`](../../skills/nobrainer-writing/references/research.md).
The active skill does not name external workflow brands or load that record for
ordinary writing.

## Evidence status

```text
SKILL_SHA256: a756274e8a55cf32c7f2f15e2502801bcd7b31f30682d787646c81adee46dcda
BASELINE_RELEASE: v1.1.0
BASELINE_CAPABILITY: ABSENT
COMPARATIVE_SCORE_CLAIM: NONE
DEVELOPMENT_PROBE: PASS 5/5; HARD_FAILURES=NONE; MATERIAL_FINDINGS=NONE
FIRST_FINAL_HOLDOUT: PASS 5/5; HARD_FAILURES=NONE; MATERIAL_FINDINGS=NONE
INDEPENDENT_DIFF_REVIEW: NO_GO; missing release evidence fixed
RELEASE_HOLDOUT: PASS 5/5; HARD_FAILURES=NONE; MATERIAL_FINDINGS=NONE
DETERMINISTIC_SUITE: reproducible commands below
CLIENT_RUNTIME: NOT_VERIFIED
```

The development probe covered a dense project status, already concise text,
unsupported product hype, a safety caveat and a useful code comment. A separate
first final holdout covered Polish incident status, an email request, safe
installation steps, a nuanced multi-agent argument and evidence-led social copy.
Both passed a separate judge 5/5. Their exact prompts, normalized results, judge
prompts, judge results and raw final messages are retained under
[`artifacts/`](artifacts/).

After independent full-diff review identified missing release registration and
hash wiring, a third untouched release holdout was frozen. Fresh, isolated
candidate and judge sessions passed all five different cases. Full runtime,
baseline, command, warning and integrity evidence is in the
`release run record`.
No skill change was made from any release-holdout result.

Historical artifact hashes:

```text
DEVELOPMENT_PROMPT_SHA256: 4832e92e6ad46b17b6a677f04fb2a38c687008bc37502bd520e83bd3b246cb8b
DEVELOPMENT_OUTPUT_SHA256: d56e3d59c3e210ba85403b1e3518037fe1ad174209f08ba369369c6b481e9173
DEVELOPMENT_RAW_OUTPUT_SHA256: 589a0ed8f189f3576141fac6dfbd84af6d2f01badb820443842f5ac7fd2b8549
DEVELOPMENT_JUDGE_PROMPT_SHA256: bc0496a8e0f2db1c297ac66b5085a26979ccef413e065774680b2a0351cf16f1
DEVELOPMENT_JUDGE_OUTPUT_SHA256: 7fa6507438ee5c61befcd362859015019bb4448fdc24a439d2c7a416b3d7a2e1
DEVELOPMENT_RAW_JUDGE_OUTPUT_SHA256: 6240ac5b44b77219e354a97eae7f0bc54a7e08c9459a4187a6baa0e32130c620
FIRST_FINAL_PROMPT_SHA256: 5099b37e588c1bbbd361553d15c64bd520ef1d52b65b1b48fa41ff1cf3f0fb18
FIRST_FINAL_OUTPUT_SHA256: 0dba82f59aaae3ced7a63947777129e3bbf1defc0c1d9ca6254701a5586b21e2
FIRST_FINAL_RAW_OUTPUT_SHA256: 6fad54d8bbd9af39fcb2b56f892f86b47b152a68c7502174fe559a194b044335
FIRST_FINAL_JUDGE_PROMPT_SHA256: 7ae6424fb216e633a271e462f27c80f334dc75c7a653760fadcbf27f8bef4279
FIRST_FINAL_JUDGE_OUTPUT_SHA256: 234662037464ab4f17f2320b46c22312fa050fdfaaaa1995c97f9ba8ab3e1f33
FIRST_FINAL_RAW_JUDGE_OUTPUT_SHA256: 9367fac825428976b2a2f82a7218e8c2797acf93aeeb0a14bcb8d27ab6cb9f64
```

Historical sessions used `codex-cli 0.147.0`, `gpt-5.6-luna`, maximum reasoning
and a read-only sandbox:

```text
DEVELOPMENT_CANDIDATE_SESSION: 01a04914-753d-7eb3-8708-6aef3aec16b1
DEVELOPMENT_JUDGE_SESSION: 01a04915-5fcb-7fc0-84ca-1542ba4b2459
FIRST_FINAL_CANDIDATE_SESSION: 01a04916-a5f5-7641-87b3-2575c4868974
FIRST_FINAL_JUDGE_SESSION: 01a04917-ae78-7fe0-8448-78e5d22bf8e9
```

The earlier wrapper finish timestamps were not retained as public artifacts;
their exact raw outputs and session identities were. The later release holdout
supersedes that metadata gap for the release gate.

## Fixed rubric

Hard failures across the final gates include:

- changing, dropping or inventing a material fact, identifier, command,
  sequence, condition, uncertainty, caveat, owner or action;
- claiming completion, causation, production proof, legal authority or broad
  representativeness not supported by the source;
- simulating humanity with fake experience, mistakes, slang or opinions;
- hiding safety or privacy constraints to reduce length;
- returning process commentary instead of the requested finished prose.

## Reproducible deterministic checks

```bash
python3 scripts/validate_skills.py --suite
python3 -B -m unittest discover -s tests -v
git diff --check
```

## Proof boundary

The model runs prove only the frozen prompt/output contracts. They do not prove
that every future draft is concise, that a client discovered the skill, that an
AI detector will classify text in a particular way, or that target readers find
the result useful. Those require fresh task- and client-specific evidence.
