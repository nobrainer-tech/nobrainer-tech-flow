# Benchmark routing prior with local learning

Use this when the owner wants ready-made worker routing, or asks to refresh or
apply it. NoBrainer.Tech publishes precomputed routing setups at
`https://nobrainer.tech/benchmark/routing/v1/`, one file per set of reachable
plans. The setup is a prior from public benchmark data. Local learning may only
re-order it from this project's verified outcomes. It is not a universal
ranking, it is not proof that a model can be called here, and it never replaces
the capability audit in [SKILL.md](../SKILL.md).

Hard limits:

- MAIN keeps the model and effort the user selected. The setup's `main` picks
  are advice to show the user, never an automatic change.
- Route a job only to a model in that job's `candidates` (or the setup's
  `jobs.bulk` pick for cheap bulk work). Learning never adds a model.
- Never use a model the user excluded, even if it has the best record.
- Never invent or hand-edit a setup. With no usable setup, keep the current
  routing and report `UNKNOWN`. A setup with `empty: true` is no
  recommendation: keep the current routing and never write a block.

The helper is `scripts/benchmark_routing.py` (Python 3.11+, standard library
only). Run it from the project directory, with `<skill-dir>` as this skill's
directory. Its state lives in the project's `.nobrainer/` folder. Keep
`routing-cache/` out of version control, and ask the owner before committing
the ledger or policy. Without Python or network access and with no cached
setup, keep the current routing and report `UNKNOWN`.

## 1. Work out the reachable routes

| Route | Plan | Router id prefix |
|---|---|---|
| `openai` | ChatGPT / Codex | `openai/` |
| `anthropic` | Claude | `anthropic/` |
| `zai` | Z.AI Coding Plan | `zai/` |
| `kimi` | Kimi Code | `kimi/` |
| `minimax` | MiniMax Token Plan | `minimax/` |
| `copilot` | GitHub Copilot | `github-copilot/` |
| `zen` | OpenCode Zen | `opencode-zen/` |

A route counts only when this client can actually request at least one model on
it (`CALLABLE` in the capability audit), ideally `VERIFIED` by an ordinary
successful call. A plan the user pays for, a model catalog or a configured
provider is not enough. For example, Codex natively reaches `openai`, Claude
Code reaches `anthropic` and GitHub Copilot reaches `copilot`. OpenCode, or a
local router in front of any client, can reach more, but only the providers it
is actually signed in to.

Set `--fast` only when the owner says time per task matters, and `--budget`
only for a small budget. Otherwise leave both off.

```sh
python3 <skill-dir>/scripts/benchmark_routing.py key --routes openai,anthropic
# openai-anthropic.f0.b0
```

## 2. Fetch the setup

```sh
python3 <skill-dir>/scripts/benchmark_routing.py fetch --routes openai,anthropic
python3 <skill-dir>/scripts/benchmark_routing.py fetch --routes openai,anthropic --force    # on request
python3 <skill-dir>/scripts/benchmark_routing.py fetch --routes openai,anthropic --offline  # cache only
```

`fetch` calls the network at most once per local day unless forced. It sends
`If-None-Match` and checks the file's sha256 against the manifest when the
manifest was fetched. It keeps the last good copy per key and never caches a
file that fails the check. Report its result as it is:

- `UPDATED`, `NOT_MODIFIED`, `CACHED_TODAY`: usable. `integrity` is `VERIFIED`
  when the manifest hash matched and `UNVERIFIED` when no manifest was reachable.
- `CACHED_OFFLINE`, `CACHED_AFTER_ERROR`: the last good copy is used and
  `reason` says why. A `SHA_MISMATCH` is never used.
- `stale: true`: past `expiresAt`. The setup is still usable, but report it as
  stale; a refresh is due.
- `UNKNOWN` (exit 3): no usable copy for this key. Keep the current routing.
- `routing: NO_RECOMMENDATION` (exit 3): the setup is valid but `empty`, because
  nothing reachable fits the limits. Keep the current routing.

Exit 3 always means keep the current routing; `routing` says why.

## 3. Read a setup

- `id` is the router id. On the `openai` route it may have no prefix (a
  Codex-native model). Codex and Claude Code natively use ids without the
  `openai/` or `anthropic/` prefix. Other apps list their own ids, so match
  those by `family` and `route`.
- `effort` is the reasoning level (`none`, `minimal`, `low`, `medium`, `high`,
  `xhigh`, `max`) or `null`. `score`, `costPerTask` and
  `timePerTask` are benchmark measurements, not measurements from this client.
  Missing values stay `UNMEASURED`.
- `ifNotAvailable` is the previous version of the same model. Use it only when
  the newer one cannot be called.
- A `null` pick means nothing reachable fits. Keep the current routing for that
  job. When `empty` is `true`, every pick is `null`, `subagents` is empty and
  `blocks` is `null`.
