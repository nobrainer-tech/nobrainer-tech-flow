#!/bin/sh
# Install, preview or undo nobrainer-tech-flow for one client, without Python.
#
# Same flags, locations, conflict rule and setup record as scripts/install.py, so
# either one can undo what the other did. Every run previews until --apply. The
# skills are linked to this checkout (never copied), one managed instruction block
# is added, and no standing authorization is ever granted. One difference: a managed
# block that is already there is left exactly as it is (install.py rewrites it to the
# current text and keeps its options).
#
# POSIX sh: dash, bash, busybox and zsh emulating sh. On Windows run it in Git Bash.

set -u

# The eighteen skills, and the names earlier layouts used. Tests keep both lists
# equal to the ones in scripts/install_skills.py.
SKILLS='nobrainer-auto-fine-tune nobrainer-autoimprove nobrainer-browser nobrainer-build
nobrainer-codex-context nobrainer-decide nobrainer-dispatcher nobrainer-rca
nobrainer-research nobrainer-review nobrainer-security nobrainer-sessions
nobrainer-skill-doctor nobrainer-spec-driven-development nobrainer-team
nobrainer-tech-flow nobrainer-wiki nobrainer-writing'
LEGACY='add-gitleaks agent-browser agents-restraint code-autoresearch codex-in-claude-code
deep-audit deep-autoresearch deep-autoreview deep-bugs-finder deep-code-review
deep-decide deep-rca dispatching-parallel-agents engineering-standards
karpathy-auto-improver karpathy-llm-wiki llm-wiki nb-add nb-dispatcher nb-flow nb-get
nb-multi nb-tidy nb-workflow nb-write nobrainer-autopilot nobrainer-capture-lesson
nobrainer-continuous-improvement nobrainer-fast-audit nobrainer-human-like
nobrainer-memory nobrainer-memory-memsearch nobrainer-npm-secure nobrainer-reddit
nobrainer-simplifier nobrainer-skill-browser nobrainer-starter nobrainer-style
nobrainer-team-builder nobrainer-ultra nobrainer-ultracode-workflow nobrainer-wiki-add
nobrainer-wiki-get nobrainer-wiki-tidy playwright-cli security-review session-handoff
wiki-add wiki-get wiki-tidy'
START='<!-- NOBRAINER-TECH-FLOW:START -->'
END='<!-- NOBRAINER-TECH-FLOW:END -->'
LEGACY_TEXT='(^|[^[:alnum:]_])nobrainer-ultra([^[:alnum:]_]|$)|^[[:space:]]*#{1,6}[[:space:]]+nobrainer([ .]?tech)?[[:space:]]+flow([^[:alnum:]_]|$)'
CONTROL=$(printf '*[\001-\037\177]*')
TAB=$(printf '\t')

# The block scripts/install_personalization.py writes without options, byte for byte
# (a test compares them).
block() {
	cat <<'EOF'
<!-- NOBRAINER-TECH-FLOW:START -->
## nobrainer-tech-flow

- Use `nobrainer-tech-flow` (`$nobrainer-tech-flow`) as the task entrypoint when this client supports skill invocation. If unavailable, check the documented installation path and report that limitation honestly.
- On first setup, load `nobrainer-auto-fine-tune` for a read-only capability audit; preserve MAIN model and effort, and mark unverified runtime values `UNKNOWN`.
- Preserve the user's selected MAIN model and effort. Inspect the host's actual subagent models, capabilities, and concurrency; delegate independent work when it improves speed or quality, choosing the smallest capable available workers. Never assume a model is available or silently substitute one.
- Split substantial work into bounded tasks with clear outputs, exclusive write scope, dependencies, and verification. Keep integration and acceptance in MAIN; avoid duplicate or filler tasks.
- Derive short-term goals from the user's long-term direction (LDD) and define observable completion criteria. At project start, inspect the existing structure and layers, then recommend a fitting approach.
- At project start, discover whether a relevant wiki exists. If one exists, read its `WIKI.md`, locate relevant `index.md` entries with a targeted search, then read only the relevant pages. Ask before creating a wiki unless project rules or prior authorization already settle it.
- Assess context and checkpoint at appropriate milestones. Recommend session rotation when it would help; do not restart or archive automatically. When rotation is authorized, use the supported lifecycle, verify exact successor takeover by ID/readback, and archive the old session only after that readback. Do not create recursive visible workers or claim a restart when unsupported.
- On the first `nobrainer-tech-flow` use each calendar day, check for available updates when this client exposes a supported check and notify the owner; do not apply them automatically. If the client is inactive or cannot check, do not claim a check occurred.
- Use `nobrainer-ak` (`nbak`) for relevant marketing and sales content creation when available. For general writing use `nobrainer-writing` when available; make technical documentation concrete, source-backed, and technically verified. Preserve facts, use the user's language, and verify at the actual delivery layer.
<!-- NOBRAINER-TECH-FLOW:END -->
EOF
}

