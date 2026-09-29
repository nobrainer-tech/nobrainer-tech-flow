# Installing nobrainer-tech-flow for OpenCode

Add the git-backed package to the `plugin` array in the global or project
`opencode.json`:

Use an immutable reviewed commit, not the moving default branch. Replace the
example ref only after the new commit passes the repository suite and its
public-clean/readback checks. For pre-merge review, use a local checkout and
explicit skills path instead.

```json
{
  "plugin": [
    "nobrainer-tech-flow@git+https://github.com/nobrainer-tech/nobrainer-tech-flow.git#NB_REVIEWED_COMMIT_SHA"
  ]
}
```

`NB_REVIEWED_COMMIT_SHA` is an intentionally non-runnable placeholder. Replace
it with the full SHA of the exact reviewed release. Record that SHA in the
release notes; do not silently follow `main` or copy an older package pin.

Restart OpenCode, list native skills, and confirm `nobrainer-tech-flow` is present.
The adapter registers the canonical `skills/` directory and prepends the small
shared `adapters/bootstrap.md` context to the first user message once. It does
not copy skill bodies into the prompt, add alternate skill trees, or inject on
every step when the marker is already present.

For a local checkout, either run `sh scripts/install.sh --client opencode` (no
Python needed; `scripts/install_skills.py --client opencode` installs the skills
alone) or configure the checkout's `skills/` directory as an OpenCode skills path.
See [the full installation guide](../docs/INSTALL.md).

The package ID is `nobrainer-tech-flow`. Existing
`nobrainer-tech-skills` registrations require the
[migration guide](../docs/MIGRATION_TO_FLOW.md) so old and new adapters do not
load together unnoticed.
