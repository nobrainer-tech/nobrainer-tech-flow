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
4. `nobrainer-tech/nobrainer-tech-flow-plugin` is the copy that the Claude directory scans;
   ChatGPT and Codex use this repository's marketplace and the release ZIP instead. The
   directory refuses scripts, programs and every other file outside Markdown, plain text,
   JSON, YAML and PNG, JPEG, GIF, WebP or ICO images from organizations it has not verified
   (`LOCAL_CODE_FILE_TYPE`, which refused `4eff9df`). It also refuses any file that starts
   with `#!` and any package-manager file, so that copy ships no script at all; git and npm
   installs keep every script. Export it from the downloaded release ZIP into a clean
   checkout of that repository, then publish the diff through a PR:

   ```bash
   python3 scripts/export_native.py nobrainer-tech-flow-X.Y.Z-plugin.zip \
     --tag vX.Y.Z --commit <tag commit> --copy ../nobrainer-tech-flow-plugin
   ```

   The exporter works as follows:
   - From the ZIP it keeps every `skills/` file of an allowed type, byte for byte. It leaves
     out `skills/*/scripts/`, and `nobrainer-tech-flow/SKILL.md` tells the agent what to do
     when a named script is absent.
   - Also from the ZIP it takes `LICENSE`, `SECURITY.md`, `docs/CHAT_PLUGINS.md` and
     `docs/PRIVACY.md`.
   - It keeps the copy's own `README.md`, `AGENTS.md`, `.claude-plugin/icon.png` (no `icon`
     field), marketplace manifest, CI workflow and listing fields in
     `.claude-plugin/plugin.json`.
   - It writes `SOURCE.json`, then runs `scripts/verify_native_export.py`, which the copy's
     CI also runs from the tag. That verifier checks the type rule, refuses `#!`
     and package-manager files, and requires every kept skill file to match the ZIP.

   The copy is the directory's snapshot of this release, not a second project to promote.
5. MCP server: pin its guidance cards to the new tag in a PR
   (`cd mcp && node scripts/build-content.ts --tag vX.Y.Z --pin`; when a quoted rule was
   reworded, update `content/cards.yaml` to the new text, then `npm test`). After the merge,
   deploy per [mcp/docs/DEPLOY.md](../mcp/docs/DEPLOY.md) and read back that `initialize`
   on https://mcp.nobrainer.tech/mcp reports `serverInfo.version` ending in `+flow.X.Y.Z`.
   Never deploy a tree with an older advisor snapshot than production serves. Then run the
   `Publish MCP Registry` workflow from the tag (or from `main` while it still carries the
   release): it publishes `mcp/server.json`, whose version is bumped with the other
   manifests, to the official MCP Registry as `io.github.nobrainer-tech/nobrainer-tech-flow`
   through GitHub OIDC. It refuses to run until the live server serves the release.
6. Website changelog: add the `X.Y.Z` entry, written from `RELEASE-NOTES.md`, to
   `sources/flow-www/site/changelog/index.html` and its `public_html/flow/changelog/` copy
   in `nobrainer-tech-www`, deploy it and read back https://nobrainer.tech/flow/changelog/.
   Add any earlier version the page is missing.
7. Claude directory (claude.ai/directory/manage) picks up the native plugin repository's
   default branch; OpenAI plugin directory (platform.openai.com/plugins) takes the
   native ZIP upload. Both submissions and publication clicks are owner-gated.

Finish with `python3 scripts/check_release_channels.py X.Y.Z`. It reads back the GitHub
release, npm, the native plugin release, the MCP server, its MCP Registry entry and the
website changelog, and
fails when a pull request in this or the native plugin repository has been open for more
than a day: merge it, close it with a reason, or report it. It exits 1 on any FAIL. The release is done only when it prints no FAIL; a channel that
cannot be fixed yet goes into the handoff's `Not checked` with its reason, and the next
release adds the missed version too. Skipping a step because it is owner-gated, manual or
"separate" still leaves it a FAIL here.
