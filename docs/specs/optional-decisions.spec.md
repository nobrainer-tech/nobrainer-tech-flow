# Optional typed decisions

Status: implementation contract, not runtime support proof.

## Outcome

Keep all seventeen Flow skills usable with one host-selected model. Offer Jev
remote and Laya local typed decisions as optional execution profiles in the same
release, with an explicit remembered preference and a complete core fallback.

## Acceptance

- AC01: With no configuration, no provider is called and ordinary work proceeds.
  During explicit setup offer core, Jev or Laya once. Persist a decline as core.
  Unattended setup defaults to core without waiting for input.
- AC02: Store non-secret project preferences in `.nobrainer/flow.json` with
  schema version, decision provider, mode, model, timeout and per-run call limit.
  Secrets are environment references, never values in the configuration.
  Explicit configuration changes replace the remembered choice. Installation,
  upgrade and new tasks do not re-open the question.
- AC03: Modes are off and shadow initially. Only explicitly enabled shadow
  requests send approved state. Provider output is advisory; MAIN/code owns
  execution, evidence, permission and completion. No automatic provider switching.
- AC04: Invalid configuration, missing credentials, unavailable local runtime,
  timeout, HTTP failure or invalid typed answers returns a bounded fallback
  reason. Core work continues. No retries by default; no hidden model download.
- AC05: Each call records provider/model, elapsed time, status and budget use
  without credentials or raw private state. Validate question IDs, types, finite
  ranges and distributions before accepting a suggestion. Scores cannot
  authorize tools or promote Autoimprove candidates.
- AC06: A pure Python stdlib core helper is optional. Hosts without process
  execution follow the same Markdown contract and use their main model. Laya's
  platform/dependency requirements are detected and honestly reported; universal
  workflow support does not mean universal local inference support.
- AC07: Test fresh/remembered/changed settings, off mode with a network trap,
  failure fallback, malformed outputs and exhausted budgets. Verify approved
  synthetic Jev/Laya calls separately from mocked failure-path tests.

## Implementation and proof scope

Use existing Ultra setup/routing owners, a focused reference and helper under
Ultra, and meaningful contract tests. Keep public Flow independent of private
skills and machine paths. Update compatibility/install docs and release site
with exact supported and unverified layers. Retain core as rollback.

The existing private Jev client and Laya smoke are implementation references,
not portable acceptance proof. The earlier eight-case comparison had subjective
urgency labels and measured local inference versus API-plus-wrapper time; it
does not prove generalized quality, calibration or a speed ratio.

Version 1.14.0 is a candidate until remote release and website readback complete.
