# Move to NoBrainer.Tech Flow

Version **1.7.1** changes the product name to **NoBrainer.Tech Flow**.
**From task to done.** Tell it what you need. Flow clarifies the goal, does the
work, and checks the result.

The canonical public repository identity is
[`nobrainer-tech/nobrainer-tech-flow`](https://github.com/nobrainer-tech/nobrainer-tech-flow)
and the product website is [nobrainer.tech/flow](https://nobrainer.tech/flow/).
The skill contracts and optional command runner are unchanged from 1.7.0.
Done still means the agreed criteria are met and the result is checked; missing
access or an unresolved decision can require an explicit unblock action.

## Existing installation identities

Display names and source URLs change. These exact technical identifiers remain
stable so a client can update an existing installation instead of treating Flow
as a second package:

| Surface | Preserved identifier |
|---|---|
| Existing package and Claude Code, Codex, Cursor, Kimi, Gemini and portable plugin IDs | `nobrainer-tech-skills` |
| New public repository/package channel | `nobrainer-tech-flow` |
| Claude Code marketplace name | `nobrainer-tech` |
| Local development marketplace name | `nobrainer-tech-skills-dev` |
| OpenCode package entry prefix | `nobrainer-tech-skills@git+` |
| OpenCode adapter module | `.opencode/plugins/nobrainer-tech-skills.js` |
| Pi extension module | `.pi/extensions/nobrainer-tech-skills.js` |
| Shared bootstrap marker | `NOBRAINER_BOOTSTRAP_V1` |
| Technical entrypoint and compatibility aliases | `$nobrainer-ultra`; `nb-flow`, `nb-ultra` and `nb-workflow` are aliases only |

All fifteen skill directory and frontmatter names remain unchanged:

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

Their existing aliases, configuration paths and installer targets are unchanged.
The legacy technical name `nobrainer-tech-skills` may therefore still appear in package
managers and client settings. It identifies the same product; do not add a
second compatibility package or rename installed directories without a separate
migration. New public source links and checkout paths use `nobrainer-tech-flow`.

## Update the source in place

Use the existing client's normal update mechanism and preserve its package ID.
For a Git-backed OpenCode entry, change only the repository URL and the reviewed
commit pin, keeping the prefix shown above; see [Installation](INSTALL.md).

Existing local checkouts can keep their directory names. Installed symlinks may
point into that directory, so moving it is unnecessary. After confirming that
`origin` is this project's remote, its URL can be updated in place:

```bash
git remote set-url origin https://github.com/nobrainer-tech/nobrainer-tech-flow.git
```

The [current installation examples](INSTALL.md) use `nobrainer-tech-flow` for a
new checkout and still require an exact reviewed commit, validation and an
installer dry-run. This guide does not run an update, move a checkout, rename
installed directories or install anything globally.

After an update, read back the source commit and package identity, restart the
client and confirm that `nobrainer-ultra` loads once. A version change or an
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
