# Terms of Use: NoBrainer Tech Flow MCP server

Version 1.0. Effective date: 21 October 2026.
Published at https://nobrainer.tech/flow/terms/

## 1. Operator and acceptance

The NoBrainer Tech Flow MCP server (the server at mcp.nobrainer.tech; endpoint https://mcp.nobrainer.tech/mcp) is operated by mastalerz.it Arkadiusz Mastalerz, a Polish sole trader registered in CEIDG, ul. Krasnowolska 18E, 02-849 Warszawa, Poland; hello@nobrainer.tech. By calling the server, or by adding it to an AI client, you accept these terms. See also the Privacy Policy at https://nobrainer.tech/flow/privacy/.

## 2. The service

A free, public, stateless remote MCP server with six read-only tools: start_flow_task, get_flow_step, check_flow_evidence, check_flow_done, draft_flow_handoff and recommend_flow_model. There are no accounts and no paid tier. It stores no task content and runs no AI model.

The checks are consistency checks on the evidence your client reports. The server cannot see your machine and does not verify that reported facts are true. A passing result is not proof that work is correct or complete.

## 3. Licences and content

- Source code: MIT licence, in https://github.com/nobrainer-tech/nobrainer-tech-flow (folder `mcp/`).
- Guidance content is excerpted from the MIT-licensed NoBrainer Tech Flow release.
- The model advisor uses a pinned snapshot of the public NoBrainer AI benchmark (https://nobrainer.tech/ai/benchmark/). The snapshot includes third-party data under its own licences, listed in `mcp/data/benchmark/NOTICE.md` in the repository. Keep those attributions if you reuse the data.
- NoBrainer names and logos are not licensed by the MIT licence.

## 4. Acceptable use

You must not:

- flood the server or send automated traffic beyond a normal use of an AI client;
- try to bypass rate limits, for example by rotating tokens, contracts or addresses;
- send secrets (API keys, private keys, passwords) or other people's personal data;
- send unlawful content or use the server to harm others;
- reverse-engineer, extract or forge the HMAC keys, or forge tokens or receipts;
- attack, probe or interfere with the server or its hosting.

## 5. Rate limits, suspension and availability

Requests are rate limited per IP address and per contract. Over the limit, the server returns an error and you must wait. We may suspend or block abusive clients at any time. We may also pause, change or end the service at any time, for example if costs spike or for maintenance, with or without notice. The service is free and has no availability commitment.

## 6. Advisor output

Output of recommend_flow_model and other tools is general information. It may be outdated (the snapshot date is shown), is not a guarantee of model quality, price or availability, and is not legal, financial or other professional advice. Check current information with the provider before you decide.

## 7. No warranty

The service is provided "as is" and "as available", free of charge, without warranties of any kind, to the extent permitted by Polish law.

## 8. Liability

The tools support professional work; no specific outcome is guaranteed. That statement does not exclude our statutory liability. Toward businesses, and to the extent Polish law permits, we are not liable for indirect loss, lost profit or loss arising from reliance on tool output. Toward consumers, nothing in these terms limits or excludes liability beyond what Polish law and mandatory consumer law allow. Nothing in these terms excludes or limits liability for damage caused intentionally.

## 9. Consumers

Mandatory consumer rights take precedence over any conflicting term here.

## 10. Governing law

Polish law governs these terms. This choice does not deprive consumers of mandatory protection applicable in their country of habitual residence, including where EU conflict-of-law rules require it. Nothing here requires arbitration.

## 11. Changes

We may update these terms. The version and effective date are at the top. Material changes are announced on this page and in the release notes. Continued use after a change means you accept the new version.

## 12. Contact

mastalerz.it Arkadiusz Mastalerz, ul. Krasnowolska 18E, 02-849 Warszawa, Poland; hello@nobrainer.tech.