usage() {
	cat <<'EOF'
usage: sh scripts/install.sh --client {claude,codex,opencode,copilot} [--home DIR] [--apply] [--undo]

Link every nobrainer-tech-flow skill and add the managed instruction block for one
client, without Python. Without --apply this only previews.

  --client  the client to set up: claude, codex, opencode or copilot
  --home    profile home for the documented default locations; when omitted,
            CLAUDE_CONFIG_DIR, CODEX_HOME and XDG_CONFIG_HOME are honoured
  --apply   write the changes; the default is a preview
  --undo    reverse the setup this script, scripts/install.py or the guided
            setup recorded (add --apply to do it)

Subsets, copy installs, the shared agents folder and other clients: docs/INSTALL.md.
EOF
}

say() { printf '%s\n' "$*"; }
err() { printf '%s\n' "$*" >&2; }

# die CODE MESSAGE [HINT]
die() {
	err "ERROR: $2"
	if [ $# -ge 3 ]; then err "HINT: $3"; fi
	exit "$1"
}

usage_error() {
	usage >&2
	err "install.sh: error: $1"
	exit 2
}

reject_control() {
	case $1 in $CONTROL) die 2 "$2 contains a control character" ;; esac
}

# Windows spellings (C:\... under Git Bash or Cygwin) to the POSIX form the shell uses.
to_posix() {
	if [ "$windows" = 1 ]; then
		case $1 in [A-Za-z]:* | *\\*) cygpath -u "$1"; return ;; esac
	fi
	printf '%s\n' "$1"
}

# The spelling the Python scripts read back from the setup record on this system.
to_native() {
	if [ "$windows" = 1 ]; then cygpath -w "$1"; else printf '%s\n' "$1"; fi
}

# clean MODE PATH: drop empty and "." parts of an absolute path, as pathlib does.
# MODE abs also resolves ".." (os.path.abspath); MODE keep leaves it (pathlib).
clean() {
	_c_rest=$2 _c_out=
	while [ -n "$_c_rest" ]; do
		case $_c_rest in
			*/*) _c_part=${_c_rest%%/*} _c_rest=${_c_rest#*/} ;;
			*) _c_part=$_c_rest _c_rest= ;;
		esac
		case $_c_part in
			'' | .) ;;
			..) if [ "$1" = abs ]; then _c_out=${_c_out%/*}; else _c_out=$_c_out/..; fi ;;
			*) _c_out=$_c_out/$_c_part ;;
		esac
	done
	printf '%s\n' "${_c_out:-/}"
}

# physical PATH: resolve the symbolic links in the part of PATH that exists, as
# pathlib's resolve() does, so two spellings of one folder compare equal.
physical() {
	_p_head=$1 _p_tail=
	while [ ! -d "$_p_head" ]; do
		_p_tail=/${_p_head##*/}$_p_tail
		_p_head=${_p_head%/*}
		if [ -z "$_p_head" ]; then
			printf '%s\n' "$1"
			return
		fi
	done
	_p_head=$(cd -P "$_p_head" 2>/dev/null && pwd -P) || _p_head=$1 _p_tail=
	printf '%s%s\n' "${_p_head%/}" "$_p_tail"
}

quote() {
	case $1 in
		'' | *[!A-Za-z0-9_./:=@%+-]*) printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")" ;;
		*) printf '%s' "$1" ;;
	esac
}

# The command that continues this run with more flags, keeping an explicit --home.
command_for() {
	printf 'sh %s --client %s' "$(quote "$here/install.sh")" "$client"
	for _flag in "$@"; do printf ' %s' "$_flag"; done
	if [ "$home_given" = 1 ]; then printf ' --home %s' "$(quote "$home")"; fi
	printf '\n'
}

# config_dir VARIABLE STRICT: set config_value to the directory VARIABLE names, or to
# nothing when it is unset. An empty CODEX_HOME or XDG_CONFIG_HOME counts as unset,
# as it does for Codex and in the XDG specification. Any other value is used exactly
# as written; one that is not absolute (an empty CLAUDE_CONFIG_DIR included) is an
# error when STRICT is yes: the client resolves it against its own working
# directory, and this script cannot know which one that is.
config_dir() {
	eval "_d_set=\${$1+set} _d_value=\${$1-}"
	config_value=
	if [ -z "$_d_set" ]; then return 0; fi
	if [ -z "$_d_value" ] && [ "$1" != CLAUDE_CONFIG_DIR ]; then return 0; fi
	reject_control "$_d_value" "$1"
	_d_path=$(to_posix "$_d_value")
	case $_d_path in
		/*) config_value=$(clean keep "$_d_path") ;;
		*) if [ "$2" = yes ]; then die 2 "$1 must be an absolute path, not '$_d_value'"; fi ;;
	esac
}

# locate CLIENT MODE: set skills_dir, target and label. MODE env honours the variable
# the client reads, plain uses the documented defaults under $home, and lenient
# honours the variable but falls back to the default when it is unusable.
locate() {
	_l_base=
	case $1 in
		claude) _l_var=CLAUDE_CONFIG_DIR ;;
		codex) _l_var=CODEX_HOME ;;
		opencode) _l_var=XDG_CONFIG_HOME ;;
		*) _l_var= ;;
	esac
	if [ -n "$_l_var" ] && [ "$2" != plain ]; then
		if [ "$2" = env ]; then config_dir "$_l_var" yes; else config_dir "$_l_var" no; fi
		_l_base=$config_value
	fi
	case $1 in
		claude)
			_l_base=${_l_base:-$home/.claude}
			skills_dir=$_l_base/skills target=$_l_base/CLAUDE.md label='Claude Code' ;;
		codex)
			skills_dir=$home/.agents/skills
			target=${_l_base:-$home/.codex}/AGENTS.md label=Codex ;;
		opencode)
			_l_base=${_l_base:-$home/.config}
			skills_dir=$_l_base/opencode/skills target=$_l_base/opencode/AGENTS.md label=OpenCode ;;
		copilot)
			skills_dir=$home/.copilot/skills
			target=$home/.copilot/copilot-instructions.md label='GitHub Copilot CLI' ;;
	esac
}

# Whether the Claude file is nothing but an @ import of the Codex global file that
# already holds the block. Only that form counts: whether an import inside a longer
# Markdown file is live depends on how Claude Code parses the whole file, and a
# second copy of the block is harmless where a missing one is not.
inherits_codex() {
	[ "$client" = claude ] && [ "$file_status" != create ] || return 1
	if [ "$home_given" = 1 ]; then _h_mode=plain; else _h_mode=lenient; fi
	_h_skills=$skills_dir _h_target=$target _h_label=$label
	locate codex "$_h_mode"
	codex_file=$(clean keep "$target")
	skills_dir=$_h_skills target=$_h_target label=$_h_label
	_h_lines=$(tr '\r' '\n' <"$target" | grep -v "^[ $TAB]*\$")
	case $_h_lines in *"
"*) return 1 ;; esac
	_h_line=$(printf '%s\n' "$_h_lines" | sed "s/[ $TAB]*\$//")
	case $codex_file in
		"$home"/*) _h_short="@~/${codex_file#"$home"/}" ;;
		*) _h_short= ;;
	esac
	[ "$_h_line" = "@$codex_file" ] || { [ -n "$_h_short" ] && [ "$_h_line" = "$_h_short" ]; } || return 1
	grep -q -F -e "$START" "$codex_file" 2>/dev/null && grep -q -F -e "$END" "$codex_file" 2>/dev/null
}

# is_our_link LINK SOURCE: LINK is a symbolic link that resolves to SOURCE.
is_our_link() {
	[ -L "$1" ] || return 1
	_o_resolved=$(cd -P "$1" 2>/dev/null && pwd -P) || return 1
	[ "$_o_resolved" = "$2" ]
}

make_link() {
	# Git Bash and Cygwin copy the tree for "ln -s" unless told to make a real link.
	MSYS=winsymlinks:nativestrict CYGWIN=winsymlinks:nativestrict ln -s "$1" "$2"
}

remove_link() {
	rm -f "$1" 2>/dev/null || rmdir "$1" 2>/dev/null
	[ ! -e "$1" ] && [ ! -L "$1" ]
}

links_work() {
	_w_dir=$(mktemp -d 2>/dev/null) || return 1
	mkdir "$_w_dir/target" && make_link "$_w_dir/target" "$_w_dir/link" 2>/dev/null && [ -L "$_w_dir/link" ]
	_w_status=$?
	rm -rf "$_w_dir"
	return "$_w_status"
}

sha256() {
	if command -v sha256sum >/dev/null 2>&1; then
		sha256sum <"$1" | cut -d ' ' -f 1
	elif command -v shasum >/dev/null 2>&1; then
		shasum -a 256 <"$1" | cut -d ' ' -f 1
	elif command -v openssl >/dev/null 2>&1; then
		openssl dgst -sha256 <"$1" | sed 's/^.*= *//'
	else
		return 1
	fi
}

