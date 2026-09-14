---
name: nobrainer-browser
description: "Use when the owner says nb-browser or nobrainer-browser, asks to inspect or operate a rendered website, attach to an existing approved Chrome/Edge session, restart an approved non-default Chromium profile for loopback CDP, reproduce a browser flow, run Playwright tests, or record and analyze a Playwright trace. Prefer a current Playwright CLI with an explicit version readback; do not set up MCP or extra browser plugins by default."
---

# NoBrainer Browser

Use one Playwright-first browser path. The agent-focused `@playwright/cli`
drives and inspects pages; the repository's Playwright test CLI records and
opens traces. Do not add a second browser framework merely because one exists.

## Route the task

| Need | Default |
|---|---|
| Inspect a rendered page, follow navigation, read dynamic content | `playwright-cli` |
| Reuse an approved logged-in Chrome/Edge session | `playwright-cli attach` over CDP |
| Run or debug repository tests | the repository's `npx playwright test` |
| Record or inspect failure evidence | Playwright trace + `show-trace` |
| Plain static content already available without a browser | use the cheaper read path |

Do not install MCP when the CLI covers the task. Do not install a browser
plugin as the default path. Reuse an already configured MCP only when the
current harness cannot run the CLI and the MCP has fresh capability readback.

## Capability and install gate

First inspect local capabilities independently and keep the interactive and
repository-test CLIs distinct:

```bash
global_cli_status=none
local_test_cli_status=none

if command -v playwright-cli >/dev/null 2>&1 &&
   playwright-cli --version >/dev/null 2>&1; then
  global_cli_status=usable
fi

if [ -f package.json ] &&
   [ -x node_modules/.bin/playwright ] &&
   node_modules/.bin/playwright --version >/dev/null 2>&1; then
  local_test_cli_status=usable
fi

printf 'global_cli=%s\n' "$global_cli_status"
printf 'local_test_cli=%s\n' "$local_test_cli_status"

if [ "$global_cli_status" = usable ] ||
   [ "$local_test_cli_status" = usable ]; then
  printf 'some_playwright_capability=available\n'
else
  printf 'some_playwright_capability=none\n' >&2
  exit 1
fi
```

Use `global_cli=usable` for interactive `playwright-cli` work. Use
`local_test_cli=usable` only for the repository's standard Playwright test CLI;
it does not prove that interactive `playwright-cli` commands such as `attach`,
`snapshot`, `click` or `fill` are available. If the capability required by the
request is not usable and setup is not in scope, stop with the exact missing
capability and one remediation; do not query npm or install.

When setup is explicitly in scope and the required local capability is not
available, use the current npm channel only to discover a version, then pin
that exact version for execution and record the readback:

```bash
PLAYWRIGHT_CLI_VERSION="$(npm view @playwright/cli version)"
test -n "$PLAYWRIGHT_CLI_VERSION"
npm install -g "@playwright/cli@$PLAYWRIGHT_CLI_VERSION"
playwright-cli --version
playwright-cli --help
playwright-cli --help attach
```

Package installation is a machine write. Perform it only when setup is within
scope, and do not claim success until the binary readback passes. For a test
repository, prefer its lockfile and package scripts over changing dependencies.

The CLI also offers `playwright-cli install --skills`. Do not run it by default
while `nobrainer-browser` owns browser routing: that would add another skill
owner with overlapping triggers. Read the live CLI help instead. If the owner
chooses the upstream Playwright skills, reconcile to one browser-skill owner
rather than keeping both active.

## Restart an approved profile for CDP attach

Use this flow only when the owner explicitly approves closing the target browser
and the target is an existing, dedicated Chromium user-data directory. It is
not a way to make a daily/default Chrome profile remotely debuggable. Read the
[bounded CDP profile restart reference](references/cdp-profile-restart.md)
before any process or profile action; it separates identity readback, stopping,
loopback launch, endpoint verification and CLI attach.

## Existing-session attach

Use attach when the owner needs the actual approved session, login or open tab:

```bash
playwright-cli attach --cdp=chrome
playwright-cli attach --cdp=http://127.0.0.1:9222
# Example for a separately configured Edge debugging endpoint:
playwright-cli attach --cdp=http://127.0.0.1:9333
```

The current CLI accepts a supported channel such as `chrome` or an actual CDP
endpoint URL; verify the live `attach` help because this interface can change.
CDP attach is Chromium-only. Confirm the exact browser, profile, endpoint and
write scope before acting. The CLI also exposes extension attach, but that is
not the default because it requires a browser extension. If attach is
unavailable, say so; do not bypass a saved browser permission block, copy or
mirror a profile, extract cookies, reuse credentials, or silently launch a
look-alike authenticated session. A request to inspect does not authorize form
submission, purchase, publication, message sending, deletion or account
changes.

If no existing login is required, a disposable session is simpler:

```bash
playwright-cli open https://example.com
```

## Inspect and operate

Take a fresh snapshot before using element references, and refresh it after a
navigation or substantial DOM change:

```bash
playwright-cli snapshot
playwright-cli find "Settings"
playwright-cli click e4
playwright-cli fill e7 "value"
playwright-cli eval "el => el.textContent" e4
```

Prefer semantic refs and visible state over brittle coordinates. For each
material action, verify the resulting URL, visible state or downloaded artifact
instead of trusting command exit alone.

## Tests and traces

Use the repository's existing script/config first. Narrow the test target and
record a trace when reproduction or evidence matters:

```bash
npx playwright test path/to/spec --trace on
REPORT_PORT=9324  # replace with an available explicit port
npx playwright show-report --port "$REPORT_PORT"
npx playwright show-trace trace.zip
```

For a live CLI flow:

```bash
playwright-cli tracing-start
playwright-cli snapshot
# perform the bounded steps
playwright-cli tracing-stop
```

Locate the actual trace artifact, preserve its path and open it. Review Actions,
DOM snapshots, Network, Console and Source; a green status without the expected
side effect is not proof. Use an available explicit report port; do not assume
that `--port 0` selects an ephemeral port across CLI versions. Treat traces as
sensitive artifacts: they may contain cookies, headers, form values, URLs,
payloads and private page content. Keep them in a project-ignored or temporary
path, inspect and redact before sharing, and never commit them as routine
evidence. Do not edit project trace policy merely to inspect one failure when a
CLI flag is sufficient.

## Failure and closeout

- If the CLI, target session or required permission is unavailable, stop with
  the exact failed probe and one remediation.
- If a trace cannot reproduce the issue, report `NOT_REPRODUCED`; do not invent
  a cause.
- For an attached external session use `playwright-cli detach`; never close it.
  Restart or close an existing profile only through the explicit pre-attach flow
  above. Close only a disposable session owned by this CLI run.
- Report the exact CLI version, browser/session mode, pages or tests inspected,
  trace/report paths, observed result, side effects, uncertainty and cleanup.

Sources: [Playwright attach](https://playwright.dev/agent-cli/commands/attach),
[Playwright `connectOverCDP`](https://playwright.dev/docs/api/class-browsertype),
[Playwright test CLI](https://playwright.dev/docs/test-cli),
[Trace Viewer](https://playwright.dev/docs/trace-viewer),
[Chrome remote-debugging security changes](https://developer.chrome.com/blog/remote-debugging-port),
and [`@playwright/cli` on npm](https://www.npmjs.com/package/@playwright/cli).
