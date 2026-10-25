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
   through a PR without `.mcp.json` or the root `mcp.json`, and remove the `mcpServers` field from the
   copied `.codex-plugin/plugin.json` (Claude's validator rejects a remote server
   without `type`, which OpenAI's required shape forbids). From `docs/` keep only
   `CHAT_PLUGINS.md` and `PRIVACY.md`, the two files its README and manifests link: the
   other guides and `docs/releases/` stay here, and the Claude directory's automatic
   checks flag the install commands and image references in them. Keep the
   repository's own Claude presentation fields and its `.claude-plugin/icon.png`
   (no `icon` field), as its README describes. Update `SOURCE.json`, run
   its unmodified `_maintainers/verify_release.py`, then release it. It is the hook-free copy that
   the Claude directory tracks, not a second project to promote.
5. Claude directory (claude.ai/directory/manage) picks up that repository's
   default branch; OpenAI plugin directory (platform.openai.com/plugins) takes the
   native ZIP upload. Both submissions and publication clicks are owner-gated.
6. Changelog on https://nobrainer.tech/flow/changelog/ after owner preview.
