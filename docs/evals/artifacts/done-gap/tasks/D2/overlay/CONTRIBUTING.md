# Contributing to shop

Thanks for helping. A few rules keep the package small and the history readable.

## Workflow

- Work on a branch and open a pull request; `main` is protected.
- One concern per pull request. Keep the diff small enough to read in one sitting.
- Run `python3 -m unittest discover -s tests` before you push. The suite must pass.

## Code

- Standard library only. No new dependencies without a discussion first.
- Money is rounded to two decimals at the point where it is summed, not per line of output.
- Keep modules under 200 lines; split by responsibility, not by layer.

## User-facing CLI changes

Every change to what `python3 -m shop` accepts or prints must, in the same pull request:

1. be documented in `README.md` under the `## CLI` section;
2. get a line under `## Unreleased` in `CHANGELOG.md`;
3. get a test in `tests/test_cli.py` that runs `python3 -m shop` through `subprocess`, so the real entry point is covered and not only the functions behind it.

Reviewers will not merge a CLI change that misses one of the three.

## Commits

Short imperative subject, no trailing period. Say why in the body when it is not obvious.
