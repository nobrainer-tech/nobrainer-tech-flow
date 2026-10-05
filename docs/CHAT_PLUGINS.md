# ChatGPT and Claude plugins

nobrainer-tech-flow is a portable skills plugin. It provides the same eighteen modules for research, writing, planning and implementation. The AI client loads the workflow and uses its available tools and permissions.

## Download and install

Download the plugin ZIP from the latest GitHub Release. It contains root plugin.json, an OpenAI compatibility manifest, a Claude compatibility manifest and the canonical skills with their references. The submission ZIP omits lifecycle hooks and app references. Claude Code's existing Git marketplace installation remains available separately.

In Claude, open Customize > Plugins, choose Add > Upload plugin and select the ZIP. Skills are supported in Chat, Cowork and Claude Code; available tools and permissions differ. Start a new conversation and ask: "Use nobrainer-tech-flow. Compare these options against my requirements and explain your recommendation with sources."

In ChatGPT Work or Codex, install from a supported local/repository marketplace or from the public Plugins directory once the listing is approved. The repository marketplace identifies this source package. A downloadable ZIP is a release artifact, not proof of directory approval. OpenAI's public directory requires a verified developer identity, package scans and platform review before publication.

For npm users, the npm package is also a plugin source. A marketplace can reference source type npm, package nobrainer-tech-flow and an exact published version. The client downloads the package without running npm lifecycle scripts.

## Check the installation

Use a fresh conversation and confirm the loaded module's name and version. Try a bounded research or writing task, then check that the final result includes its evidence and remaining gaps. Loading metadata or passing a package test does not establish task quality in every client.

If browser, shell, workers or local files are unavailable, the workflow must report that limit and use the permitted path. Installing a skill does not grant those capabilities, authorize publication or enable automatic model switching. Explicit user requirements and client policy remain authoritative.

## Sources and distribution boundary

- OpenAI plugin architecture: https://developers.openai.com/plugins/concepts/plugins
- OpenAI package formats and npm sources: https://developers.openai.com/plugins/build/plugins
- OpenAI publication: https://developers.openai.com/plugins/deploy/submission
- Claude supported surfaces: https://claude.com/docs/plugins/platform-support
- Claude publication: https://claude.com/docs/directory/publish

The inFakt integration uses an MCP server and OAuth to access an existing account: https://www.infakt.pl/integracje-z-infakt-za-pomoca-api/#asystenci-ai . Flow currently needs skills and the client's existing tools, so this distribution does not add an MCP backend or require account access.
