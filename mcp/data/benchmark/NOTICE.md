# Benchmark snapshot notice

`snapshot.json` is a compact, pinned extract of the public NoBrainer benchmark
(https://nobrainer.tech/ai/benchmark/), built by
`scripts/build-benchmark-snapshot.mjs`. `SOURCE.json` records the source path,
website commit, input hashes and the snapshot hash. The `recommend_flow_model`
tool reads only this file and makes no network calls.

NoBrainer derived these rankings from released third-party data. The source
publishers do not endorse these recommendations. Values were filtered and
transformed; the build script shows every step.

## Included data

| Data | Source | Licence | Notes |
|---|---|---|---|
| Arena ratings (orchestration, instructions, frontend, research, writing) | LMArena leaderboard dataset, https://huggingface.co/datasets/lmarena-ai/leaderboard-dataset | CC BY 4.0 (dataset card licence field `cc-by-4.0`, checked 2026-10-20) | Filtered to current models and reshaped. CC BY 4.0 permits sharing and adaptation, including commercially, with attribution and an indication of changes. |
| Terminal-Bench success rates, costs and times | harbor-framework/terminal-bench and terminal-bench-2-1 released submissions | Apache License 2.0 | Licence copies: `terminal-bench-LICENSE.txt`, `terminal-bench-2-1-LICENSE.txt`. |
| Model catalog, routes and list prices | models.dev, https://models.dev/api.json | MIT (https://github.com/sst/models.dev LICENSE, checked 2026-10-20) | Prices feed the reference-workload cost estimates. |
| Own agent telemetry cost and time | NoBrainer aggregated agent-log metadata | NoBrainer data; no prompts or content | Median seconds and list-price USD per action for a fixed reference task size. |

## Withheld data: Artificial Analysis

The website's coding, orchestration and research tabs also use AA-aligned
scores derived from Artificial Analysis model comparisons. These are **not**
included in this snapshot or in tool responses. For those scores, use
https://nobrainer.tech/ai/benchmark/. Without them, orchestration and research
rank on the Arena cohorts, and coding returns no shortlist; terminal-coding
has Terminal-Bench data.

Reason (terms checked 2026-10-20):

- Artificial Analysis Terms of Use, version 1.0, last revised 2024-04-28,
  https://artificialanalysis.ai/docs/legal/Terms-of-Use.pdf, section 2.1:
  "a non-transferable, non-exclusive, revocable, limited license to use and
  access the Site solely for your own personal, noncommercial use." Section 2.2:
  "you shall not license, sell, rent, lease, transfer, assign, distribute, host,
  or otherwise commercially exploit the Site, whether in whole or in part, or any
  content displayed on the Site".
- Artificial Analysis Data Platform Terms and Conditions, version 1.1, last
  revised 2026-08-19, https://artificialanalysiscdn.com/legal/ProDataPlatformTerms.pdf
  (the API documentation says API use is subject to these terms and the Terms of
  Use). Section 2.3 (all tiers) allows brief citations only if they "do not
  reproduce Data in a structured, tabular, or machine-readable format".
  Section 2.4(c): not "Embed or otherwise make raw Data available through any
  customer-facing product, API, dashboard, or service". Section 2.5: "Customer
  shall not use the Data to develop, operate, or improve any product or service
  made available to third parties whose primary purpose is benchmarking,
  ranking, comparison, competitive intelligence, or model/provider selection
  guidance, without Company's prior written consent."

A model-selection MCP tool that returns machine-readable scores falls within
these restrictions, so the AA-derived cohort stays out unless Artificial
Analysis gives written consent.

Cost and time figures are per-task reference estimates, source-harness
measurements or own telemetry. They are not invoices, quotas or predictions of
accepted task completion.
