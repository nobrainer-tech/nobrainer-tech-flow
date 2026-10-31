# Releasing nobrainer-tech-flow

This repository is the one product to promote: stars, issues and links point here.
Every channel below carries the same version from the same tag, and its links
(homepage, repository, support) lead back here. A stable release is finished only
when each channel reads back that version, or the gap is reported:

1. GitHub release from the annotated `vX.Y.Z` tag, with
   `nobrainer-tech-flow-X.Y.Z-plugin.zip` (`scripts/build_plugin.py`) and the
   `npm pack` tarball built from the merge commit; download each asset and compare its
   SHA-256 with the digest of that same file before upload.
2. npm: run the `Publish npm` workflow from the tag, then read back
   `npm view nobrainer-tech-flow version`.
3. Claude Code and Codex marketplaces in this repository: they follow the default
   branch, so install `nobrainer-tech-flow@nobrainer-tech` in a throwaway profile while
   `main` still equals the tag, and read back the version and the installed commit.
4. `nobrainer-tech/nobrainer-tech-flow-plugin`: export the release ZIP there
   through a PR. That copy is tracked only by the Claude directory, so leave out
   `.mcp.json`, the root `mcp.json`, the root portable `plugin.json`, the
   `.codex-plugin/` folder and `assets/` (Claude's validator rejects OpenAI's remote
   server shape, and the other manifests only add image-reference findings; ChatGPT and
   Codex use this repository's marketplace and the release ZIP). From `docs/` keep only
   `CHAT_PLUGINS.md` and `PRIVACY.md`, the two files its README and manifests link: the
   other guides and `docs/releases/` stay here, and the Claude directory's automatic
   checks flag the install commands and image references in them. Keep the
   repository's own Claude presentation fields and its `.claude-plugin/icon.png`
   (no `icon` field), as its README describes. Update `SOURCE.json`, run
   its unmodified `_maintainers/verify_release.py`, then release it. It is the hook-free copy that
   the Claude directory tracks, not a second project to promote.
5. MCP server: pin its guidance cards to the new tag in a PR
   (`cd mcp && node scripts/build-content.ts --tag vX.Y.Z --pin`; when a quoted rule was
   reworded, update `content/cards.yaml` to the new text, then `npm test`). After the merge,
   deploy per [mcp/docs/DEPLOY.md](../mcp/docs/DEPLOY.md) and read back that `initialize`
   on https://mcp.nobrainer.tech/mcp reports `serverInfo.version` ending in `+flow.X.Y.Z`.
   Never deploy a tree with an older advisor snapshot than production serves.
6. Website changelog: add the `X.Y.Z` entry, written from `RELEASE-NOTES.md`, to
   `sources/flow-www/site/changelog/index.html` and its `public_html/flow/changelog/` copy
   in `nobrainer-tech-www`, deploy it and read back https://nobrainer.tech/flow/changelog/.
   Add any earlier version the page is missing.
7. Claude directory (claude.ai/directory/manage) picks up the native plugin repository's
   default branch; OpenAI plugin directory (platform.openai.com/plugins) takes the
   native ZIP upload. Both submissions and publication clicks are owner-gated.

Finish with `python3 scripts/check_release_channels.py X.Y.Z`. It reads back the GitHub
release, npm, the native plugin release, the MCP server and the website changelog, and
exits 1 on any FAIL. The release is done only when it prints no FAIL; a channel that
cannot be fixed yet goes into the handoff's `Not checked` with its reason, and the next
release adds the missed version too. Skipping a step because it is owner-gated, manual or
"separate" still leaves it a FAIL here.
