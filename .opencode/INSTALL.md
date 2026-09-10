# Installing NoBrainer.Tech Flow for OpenCode

Add the git-backed package to the `plugin` array in the global or project
`opencode.json`:

Use an immutable reviewed commit, not the moving default branch. Replace the
example ref only after the new commit passes the repository suite and its
public-clean/readback checks. For pre-merge review, use a local checkout and
explicit skills path instead.

```json
{
  "plugin": [
    "nobrainer-tech-skills@git+https://github.com/nobrainer-tech/nobrainer-tech-flow.git#NB_REVIEWED_COMMIT_SHA"
  ]
}
```

`NB_REVIEWED_COMMIT_SHA` is an intentionally non-runnable placeholder. Replace
it with the full SHA of the exact reviewed release. Record that SHA in the
release notes; do not silently follow `main` or copy an older package pin.

Restart OpenCode, list native skills, and confirm `nobrainer-ultra` is present.
The adapter registers the canonical `skills/` directory and prepends the small
shared `adapters/bootstrap.md` context to the first user message once. It does
not copy skill bodies into the prompt, add alternate skill trees, or inject on
every step when the marker is already present.

For a local checkout, either use `scripts/install_skills.py --client opencode`
or configure the checkout's `skills/` directory as an OpenCode skills path.
See [the full installation guide](../docs/INSTALL.md).

The package ID remains `nobrainer-tech-skills` to update existing installations.
See the [Flow migration guide](../docs/MIGRATION_TO_FLOW.md) before changing a configured source.
