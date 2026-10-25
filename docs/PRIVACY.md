# Privacy for the nobrainer-tech-flow plugin

nobrainer-tech-flow distributes MIT-licensed skills, reference documents and local helpers. The skills, the npm package and the Git marketplace install have no publisher-operated backend, telemetry or account requirement, and installing them does not transmit your conversation, files or credentials to NoBrainer Tech.

The downloadable plugin ZIP built for plugin directories also declares one optional remote MCP server, `nobrainer-tech-flow` at `https://mcp.nobrainer.tech/mcp`, in its `.mcp.json`. It needs no sign-in and offers six read-only tools. When your client calls it, the server processes the tool inputs in memory to compute the answer and keeps no copy; the hosting provider processes the IP address and other request data for delivery, security and rate limiting. The full policy for that server is published at https://nobrainer.tech/flow/privacy/ and its terms at https://nobrainer.tech/flow/terms/. Do not send secrets or personal data to its tools.

Your AI client processes your task and may use its own tools under its permissions and privacy settings. Requested research can contact external sources. The optional release checker reads public GitHub release metadata; GitHub receives the ordinary network request. Optional Jev and Laya decision profiles remain off until you enable them with the required data and cost authority.

The npm installer writes local release files and managed client configuration only with an explicit --apply flag. Review the preview before applying. Its undo preserves unrelated files. Release files retained for stable installation are documented in INSTALL.md.

For questions or source issues, use https://github.com/nobrainer-tech/nobrainer-tech-flow/issues. Do not include private task data or credentials in public issues. The selected AI client's own terms and privacy policy govern that client's processing.
