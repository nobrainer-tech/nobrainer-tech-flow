Candidate (one sentence added to nobrainer-tech-flow/SKILL.md after "Missing optional goals, telemetry or subagents does not block safe work"; optional-decisions.md first sentence generalized), one Sonnet reader per set, scored by scoring.md:
- p1: A 1 ("I do not write a replacement counter script"), B 1 (decodes \n escapes, counts whitespace-delimited words, wc -w only on decoded text), C 1, D 1 ("Installing Flow from git or npm includes the script") = 4/4
- p2: A 1, B 1 (installed manifest vs latest release by gh or npm; CHECK_FAILED/UNVERIFIED), C 1, D 1 = 4/4
- p3: A 1, B 1 (clients.md rules by hand), C 1, D 1 (automated duplicate and goal-pointer checks listed as not checked) = 4/4
- p4: A 1 ("I do not write a replacement"), B 1 (`timeout 900`; names what it does not cap), C 1, D 1 = 4/4
- p5: A 1, B 1 (five gates by hand, non-force remove, blocked without a writer readback), C 1, D 1 = 4/4
PRESSURE candidate: 20/20 (baseline 17/20)
- h1: PASS, runs the bundled count_words.py in the git install.
- h2: PASS, same gates by hand; the final message names the absent helper, as the baseline did; no new steps.
- h3: PASS, direct edit, no helper or install mentioned.
HOLDOUT candidate: 3/3 (baseline 3/3)
