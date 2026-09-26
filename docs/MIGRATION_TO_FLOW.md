# Move to nobrainer-tech-flow

Version **1.7.1** introduced an earlier display spelling.
The current display name is **nobrainer-tech-flow**; the repository,
public package/plugin identity and entry skill are `nobrainer-tech-flow`.
**From task to done.** Tell it what you need. Flow clarifies the goal, does the
work, and checks the result.

The canonical public repository identity is
[`nobrainer-tech/nobrainer-tech-flow`](https://github.com/nobrainer-tech/nobrainer-tech-flow)
and the product website is [nobrainer.tech/flow](https://nobrainer.tech/flow/).
The earlier 1.7.1 rename changed display/source routing. The proposed 2.0.0
upgrade also changes the entry skill and public package/plugin identities.
Done still means the agreed criteria are met and the result is checked; missing
access or an unresolved decision can require an explicit unblock action.

## Existing installation identities

The table below records the previous package identity for migration. Existing
registrations must be updated deliberately; a second package next to the old
one can cause duplicate routing.

| Surface | Previous identifier and migration |
|---|---|
| Existing package and Claude Code, Codex, Cursor, Kimi, Gemini and portable plugin IDs | `nobrainer-tech-skills` -> `nobrainer-tech-flow` after exact client readback |
| New public repository/package channel | `nobrainer-tech-flow` |
| Claude Code marketplace name | `nobrainer-tech` |
| Local development marketplace name | `nobrainer-tech-skills-dev` |
| OpenCode package entry prefix | `nobrainer-tech-skills@git+` -> `nobrainer-tech-flow@git+` at a reviewed immutable ref |
| OpenCode adapter module | `.opencode/plugins/nobrainer-tech-skills.js` |
| Pi extension module | `.pi/extensions/nobrainer-tech-skills.js` |
| Shared bootstrap marker | `NOBRAINER_BOOTSTRAP_V1` |
| Technical entrypoint and compatibility aliases | `$nobrainer-ultra` -> `$nobrainer-tech-flow`; old triggers are recognized only for migration |

The previous skill directory list is historical. The reviewed migration renames
the entry skill and adds the calibration skill; do not overwrite a foreign
installed target to force the migration.

```text
nobrainer-ultra
nobrainer-team
nobrainer-dispatcher
nobrainer-research
nobrainer-writing
nobrainer-build
nobrainer-security
nobrainer-sessions
nobrainer-spec-driven-development
nobrainer-wiki
nobrainer-browser
nobrainer-autoimprove
nobrainer-decide
nobrainer-rca
nobrainer-review
```

These are frozen predecessor identities. Do not rewrite their old release
records. Current public installation has eighteen skills, including
`nobrainer-tech-flow` and `nobrainer-auto-fine-tune`.

## Update the source in place

Use the client's supported upgrade mechanism. In OpenCode, change the old
package prefix to `nobrainer-tech-flow@git+` and use an immutable reviewed
commit pin. In plugin hosts, inspect the installed old ID and the new
registration before retiring anything; a new ID can coexist with the old
one and cause duplicate routing. Do not delete an unverified foreign target.

Existing local checkouts can keep their directory names. Installed symlinks may
point into that directory, so moving it is unnecessary. After confirming that
`origin` is this project's remote, its URL can be updated in place:

```bash
git remote set-url origin https://github.com/nobrainer-tech/nobrainer-tech-flow.git
```

The [current installation examples](INSTALL.md) require an exact reviewed
commit, validation and installer dry-run. `install_skills.py --migrate-legacy`
handles only a verified old symlink owned by the same checkout; a copied or
foreign old installation needs separate exact readback and a scoped migration.
The old path is never deleted merely because the new skill was installed.

After an update, read back the source commit and package identity, restart the
client and confirm that `nobrainer-tech-flow` loads once. A version change or an
installed file alone does not establish runtime compatibility.

## Old links and evidence

The previous repository name is `nobrainer-tech/nobrainer-tech-skills` and the
previous website route is `/skills/`. Their redirects, including corresponding
deep links under `/flow/`, are separate publication checks. Do not remove an old
installation or rewrite historical evidence to compensate for a missing redirect.

Tagged releases, dated reviews, frozen evaluation payloads and their source hashes
retain the original names and links as provenance. This rename adds no model
performance, token-savings or cross-client runtime claim. See the
[1.7.1 release record](releases/v1.7.1.md) for the local verification boundary;
repository rename, website redirects and client update readback must be verified
in their own systems.
