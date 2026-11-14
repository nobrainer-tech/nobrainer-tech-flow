# Token cost: SLIM arm scoring (frozen before its first run)

Question: does shortening the text Flow always loads remove the 1.31x cost measured for FLOW?

- **SLIM**: the FLOW arm with two changes: each skill's `description` replaced from
  `slim-descriptions.json` (5298 to 2106 characters in all) and `slim-bootstrap.md` as
  `CLAUDE.md` (220 to 51 words). Skill bodies and references are unchanged (`6330c3b`).
- **PLAIN**: twelve fresh runs, interleaved with SLIM, so both arms share the same hour.
- Same tasks, hidden checks, retry turn, client, model, effort, flags and measures as
  `scoring.md`; two runs at a time.
- Manipulation check: every SLIM run lists `nobrainer-tech-flow` among its skills, and its
  copy carries the short description; no PLAIN run lists it.

Primary: RATIO = SLIM cost per verified fix / fresh PLAIN cost per verified fix.

- `SLIM_SAVES`: RATIO <= 0.90 and SLIM verified fixes >= PLAIN.
- `EVEN`: 0.90 < RATIO < 1.10 (the always-loaded overhead is gone within this sample).
- `SLIM_COSTS_MORE`: RATIO >= 1.10.

Secondary, reported only: SLIM against the FLOW table in `results-clean-rerun.tsv`.

Not measured: whether agents still pick the right skill with the short descriptions
(routing). A SLIM result alone never ships; routing evals must pass first.
