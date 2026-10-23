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

## Snapshot scope

The public benchmark fetched on 2026-10-23 contains no Artificial Analysis data.
This snapshot includes only its published Arena and Terminal-Bench quality
measurements, model catalog metadata and aggregated telemetry. The legacy task
`coding` (case-insensitive) maps to `terminal-coding`, as on the website; it is
not a separate task or score cohort.

Cost and time figures are per-task reference estimates, source-harness
measurements or own telemetry. They are not invoices, quotas or predictions of
accepted task completion.