- `subagents` is the default worker, then the fallback chain for quota or
  availability errors. The same family can appear twice on different routes;
  those are separate quotas, so the second one is a real fallback.
- `skip` lists families left out and why. An `excludedBy` value (`deprecated`,
  `data`, `cost`, `time`) means the family is out because of its age, missing
  measurements or the chosen limits, not because of its quality.

## 4. Record verified outcomes

After each delegated unit, record one content-free row in
`.nobrainer/routing-ledger.jsonl`. The outcome comes from the verification of
that unit (tests, review or a real run), never from the worker's own report.
Use `unknown` when nothing was verified.

```sh
python3 <skill-dir>/scripts/benchmark_routing.py record --job coding \
  --model openai/<model-id> --route openai --outcome pass --duration 212
python3 <skill-dir>/scripts/benchmark_routing.py record --job research \
  --model <bare-model-id> --route anthropic --outcome unknown --quota-error
```

Jobs: `coding`, `agentic`, `research`, `planning`, `orchestration`, `bulk`. A
row holds only the timestamp, job, model id, route, outcome, duration and a
quota/limit flag. Never put prompts, code, file contents, paths, task titles or
secrets in it. The helper refuses any model value that is not an id.

## 5. Recompute the policy

```sh
python3 <skill-dir>/scripts/benchmark_routing.py policy --routes openai,anthropic
python3 <skill-dir>/scripts/benchmark_routing.py policy --routes openai,anthropic --exclude "<family or id>"
```

`policy` reads only the cached setup and the ledger, with no network, and writes
`.nobrainer/routing-policy.json`. For each job it keeps the setup's candidates,
drops duplicates and excluded models, then orders them by the Beta(1, 1)
posterior mean of verified passes and failures. It is a bounded re-ordering,
not an open-ended optimization loop:

- A candidate needs at least `--min-samples` (default 5) pass or fail rows
  before its record counts. Until then it counts as an even chance (0.5), and
  ties keep the benchmark order. With no data, the order is the setup's order.
- `unknown` outcomes and quota or limit errors are not failures. A quota error
  means following the fallback chain, not demoting the model.
- Exclusions are kept in the policy file; `--clear-excludes` resets them.
- `order: LEARNED` marks a job whose order moved away from the benchmark order.
- For an `empty` setup the policy says `recommendation: NONE`, lists no
  candidates and exits 3. It still writes the file, so an older policy for the
  same key is not used by mistake.

When it freezes `MODEL_POLICY` for a delegated unit, nobrainer-tech-flow reads
the policy without network access. It takes the first candidate for the unit's
job that this client can call, and records `MODEL_REQUESTED` and
`MODEL_ACTUAL`. `nobrainer-dispatcher` carries that frozen policy and never
picks a model itself. If the policy is missing, lists no candidates for the
job, or its `key` differs from the current reachable routes, refresh it or keep
the current routing.

## 6. Write the routing block into an instruction file

Each setup carries the routing section in three `blocks`, wrapped in
`<!-- nobrainer-routing:start -->` and `<!-- nobrainer-routing:end -->`:
`router` (router ids, for OpenCode or a local router), `plain` (no ids, for
GitHub Copilot or when ids are unknown) and `bare` (native ids, only for a
setup keyed to `openai` or `anthropic` alone).

```sh
python3 <skill-dir>/scripts/benchmark_routing.py apply --routes openai,anthropic \
  --file <instruction-file> --block router
```

The dry run changes nothing. It finds the existing routing, which is either the
marker block or an unmarked section titled `Model routing for
nobrainer-tech-flow` (or the older `Model routing for NoBrainer.Tech Flow`)
running up to the next heading of the same or a higher level. It prints the
diff, other lines that choose models, and a `PREVIEW_ID`. It refuses to guess
when there are two routing regions or broken markers; the user merges those by
hand first. For an `empty` setup it writes nothing and exits 3.

Show the user the before -> after diff and the other model-choosing lines
(the helper reports those but never edits them). Wait for explicit
confirmation, then run the same command with `--write --confirm <PREVIEW_ID>`.
The write stops if the file or setup changed since the preview. It backs up the
file, replaces the routing once, and reads the file back to check that exactly
one marker block holds the setup's block. Running it again gives `NO_CHANGE`.
Keep this block separate from nobrainer-tech-flow's own managed instruction
block and never nest one inside the other.

## Report

Add these lines to the routing policy:

```text
BENCHMARK_PRIOR: <key> <version> VERIFIED | UNVERIFIED [STALE] | NO_RECOMMENDATION | UNKNOWN
LEARNING: BENCHMARK | LEARNED for <jobs> (<ledger rows>, min <n> samples)
INSTRUCTION_BLOCK: NOT_PROPOSED | PREVIEWED | WRITTEN (backup, readback OK)
```
