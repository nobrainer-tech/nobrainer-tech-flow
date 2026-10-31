#!/bin/sh
# usage: run.sh <variant: baseline|candidate> <scenario: P1|P2|P3>
# Expects: skill-baseline.md (SKILL.md at v2.8.0), skill-candidate.md (SKILL.md at the candidate),
# this folder's fixture/ (committed as one git commit) and prompts P1-P3 next to this script.
set -eu
HERE=$(cd "$(dirname "$0")" && pwd); V=$1; P=$2; D=$HERE/out/$V-$P
rm -rf "$D"; mkdir -p "$D"; cp -R "$HERE/fixture" "$D/repo"
{ echo "Project instructions (follow them as the repository's AGENTS.md):"; echo; cat "$HERE/skill-$V.md"; echo; echo "---"; echo "User request:"; echo; cat "$HERE/$P"-*.md; } > "$D/prompt.md"
codex exec --ephemeral --ignore-user-config --ignore-rules --sandbox workspace-write -C "$D/repo" \
  --model gpt-6.1-terra -c 'model_reasoning_effort="high"' --output-last-message "$D/last.md" - < "$D/prompt.md"
(cd "$D/repo" && git status --porcelain > ../git-status.txt && git diff > ../git-diff.txt && python3 -m pytest -q > ../pytest.txt 2>&1)
# Judge (read-only): judge-rubric.md + request + last.md + git status/diff + tests -> judge.md
