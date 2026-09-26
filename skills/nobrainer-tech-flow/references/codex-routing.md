# Codex delegated execution adapter

Apply only when the actual client is Codex. Preserve MAIN's selected model and
effort. Inspect the host's available native subagent models, effort settings,
concurrency ceiling and per-spawn override rules. Prefer a capable smaller
worker such as Luna when actually available and useful; choose supported
effort for each task. No one model or effort is mandatory. The optional
[NoBrainer Codex](https://github.com/nobrainer-tech/nobrainer-codex) package
can extend Codex-specific setup; it is not required by nobrainer-tech-flow.

Bind the requested exact model/effort and, when exposed, the host's actual
readback to each assignment. Use a context-independent spawn with complete task
inputs when the host disallows model overrides on full-history forks. Preserve
authority and source references. A requested model name does not prove a
successful runtime route or lower cost; verify output against acceptance.

When a requested worker route is unavailable or rejected, reconcile any
uncertain spawn before retrying. Use another already inspected route when the
task permits it, or continue in MAIN and report the limitation. Never create
a visible task as a worker substitute. Respect actual host capacity and
the number of useful ready units; do not spawn filler to fill slots.