utf8_ok() {
	if command -v iconv >/dev/null 2>&1; then iconv -f UTF-8 -t UTF-8 "$1" >/dev/null 2>&1; fi
}

# The setup record is the JSON file scripts/install.py and the guided setup write.
# Only its own layout is read: one key per line, strings with \\ and \" escapes.
json_string() {
	printf '"%s"' "$(printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g')"
}

# json_field LINE: set json_value to the string value on LINE; fail on anything else.
json_field() {
	_j_raw=${1#*\": }
	_j_raw=${_j_raw%,}
	case $_j_raw in \"*\") ;; *) return 1 ;; esac
	_j_raw=${_j_raw#\"}
	_j_raw=${_j_raw%\"}
	json_value=
	while :; do
		case $_j_raw in
			*\\*)
				json_value=$json_value${_j_raw%%\\*}
				_j_raw=${_j_raw#*\\}
				case $_j_raw in
					\\*) json_value=$json_value\\ _j_raw=${_j_raw#?} ;;
					\"*) json_value=$json_value\" _j_raw=${_j_raw#?} ;;
					*) return 1 ;;
				esac ;;
			*)
				json_value=$json_value$_j_raw
				return 0 ;;
		esac
	done
}

read_state() {
	st_dest= st_created= st_target= st_backup= st_hash= _r_in=
	while IFS= read -r _r_line || [ -n "$_r_line" ]; do
		case $_r_in in
			skills)
				case $_r_line in
					'  ]' | '  ],') _r_in= ;;
					*)
						json_field "\": ${_r_line#    }" || return 1
						case " $(printf '%s' "$SKILLS" | tr '\n' ' ') " in *" $json_value "*) ;; *) return 1 ;; esac
						case " $st_created " in *" $json_value "*) return 1 ;; esac
						st_created="$st_created $json_value" ;;
				esac
				continue ;;
			profile)
				case $_r_line in
					'  }' | '  },') _r_in= ;;
					'    "target": '*) json_field "$_r_line" || return 1; st_target=$json_value ;;
					'    "backup": null' | '    "backup": null,') st_backup= ;;
					'    "backup": '*) json_field "$_r_line" || return 1; st_backup=$json_value ;;
					'    "written_sha256": '*) json_field "$_r_line" || return 1; st_hash=$json_value ;;
					*) return 1 ;;
				esac
				continue ;;
		esac
		case $_r_line in
			'{' | '}') ;;
			'  "destination": '*) json_field "$_r_line" || return 1; st_dest=$json_value ;;
			'  "created_skills": []' | '  "created_skills": [],') ;;
			'  "created_skills": [') _r_in=skills ;;
			'  "profile": {}' | '  "profile": {},') ;;
			'  "profile": {') _r_in=profile ;;
			*) return 1 ;;
		esac
	done <"$1"
	[ -n "$st_dest" ] && [ -z "$_r_in" ] || return 1
	st_dest=$(to_posix "$st_dest")
	if [ -n "$st_target" ]; then st_target=$(to_posix "$st_target"); fi
	if [ -n "$st_backup" ]; then st_backup=$(to_posix "$st_backup"); fi
	return 0
}

