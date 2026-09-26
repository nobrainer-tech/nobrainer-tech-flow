# nobrainer-tech-flow naming

This map separates the public product language from compatibility and source
identifiers. It is the canonical naming reference for maintained copy.

| Class | Use | Rule |
| --- | --- | --- |
| Product | nobrainer-tech-flow | Use this exact name in user-facing prose, status, headings and display copy. |
| Public repository/package channel | `nobrainer-tech-flow` | Use in repository links, new checkout paths and public source URLs. |
| Workflow skills | `nobrainer-build`, `nobrainer-research`, `nobrainer-review`, etc. | Name the specific skill when it explains which part of the workflow is doing the work. Preserve its exact lowercase kebab-case name and inline-code formatting. |
| Assistant conversation label | nobrainer-tech-flow | Do not open with a ritual entry announcement; mention the product or a specific skill only when it helps explain an action, constraint or result. |
| X hashtag | `#NoBrainerTechFlow` | Use this punctuation-free form when a real hashtag is useful. A hyphen ends an X hashtag, so never publish `#nobrainer-tech-flow` as the tag. |
| Legacy display name | Former display spellings | Preserve only in historical release evidence and compatibility metadata. Do not use it as the current product name in new prose. |
| Technical entry skill | `nobrainer-tech-flow` | Use for the skill directory, frontmatter name, installer target and `$nobrainer-tech-flow` entrypoint. |
| Retired entry name | `nobrainer-ultra` | Recognize only in migration notes for existing installations. Never direct a new user to invoke it. |
| Active phrases | `NBFlow`, `NBF`, `nobrainer-tech-flow` | Use in natural-language requests. Exact skill loading is `$nobrainer-tech-flow` when the client supports it; do not create alias directories. |
| Retired aliases | `nb-ultra`, `nb-flow`, `nb-workflow` | Preserve only in migration records for older installations. |
| Public package/plugin identity | `nobrainer-tech-flow` | Use in new package manifests, plugin IDs and installation examples. |
| Legacy package identity | `nobrainer-tech-skills` | Preserve only in migration guidance and old adapter module paths; update existing client registrations explicitly. |
| Historical evidence | Prior product/package forms | Keep in dated releases, evaluations, hashes and frozen fixtures when changing them would rewrite provenance. |

## Propagation plan

The canonical source is updated first. Existing repository copies are then
handled through the reviewed synchronization workflow after the source change
is approved:

1. inventory current consumer instruction files before propagation;
2. classify each occurrence as maintained public text, technical identifier or
   historical evidence;
3. update only maintained public text and preserve managed blocks, local rules,
   paths, aliases and technical identifiers;
4. preview exact diffs and require per-repository dirty-state readback;
5. apply through canonical synchronization, then run each repository's nearest
   validator and record any owner-gated or conflicting checkout.

This PR changes the canonical source. Install and personalize clients only
after the owner reviews it; keep live client directories and caches untouched
until the exact reviewed release is available.
