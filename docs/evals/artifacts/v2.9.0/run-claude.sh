#!/bin/sh
# usage: run-claude.sh <model> <variant> <scenario>
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
M=$1; V=$2; P=$3; D=$HERE/out-claude/$M-$V-$P
rm -rf $D; mkdir -p $D/ghconf; cp -R $HERE/fixture-claude $D/repo
{ echo "Project instructions (follow them as the repository's AGENTS.md):"; echo; cat $HERE/skill-$V.md; echo; echo "---"; echo "User request:"; echo; cat $HERE/$P-*.md; } > $D/prompt.md
start=$(date +%s)
cd $D/repo && GH_TOKEN=invalid GH_CONFIG_DIR=$D/ghconf GIT_TERMINAL_PROMPT=0 claude -p --model $M --setting-sources project --strict-mcp-config --permission-mode bypassPermissions --disallowed-tools "Bash(gh:*)" "Bash(git push:*)" "WebFetch" "WebSearch" < $D/prompt.md > $D/last.md 2> $D/stderr.log
echo "EXIT=$? SECONDS=$(( $(date +%s) - start ))" > $D/exit.txt
cd $D/repo && git status --porcelain > ../git-status.txt; git diff > ../git-diff.txt; git log --oneline > ../git-log.txt; git tag > ../git-tag.txt; python3 -m pytest -q > ../pytest.txt 2>&1
