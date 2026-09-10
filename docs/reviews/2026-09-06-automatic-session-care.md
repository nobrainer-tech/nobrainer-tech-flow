# Automatic session care review

The owner clarified that the primary objective is manageable context and seamless
continuation, with the session creation date visible immediately. Economic
payback is a secondary qualification, not a mandatory veto on context health.

## Verified baseline findings

- The restart gate rejected pressure-driven rotation without economic estimates.
- Explicit Flow entry did not invoke startup naming or context assessment.
- A committed transfer could return FINISH/CHECKPOINT_ONLY before takeover checks
  if remaining work, consent or policy changed.

The added regressions reproduced the first and third findings against the old
helper. The revised helper resolves both, retains transfer checks, and accepts a
current pressure signal with materially smaller complete startup independently
of billing estimates. A separate title formatter preserves actual creation time,
timezone and idempotent suffix replacement; it never mutates sessions itself.
Ultra and the shared bootstrap now invoke the protocol at explicit Flow entry.

## Evidence and boundaries

All 162 tests and both repository validators passed.
Independent read-only review found no remaining actionable helper/protocol defect.
The actual Claude and Cursor SessionStart scripts emit the revised routing.
Native title readback in the current desktop client confirmed a dated current
conversation using its actual creation metadata. Resume and timezone edges are
covered by formatter tests. The active local installation links to these sources.

A full native fresh-conversation takeover was not executed. No bundled adapter
collects all host telemetry or implements ownership transfer. Agents use available
native tools; a host without trustworthy transfer stays in manual handoff mode.
Thus helper/hook proof is not end-to-end automatic-continuation proof. No global
hook, daemon, public release or website deployment was added by this change.

Full-directory secret scanning matched existing synthetic credential fixtures in
ignored compiled test caches. Scanning the complete changed text and new files
found no secrets. These cache findings are not new source credentials.

Rollback: revert only this task's scoped working-tree patch to the v1.8.1 baseline;
leave unrelated work intact. The cosmetic current-chat rename can be reversed
independently without changing task ownership.

## Source cross-check

The official [Claude hooks reference](https://code.claude.com/docs/en/hooks)
distinguishes startup, resume, clear and compact events and documents injection
of additional context. This supports reusing the existing bootstrap hook, not
claiming a hook performs the native transfer itself.
The official [OpenAI skill creator](https://github.com/openai/skills/blob/main/skills/.system/skill-creator/SKILL.md)
describes progressive disclosure; startup estimation therefore inventories needed
skill bodies and metadata, rather than loading every installed skill.