write_state() {
	mkdir -p "$home" || return 1
	_s_tmp=$(mktemp "$home/.nobrainer-flow-onboarding-$client.XXXXXX") || return 1
	{
		printf '{\n  "destination": %s,\n' "$(json_string "$(to_native "$skills_dir")")"
		if [ -z "$new_created" ]; then
			printf '  "created_skills": [],\n'
		else
			printf '  "created_skills": [\n'
			_s_sep=
			for _s_name in $new_created; do
				printf '%s    "%s"' "$_s_sep" "$_s_name"
				_s_sep=',
'
			done
			printf '\n  ],\n'
		fi
		if [ -z "$new_target" ]; then
			printf '  "profile": {}\n'
		else
			printf '  "profile": {\n    "target": %s,\n' "$(json_string "$(to_native "$new_target")")"
			if [ -n "$new_backup" ]; then
				printf '    "backup": %s,\n' "$(json_string "$(to_native "$new_backup")")"
			else
				printf '    "backup": null,\n'
			fi
			printf '    "written_sha256": "%s"\n  }\n' "$new_hash"
		fi
		printf '}\n'
	} >"$_s_tmp" && chmod 600 "$_s_tmp" && mv -f "$_s_tmp" "$state" && return 0
	rm -f "$_s_tmp"
	return 1
}

