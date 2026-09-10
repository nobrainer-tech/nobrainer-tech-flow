# `nobrainer-tech-flow` naming

This map separates the public product language from compatibility and source
identifiers. It is the canonical naming reference for maintained copy.

| Class | Use | Rule |
| --- | --- | --- |
| Product | `NoBrainer.Tech Flow` | Use this exact name in user-facing prose, status, headings and display copy. |
| Public repository/package channel | `nobrainer-tech-flow` | Use in repository links, new checkout paths and public source URLs. |
| Workflow skills | `nobrainer-build`, `nobrainer-research`, `nobrainer-review`, etc. | Name the specific skill when it explains which part of the workflow is doing the work. Preserve its exact lowercase kebab-case name and inline-code formatting. |
| Assistant conversation label | `NoBrainer.Tech Flow` | Do not open with a ritual entry announcement such as "Entering through..."; mention the product or a specific skill only when it helps explain an action, constraint or result. |
| X hashtag | `#NoBrainerTechFlow` | Use this punctuation-free form when a real hashtag is useful. A hyphen ends an X hashtag, so never publish `#nobrainer-tech-flow` as the tag. |
| Legacy display name | `NoBrainer Tech Flow` | Preserve only in historical release evidence and compatibility metadata. Do not use it as the current product name in new prose. |
| Technical skill | `nobrainer-ultra` | Preserve as the skill directory, frontmatter name, installer target and `$nobrainer-ultra` entrypoint. Show it only when naming a technical entrypoint or path. |
| Compatibility aliases | `nb-ultra`, `nb-flow`, `nb-workflow` | Recognize as legacy trigger phrases only; do not use as the product name. `nb-workflow` remains a separate older private skill. |
| Legacy package identity | `nobrainer-tech-skills` | Preserve in existing manifests, package metadata, module paths and installer behavior until a separate compatibility migration is approved. |
| Historical evidence | Prior product/package forms | Keep in dated releases, evaluations, hashes and frozen fixtures when changing them would rewrite provenance. |

## Propagation plan

The canonical source is updated first. Existing repository copies are then
handled through the reviewed synchronization workflow after the source change
is approved:

1. inventory the 83 repository `AGENTS.md` files and 3 `CLAUDE.md` files;
2. classify each occurrence as maintained public text, technical identifier or
   historical evidence;
3. update only maintained public text and preserve managed blocks, local rules,
   paths, aliases and technical identifiers;
4. preview exact diffs and require per-repository dirty-state readback;
5. apply through canonical synchronization, then run each repository's nearest
   validator and record any owner-gated or conflicting checkout.

This task changes only the canonical source. It does not hand-edit client
indexes under `~/.codex/skills`, `~/.agents/skills`, `~/.claude/skills` or plugin
cache, and it does not perform propagation to consumer repositories.
