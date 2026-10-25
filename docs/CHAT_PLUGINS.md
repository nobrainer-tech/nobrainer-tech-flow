# ChatGPT and Claude plugins

nobrainer-tech-flow is one workflow of 18 modules for research, writing, planning and implementation, packaged as a portable plugin. The AI client loads the workflow and uses its available tools and permissions.

## Download and install

Download the plugin ZIP from the latest GitHub Release. It contains root plugin.json, an OpenAI compatibility manifest, a Claude compatibility manifest, the canonical skills with their references and a `.mcp.json` that declares one optional remote MCP server, `nobrainer-tech-flow` at `https://mcp.nobrainer.tech/mcp` (described below). The OpenAI manifest points to it with `"mcpServers": "./.mcp.json"`, because OpenAI's plugin directory does not accept skills-only submissions. The submission ZIP omits lifecycle hooks and app references. Only the ZIP declares the server: the Git marketplace and npm installs stay skills-only, so they do not connect to it. That entry uses OpenAI's required shape, a `url` without a `type`; Claude expects `"type": "http"` for a remote server, so `claude plugin validate` reports this entry as an error and states that Claude Code drops such an entry at load. A Claude upload of this ZIP has not been verified since the entry was added; the Claude directory tracks the separate skills-only export instead. To use the server in Claude, add it as a custom connector as described below. Claude Code's existing Git marketplace installation remains available separately.

In Claude, open Customize > Plugins, choose Add > Upload plugin and select the ZIP. Skills are supported in Chat, Cowork and Claude Code; available tools and permissions differ. Start a new conversation and ask: "Use nobrainer-tech-flow. Compare these options against my requirements and explain your recommendation with sources."

In ChatGPT Work or Codex, install from a supported local/repository marketplace or from the public Plugins directory once the listing is approved. The repository marketplace identifies this source package. A downloadable ZIP is a release artifact, not proof of directory approval. OpenAI's public directory requires a verified developer identity, package scans and platform review before publication.

The npm package `nobrainer-tech-flow` is published, so it can also serve as a plugin source. A marketplace can reference source type npm, package nobrainer-tech-flow and an exact published version. The client downloads the package without running npm lifecycle scripts.

To use Flow without installing anything, add the free remote MCP server `https://mcp.nobrainer.tech/mcp` in claude.ai (custom connector) or ChatGPT (custom MCP server), or in any MCP client. It needs no sign-in, is stateless and offers six read-only tools: `start_flow_task`, `get_flow_step`, `check_flow_evidence`, `check_flow_done`, `draft_flow_handoff` and `recommend_flow_model`. It gives the agent a task contract, an evidence check and a done gate plus a model advisor; it does not install the 18 modules. Per-client steps and which clients are verified: [MCP server README](../mcp/README.md#install).

## Check the installation

Use a fresh conversation and confirm the loaded module's name and version. Try a bounded research or writing task, then check that the final result includes its evidence and remaining gaps. Loading metadata or passing a package test does not establish task quality in every client.

If browser, shell, workers or local files are unavailable, the workflow must report that limit and use the permitted path. Installing a skill does not grant those capabilities, authorize publication or enable automatic model switching. Explicit user requirements and client policy remain authoritative.

## Sources and distribution boundary

- OpenAI plugin architecture: https://developers.openai.com/plugins/concepts/plugins
- OpenAI package formats and npm sources: https://developers.openai.com/plugins/build/plugins
- OpenAI publication: https://developers.openai.com/plugins/deploy/submission
- Claude supported surfaces: https://claude.com/docs/plugins/platform-support
- Claude publication: https://claude.com/docs/directory/publish

The inFakt integration uses an MCP server and OAuth to access an existing account: https://www.infakt.pl/integracje-z-infakt-za-pomoca-api/#asystenci-ai . The npm package and the Git marketplace install need only the skills and the client's existing tools, so they add no MCP backend and require no account access. The plugin ZIP declares the MCP server above; it needs no account, and the skills work without it. Privacy policy for that server: https://nobrainer.tech/flow/privacy/ ; terms: https://nobrainer.tech/flow/terms/ .