# Refuse a destination that cannot hold skills before anything is planned.
check_destination() {
	_k_path=$skills_dir
	while :; do
		if [ -e "$_k_path" ]; then
			[ -d "$_k_path" ] || die 2 "destination is not a directory: $_k_path"
			return 0
		fi
		if [ -L "$_k_path" ]; then die 2 "destination is a dangling or looping link: $_k_path"; fi
		_k_parent=${_k_path%/*}
		if [ -z "$_k_parent" ] || [ "$_k_parent" = "$_k_path" ]; then return 0; fi
		_k_path=$_k_parent
	done
}

# The setup already recorded for this client must be for the same places.
check_record() {
	record=0 st_dest= st_created= st_target= st_backup= st_hash=
	if [ ! -e "$state" ] && [ ! -L "$state" ]; then return 0; fi
	if [ -L "$state" ] || [ ! -f "$state" ]; then die 3 "setup state path is not a regular file: $state"; fi
	read_state "$state" || die 3 "cannot read the setup record $state" \
		"it holds characters or a layout this script does not read; undo it with python3 scripts/install.py --client $client --undo --apply"
	record=1
	if [ "$(physical "$st_dest")" != "$(physical "$skills_dir")" ]; then
		die 3 "existing setup state belongs to a different skills destination: $st_dest" \
			"undo that setup with $(command_for --undo --apply), then run this again"
	fi
	if [ -n "$st_target" ] && [ "$(clean keep "$st_target")" != "$(clean keep "$target")" ]; then
		die 3 "existing setup state belongs to a different personalization target: $st_target" \
			"undo that setup with $(command_for --undo --apply), then run this again"
	fi
}

plan_skills() {
	to_link= link_count=0 kept_count=0 problems=
	for _p_name in $SKILLS; do
		_p_source=$root/skills/$_p_name
		[ -f "$_p_source/SKILL.md" ] || die 2 "this checkout is incomplete: $_p_source/SKILL.md is missing"
		_p_target=$skills_dir/$_p_name
		if is_our_link "$_p_target" "$_p_source"; then
			kept_count=$((kept_count + 1))
		elif [ -e "$_p_target" ] || [ -L "$_p_target" ]; then
			problems="$problems
CONFLICT: $_p_name: $_p_source -> $_p_target"
		else
			to_link="$to_link $_p_name"
			link_count=$((link_count + 1))
		fi
	done
	for _p_name in $LEGACY; do
		_p_target=$skills_dir/$_p_name
		if [ -e "$_p_target" ] || [ -L "$_p_target" ]; then
			problems="$problems
LEGACY: $_p_name: $_p_target"
		fi
	done
	if [ -n "$problems" ]; then
		printf '%s\n' "$problems" | sed '1d' >&2
		err "ERROR: refusing to overwrite existing targets"
		case $problems in
			*LEGACY:*) err "HINT: an entry above comes from an earlier layout of these skills; move it away after checking it, or migrate it as docs/MIGRATION_TO_FLOW.md describes." ;;
			*) err "HINT: a target above exists and is not a link to this checkout. Inspect it and move it away if it is yours to remove, or install the other skills one by one with scripts/install_skills.py --skill (docs/INSTALL.md)." ;;
		esac
		exit 3
	fi
	if [ "$link_count" -gt 0 ] && ! links_work; then
		err "ERROR: this machine cannot create symbolic links, which this script needs."
		if [ "$windows" = 1 ]; then
			err "HINT: turn on Developer Mode (Settings > System > For developers) or run Git Bash as administrator, then rerun. To copy the skills instead, see docs/INSTALL.md (Windows)."
		else
			err "HINT: check that $skills_dir can hold symbolic links, or copy the skills as docs/INSTALL.md describes."
		fi
		exit 2
	fi
}

plan_instructions() {
	file_status=
	if [ "$client" = codex ]; then
		_i_override=${target%/*}/AGENTS.override.md
		if [ -f "$_i_override" ] && grep -q '[^[:space:]]' "$_i_override" 2>/dev/null; then
			die 3 "$_i_override takes precedence over AGENTS.md in Codex, so a block written to AGENTS.md would not load" \
				"remove or empty that file and rerun, or write to it on purpose with scripts/install_personalization.py --client codex --path <file>."
		fi
	fi
	if [ -L "$target" ]; then die 3 "target must be a regular non-symlink file: $target"; fi
	if [ ! -e "$target" ]; then
		file_status=create
		return 0
	fi
	[ -f "$target" ] || die 3 "target must be a regular non-symlink file: $target"
	_i_starts=$(grep -c -F -e "$START" "$target" 2>/dev/null)
	_i_ends=$(grep -c -F -e "$END" "$target" 2>/dev/null)
	if [ "${_i_starts:-0}" = 0 ] && [ "${_i_ends:-0}" = 0 ]; then
		if grep -E -i -q -e "$LEGACY_TEXT" "$target" 2>/dev/null; then
			die 3 "unmarked existing nobrainer-tech-flow instructions detected in $target; explicit migration is required before installing a managed block" \
				"see docs/MIGRATION_TO_FLOW.md"
		fi
		utf8_ok "$target" || die 3 "target is not UTF-8 text: $target"
		file_status=append
		return 0
	fi
	_i_first=$(grep -n -F -e "$START" "$target" | cut -d : -f 1)
	_i_last=$(grep -n -F -e "$END" "$target" | cut -d : -f 1)
	if [ "$_i_starts" != 1 ] || [ "$_i_ends" != 1 ] || [ "$_i_first" -gt "$_i_last" ]; then
		die 3 "malformed or duplicated nobrainer-tech-flow managed markers in $target"
	fi
	file_status=present
}

block_is_default() {
	_b_file=$(mktemp) || return 1
	block >"$_b_file"
	awk -v s="$START" -v e="$END" 'index($0, s) { on = 1 } on { print } on && index($0, e) { on = 0 }' "$target" |
		cmp -s - "$_b_file"
	_b_status=$?
	rm -f "$_b_file"
	return "$_b_status"
}

variable_note() {
	if [ "$home_given" = 1 ]; then return 0; fi
	case $client in
		claude) _v_name=CLAUDE_CONFIG_DIR ;;
		codex) _v_name=CODEX_HOME ;;
		opencode) _v_name=XDG_CONFIG_HOME ;;
		*) return 0 ;;
	esac
	eval "_v_value=\${$_v_name-}"
	if [ -n "$_v_value" ]; then say "NOTE: this setup follows $_v_name=$_v_value; keep it set when you undo it."; fi
}

preview() {
	say "$source_line for $label"
	say "SKILLS: $link_count to link into $skills_dir ($kept_count already linked)"
	if [ "$inherit" = 1 ]; then
		say "INHERITS_CODEX: $target imports $codex_file; no duplicate block added"
	else
		say "TARGET: $target"
		if [ "$file_status" = present ]; then
			say "PRESENT: the managed block is already there and is left as it is"
			if ! block_is_default; then
				say "NOTE: it differs from this version's default block; scripts/install_personalization.py --keep-options updates it and keeps its options"
			fi
		else
			say "MISSING: nobrainer-tech-flow personalization block"
			say "AUTO_UPDATE: CHECK_AND_NOTIFY"
			say "AUTO_SESSION_RESTART: ASSESS_CHECKPOINT_RECOMMEND"
			say "DIFF:"
			block | sed 's/^/+/'
		fi
	fi
	variable_note
	say "NO_CHANGES: preview only; install with: $(command_for --apply)"
}

# Append the block the way scripts/install_personalization.py does: after a line
# break when the file does not end with one, and without a trailing one.
write_instructions() {
	_w_dir=${target%/*}
	mkdir -p "$_w_dir" || return 1
	_w_tmp=$(mktemp "$_w_dir/.${target##*/}.XXXXXX") || return 1
	if [ "$file_status" = append ]; then
		_w_stamp=$(date -u +%Y%m%dT%H%M%SZ)
		made_backup=$target.bak.$_w_stamp
		_w_index=1
		while [ -e "$made_backup" ] || [ -L "$made_backup" ]; do
			made_backup=$target.bak.$_w_stamp.$_w_index
			_w_index=$((_w_index + 1))
		done
		if ! cp -p "$target" "$made_backup" || ! cp -p "$target" "$_w_tmp"; then
			rm -f "$_w_tmp"
			return 1
		fi
		case $(tail -c 1 "$_w_tmp" | od -An -to1 | tr -d ' \n') in
			'' | 012 | 015) ;;
			*) printf '\n' >>"$_w_tmp" ;;
		esac
	fi
	if printf '%s' "$(block)" >>"$_w_tmp" && mv -f "$_w_tmp" "$target"; then return 0; fi
	rm -f "$_w_tmp"
	return 1
}

