# Codex delegated execution preset

Apply only when the actual client is Codex and native delegation supports explicit
model selection. For bounded delegated execution, use `gpt-5.6-luna` with reasoning
`max`, regardless of MAIN's selected model. This default covers research,
implementation, testing and review assignments; an explicit owner override wins.
MAIN retains its selected model and integration responsibility. Do not rewrite
user config or claim to switch an already-running MAIN.

Bind `ROUTED`, the requested model/effort and the host's actual model readback to
each assignment. Use a context-independent spawn with complete task inputs when
the host disallows model overrides on full-history forks. Preserve authority and
required source references. Model naming alone does not prove lower price or
adequate quality; verify the assigned result against acceptance.

When Luna/max is unavailable or the host rejects the requested configuration,
reconcile any uncertain spawn before retrying. Execute in MAIN where allowed and
report the degraded mode once; do not silently substitute another worker model,
reduce effort, install a CLI or create visible tasks. The global cap of 15 active
subagents still applies. Other clients use their own supported policy; this
preset makes no cross-client or cross-provider claim.
