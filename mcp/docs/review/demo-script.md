# Demo recording script (OpenAI MCP review)

Goal: one public MP4 for `review.demo_recording_url`, about 4 minutes, 1920 x 1080, English
captions, Day theme, no personal data, no real secrets, no private repositories. Suggested host:
`https://nobrainer.tech/flow/assets/mcp-review-demo.mp4`.

Before recording:

- The server is live at `https://mcp.nobrainer.tech/mcp` and `npm run smoke` passes against it.
- ChatGPT has the server as a custom MCP connection (developer mode) in a clean project with no
  memory. Codex has it in `~/.codex/config.toml`.
- A small public demo repository with a date parser whose `parse('2026-02-30')` does not raise yet.
- Browser zoom so tool-call cards are readable; notifications off.

| Time | Scene | What to show and say (caption) |
|---|---|---|
| 0:00-0:20 | Title card | "NoBrainer Tech Flow: one task contract and one done gate for AI agents. Stores nothing, runs no AI model." |
| 0:20-1:00 | P1 Start a contract | Paste the P1 prompt from `test-cases.md`. Expand the `start_flow_task` card: path `QUICK`, items `AC01` (test, local) and `AC02` (file, static), the `DRIFT_CHECK` rules and the token. Caption: "The definition of done gets IDs and a required kind and level of proof." |
| 1:00-1:30 | P2 Blocked | Paste the P2 prompt. Show `get_flow_step` with event `blocked`, its rules and the source file in the Flow release. Caption: "Guidance is quoted from the pinned Flow release, a few rules at a time." |
| 1:30-2:20 | P3 False claim | Paste failing pytest output ending `1 failed, 4 passed` and say the tests pass. Show `FAILED`, then the second record `REJECTED` with `COUNTS_MISMATCH`. Caption: "The server checks the runner summary, not the claim." |
| 2:20-2:50 | P4 Done gate | Paste passing output for AC01 and ask "Is the task done?". Show `NOT_DONE` with AC02 missing and no receipt. |
| 2:50-3:20 | P4 Gaps and handoff | "Mark AC02 as not checked: no access to the changelog. Then write the handoff." Show `DONE_WITH_GAPS` and the handoff with AC01 proof and AC02 under "Not checked", and the closing line "the server checked consistency, not truth". |
| 3:20-3:40 | P5 Model advice | "I use Codex. Which model should I use for a coding task?" Show the top-3 shortlist with quality, cost and time, the snapshot date and the benchmark URL. |
| 3:40-4:00 | Codex continuity | In Codex, in the demo repository, ask it to read `CONTRACT_TOKEN` from the goal file and call `check_flow_done`. Same verdict as in ChatGPT. Caption: "The same contract continues in another client." |
| 4:00-4:20 | N1-N3 | Ask the three negative prompts. Show direct answers with no Flow tool call; for "Deploy my app" the model says the plugin does not deploy. |
| 4:20-4:30 | End card | Privacy and terms URLs, repository URL. |

Notes:

- Record each scene in one take; cut only between scenes. Do not edit tool outputs.
- If a model does not call the expected tool in a take, record again; do not stage the output.
- Keep the token visible but do not zoom on it; it holds no user data.