install() {
	plan_skills
	plan_instructions
	check_record
	inherit=0
	if inherits_codex; then inherit=1; fi
	if [ "$apply" = 0 ]; then
		preview
		return 0
	fi
	sha256 /dev/null >/dev/null || die 2 "this script needs sha256sum, shasum or openssl to record the setup"

	created=
	if [ "$link_count" -gt 0 ]; then mkdir -p "$skills_dir" || die 2 "cannot create $skills_dir"; fi
	for _a_name in $to_link; do
		_a_target=$skills_dir/$_a_name
		_a_source=$root/skills/$_a_name
		if [ ! -e "$_a_target" ] && [ ! -L "$_a_target" ] &&
			make_link "$_a_source" "$_a_target" 2>/dev/null && is_our_link "$_a_target" "$_a_source"; then
			created="$created $_a_name"
			continue
		fi
		# A directory that appeared since the plan would have received the link inside it.
		if is_our_link "$_a_target/$_a_name" "$_a_source"; then remove_link "$_a_target/$_a_name"; fi
		for _a_done in $created; do remove_link "$skills_dir/$_a_done"; done
		if [ "$windows" = 1 ]; then
			err "HINT: turn on Developer Mode (Settings > System > For developers) or run Git Bash as administrator, then rerun."
		fi
		die 4 "could not link $_a_name into $skills_dir; the links made by this run were removed"
	done

	made_backup= wrote=0
	if [ "$file_status" != present ] && [ "$inherit" = 0 ]; then
		if ! write_instructions; then
			for _a_done in $created; do remove_link "$skills_dir/$_a_done"; done
			die 4 "could not write $target; the links made by this run were removed"
		fi
		wrote=1
	fi

	# Undo puts the block back as it was before the first setup, so a record that
	# already names this file keeps its first backup (or its absence).
	new_target= new_backup= new_hash=
	if [ "$record" = 1 ] && [ -n "$st_target" ] && [ -e "$target" ]; then
		new_target=$target new_backup=$st_backup new_hash=$(sha256 "$target")
	elif [ "$wrote" = 1 ]; then
		new_target=$target new_backup=$made_backup new_hash=$(sha256 "$target")
	fi
	if [ -n "$created" ] || [ "$wrote" = 1 ] || { [ "$record" = 1 ] && [ "$new_hash" != "$st_hash" ]; }; then
		new_created=$(printf '%s\n' $st_created $created | sort -u | tr '\n' ' ')
		new_created=${new_created# }
		new_created=${new_created% }
		if ! write_state; then
			for _a_done in $created; do remove_link "$skills_dir/$_a_done"; done
			if [ "$wrote" = 1 ]; then
				if [ -n "$made_backup" ]; then cp -p "$made_backup" "$target"; else rm -f "$target"; fi
			fi
			die 4 "could not save the setup record $state; the changes of this run were reversed"
		fi
	fi

	say "INSTALLED: $source_line for $label"
	say "SKILLS: $((link_count + kept_count)) linked in $skills_dir ($link_count new)"
	if [ "$inherit" = 1 ]; then
		say "INSTRUCTIONS: inherited from the Codex global instructions; nothing written here"
	elif [ "$wrote" = 1 ] && [ -n "$made_backup" ]; then
		say "INSTRUCTIONS: $target (backup: $made_backup)"
	elif [ "$wrote" = 1 ]; then
		say "INSTRUCTIONS: $target"
	else
		say "INSTRUCTIONS: $target already has the managed block; left as it is"
	fi
	if [ -e "$state" ]; then
		say "UNDO: $(command_for --undo --apply)"
	else
		say "UNDO: nothing was changed, so there is nothing to undo"
	fi
	variable_note
	say "NEXT: restart $label, then give it one small task with a checkable result (docs/TRY_IT.md)."
}

# The managed block must stand on lines of its own for the line-based undo below.
block_on_own_lines() {
	[ "$(grep -c -x -F -e "$START" -e "$START$(printf '\r')" "$1")" = 1 ] &&
		[ "$(grep -c -x -F -e "$END" -e "$END$(printf '\r')" "$1")" = 1 ]
}

# restore_into CURRENT BACKUP OUT: CURRENT with its managed block replaced by the one
# BACKUP held, or removed when BACKUP had none. Everything outside the block stays as
# it is now; when nothing else changed, OUT is BACKUP byte for byte.
restore_into() {
	{
		awk -v s="$START" 'index($0, s) { exit } { print }' "$1"
		if [ -n "$2" ]; then
			awk -v s="$START" -v e="$END" 'index($0, s) { on = 1 } on { print } on && index($0, e) { exit }' "$2"
		fi
		awk -v e="$END" 'after { print } index($0, e) { after = 1 }' "$1"
	} >"$3" || return 1
	if [ -n "$2" ] && { cat "$2"; printf '\n'; } | cmp -s - "$3"; then
		# The setup added one line break before the block, and it goes too.
		cat "$2" >"$3"
	fi
}

undo() {
	if [ ! -e "$state" ] && [ ! -L "$state" ]; then
		if [ -e "$home/.nobrainer-flow-onboarding.json" ]; then
			die 3 "only an older setup record exists: $home/.nobrainer-flow-onboarding.json" \
				"undo it with python3 scripts/install.py --client $client --undo --apply, which can tell which client it belongs to."
		fi
		die 3 "rollback state not found: $state" \
			"undo reverses a setup that this script, scripts/install.py or the guided setup recorded; none is recorded for $label."
	fi
	if [ -L "$state" ] || [ ! -f "$state" ]; then die 3 "rollback state must be a regular file: $state"; fi
	read_state "$state" || die 3 "cannot read the setup record $state" \
		"it holds characters or a layout this script does not read; undo it with python3 scripts/install.py --client $client --undo --apply"

	if [ -n "$st_target" ]; then
		# The record may only name a documented instruction file of this home.
		_u_saved_skills=$skills_dir _u_saved_target=$target _u_saved_label=$label
		_u_allowed=0
		for _u_client in claude codex opencode copilot; do
			for _u_mode in lenient plain; do
				if [ "$home_given" = 1 ] && [ "$_u_mode" = lenient ]; then continue; fi
				locate "$_u_client" "$_u_mode"
				if [ "$(clean keep "$target")" = "$(clean keep "$st_target")" ]; then _u_allowed=1; fi
			done
		done
		skills_dir=$_u_saved_skills target=$_u_saved_target label=$_u_saved_label
		[ "$_u_allowed" = 1 ] || die 3 "refusing unexpected personalization target: $st_target"
		case $st_hash in
			*[!0-9a-f]* | '') die 3 "invalid personalization readback hash in rollback state" ;;
		esac
		[ "${#st_hash}" = 64 ] || die 3 "invalid personalization readback hash in rollback state"
		if [ -n "$st_backup" ]; then
			case $st_backup in
				"$st_target".bak.*) ;;
				*) die 3 "refusing unexpected personalization backup: $st_backup" ;;
			esac
			case ${st_backup#"$st_target".bak.} in */*) die 3 "refusing unexpected personalization backup: $st_backup" ;; esac
			if [ -L "$st_backup" ] || [ ! -f "$st_backup" ]; then
				die 3 "personalization backup must be a regular file: $st_backup"
			fi
			if [ ! -e "$st_target" ]; then
				say "PRESERVED: personalization target is missing: $st_target"
				exit 3
			fi
		fi
		if [ -e "$st_target" ]; then
			sha256 /dev/null >/dev/null || die 2 "this script needs sha256sum, shasum or openssl to check the setup"
			if [ "$(sha256 "$st_target")" != "$st_hash" ]; then
				say "PRESERVED: personalization changed since setup: $st_target"
				exit 3
			fi
			if ! block_on_own_lines "$st_target" || { [ -n "$st_backup" ] && grep -q -F -e "$START" "$st_backup" && ! block_on_own_lines "$st_backup"; }; then
				die 3 "the managed block in $st_target does not stand on lines of its own" \
					"undo it with python3 scripts/install.py --client $client --undo --apply"
			fi
		fi
	fi
	for _u_name in $st_created; do
		_u_link=$st_dest/$_u_name
		if [ -L "$_u_link" ]; then
			if ! is_our_link "$_u_link" "$root/skills/$_u_name"; then
				say "PRESERVED: changed target $_u_link"
				exit 3
			fi
		elif [ -e "$_u_link" ]; then
			say "PRESERVED: changed target $_u_link"
			exit 3
		fi
	done

	_u_count=0
	for _u_name in $st_created; do _u_count=$((_u_count + 1)); done
	if [ "$apply" = 0 ]; then
		say "UNDO_PLAN: unlink $_u_count skills from $st_dest"
		if [ -n "$st_target" ] && [ -n "$st_backup" ]; then
			say "INSTRUCTIONS: $st_target: put the managed block back as it was before the setup (from $st_backup); later edits outside the block stay"
		elif [ -n "$st_target" ]; then
			say "INSTRUCTIONS: $st_target: remove the managed block"
		fi
		variable_note
		say "NO_CHANGES: preview only; undo with: $(command_for --undo --apply)"
		return 0
	fi

	_u_removed=0
	for _u_name in $st_created; do
		_u_link=$st_dest/$_u_name
		if is_our_link "$_u_link" "$root/skills/$_u_name"; then
			remove_link "$_u_link" || die 4 "could not remove $_u_link"
			_u_removed=$((_u_removed + 1))
		fi
	done
	_u_result=
	if [ -n "$st_target" ] && [ -e "$st_target" ]; then
		_u_tmp=$(mktemp "${st_target%/*}/.${st_target##*/}.XXXXXX") || die 4 "cannot write next to $st_target"
		cp -p "$st_target" "$_u_tmp" && restore_into "$st_target" "$st_backup" "$_u_tmp" ||
			{ rm -f "$_u_tmp"; die 4 "cannot write next to $st_target"; }
		if [ -z "$st_backup" ] && ! grep -q '[^[:space:]]' "$_u_tmp"; then
			rm -f "$_u_tmp" "$st_target"
			_u_result="INSTRUCTIONS: $st_target removed; the setup had created it"
		else
			mv -f "$_u_tmp" "$st_target" || { rm -f "$_u_tmp"; die 4 "cannot write $st_target"; }
			if [ -n "$st_backup" ] && cmp -s "$st_target" "$st_backup"; then
				_u_result="INSTRUCTIONS: $st_target is back as it was before the setup (backup kept: $st_backup)"
			else
				_u_result="INSTRUCTIONS: managed block removed from $st_target; the rest of the file is kept as it is now"
			fi
		fi
	fi
	rm -f "$state"
	rmdir "$st_dest" 2>/dev/null
	say "UNDONE: nobrainer-tech-flow for $label"
	say "SKILLS: $_u_removed unlinked from $st_dest"
	if [ -n "$_u_result" ]; then say "$_u_result"; fi
	say "NEXT: restart $label to drop the skills."
}

