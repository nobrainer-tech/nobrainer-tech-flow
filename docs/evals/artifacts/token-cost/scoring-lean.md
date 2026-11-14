# Token cost: LEAN arm scoring (frozen before its first run)

Question: does a five-line token budget in `CLAUDE.md`, with no Flow install, lower what a
Claude Code user spends to reach a verified fix?

- **LEAN**: the PLAIN fixture plus `lean-claude-md.md` as `CLAUDE.md`. No skills.
- Same tasks, hidden checks, retry turn, client, model, effort, flags and measures as
  `scoring.md`; the harness as fixed for the reported FLOW/PLAIN runs (two runs at a time).
- Two runs per task (12 runs). The baseline is the twelve clean PLAIN runs recorded in
  `results-clean-rerun.tsv` the same day; no PLAIN run is repeated.
- Manipulation check: no LEAN run lists `nobrainer-tech-flow` among its skills, and the
  repository copy has the five lines as `CLAUDE.md`.

RATIO = LEAN cost per verified fix / PLAIN cost per verified fix.

- `LEAN_SAVES`: RATIO <= 0.90 and LEAN verified fixes >= PLAIN (12).
- `EVEN`: 0.90 < RATIO < 1.10.
- `LEAN_COSTS_MORE`: RATIO >= 1.10.

The lines may be published as a token saver only on `LEAN_SAVES`, and only with this sample's
limits stated next to the number.