# ---------------------------------------------------------------------------------

case $(uname -s 2>/dev/null) in
	MINGW* | MSYS* | CYGWIN*) windows=1 ;;
	*) windows=0 ;;
esac

client= opt_home= home_given=0 apply=0 undo=0
while [ $# -gt 0 ]; do
	case $1 in
		--client)
			[ $# -ge 2 ] || usage_error "argument --client: expected one argument"
			client=$2
			shift 2 ;;
		--client=*) client=${1#*=}; shift ;;
		--home)
			[ $# -ge 2 ] || usage_error "argument --home: expected one argument"
			opt_home=$2 home_given=1
			shift 2 ;;
		--home=*) opt_home=${1#*=} home_given=1; shift ;;
		--apply) apply=1; shift ;;
		--undo) undo=1; shift ;;
		-h | --help) usage; exit 0 ;;
		*) usage_error "unrecognized arguments: $1" ;;
	esac
done
case $client in
	claude | codex | opencode | copilot) ;;
	'') usage_error "the following arguments are required: --client" ;;
	*) usage_error "argument --client: invalid choice: '$client' (choose from claude, codex, opencode, copilot)" ;;
esac

script=$0
if [ "$windows" = 1 ]; then script=$(to_posix "$script"); fi
case $script in */*) here=${script%/*} ;; *) here=. ;; esac
here=$(cd "$here" 2>/dev/null && pwd -P) || die 2 "cannot find the folder this script is in"
root=${here%/*}
if [ ! -f "$root/skills/nobrainer-tech-flow/SKILL.md" ] || [ ! -f "$root/scripts/install.sh" ]; then
	die 2 "run this script from a nobrainer-tech-flow checkout" \
		"git clone https://github.com/nobrainer-tech/nobrainer-tech-flow ~/.nobrainer-tech-flow, then sh ~/.nobrainer-tech-flow/scripts/install.sh --client $client"
fi

if [ "$home_given" = 1 ]; then
	[ -n "$opt_home" ] || usage_error "argument --home: expected a directory"
	reject_control "$opt_home" "--home"
	_home=$(to_posix "$opt_home")
	case $_home in /*) ;; *) _home=$(pwd -P)/$_home ;; esac
	home=$(clean abs "$_home")
	locate "$client" plain
else
	if [ "$windows" = 1 ] && [ -n "${USERPROFILE:-}" ]; then _home=$(to_posix "$USERPROFILE"); else _home=${HOME:-}; fi
	reject_control "$_home" "the home directory"
	case $_home in
		/*) home=$(clean keep "$_home") ;;
		*) die 2 "the home directory must be an absolute path, not '$_home'" ;;
	esac
	locate "$client" env
fi
skills_dir=$(clean keep "$skills_dir")
target=$(clean keep "$target")
for _path in "$skills_dir" "$target" "$root"; do reject_control "$_path" "a path"; done
state=$home/.nobrainer-flow-onboarding-$client.json

source_line="nobrainer-tech-flow $(cat "$root/skills/nobrainer-tech-flow/VERSION" 2>/dev/null || printf unknown)"
if command -v git >/dev/null 2>&1 && _commit=$(git -C "$root" rev-parse --short HEAD 2>/dev/null); then
	if [ -n "$(git -C "$root" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
		source_line="$source_line (commit $_commit, local changes)"
	else
		source_line="$source_line (commit $_commit)"
	fi
fi

if [ "$undo" = 1 ]; then
	undo
else
	check_destination
	install
fi
