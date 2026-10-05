#!/usr/bin/env node
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = new URL('../', import.meta.url);
const metadata = JSON.parse(readFileSync(new URL('package.json', root), 'utf8'));
const args = process.argv.slice(2);
const help = [
  'nobrainer-tech-flow ' + metadata.version, '',
  'Preview: npx nobrainer-tech-flow --client codex',
  'Install: npx nobrainer-tech-flow --client codex --apply',
  'Undo:    npx nobrainer-tech-flow --client codex --undo --apply', '',
  'Clients: codex, claude (Claude Code), opencode, copilot.',
  'Use --home PATH for an isolated profile. Python 3.11+ is required for installation.',
  'Nothing is installed until --apply. Applied installs retain this release in',
  "your profile's .nobrainer-tech-flow/npm directory, so skills survive npx cache cleanup.",
  'Undo uses the existing managed setup record; it preserves foreign files.',
  'For Claude Chat, use the release plugin ZIP. ChatGPT/Codex plugin setup:',
  'https://github.com/nobrainer-tech/nobrainer-tech-flow/blob/main/docs/CHAT_PLUGINS.md', ''
].join('\n');
if (!args.length || args.includes('--help') || args.includes('-h')) {
  process.stdout.write(help);
} else if (args.length === 1 && ['--version', '-v'].includes(args[0])) {
  console.log(metadata.version);
} else {
  const candidates = process.platform === 'win32'
    ? [['py', ['-3']], ['python', []], ['python3', []]]
    : [['python3', []], ['python', []]];
  let chosen;
  for (const [executable, prefix] of candidates) {
    const check = spawnSync(executable, [...prefix, '-c',
      'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'],
      { stdio: 'ignore', timeout: 5000 });
    if (check.status === 0) { chosen = [executable, prefix]; break; }
  }
  if (!chosen) {
    console.error('Python 3.11+ is required. Install Python from python.org, then repeat this command.');
    process.exitCode = 2;
  } else {
    const [executable, prefix] = chosen;
    const run = spawnSync(executable,
      [...prefix, fileURLToPath(new URL('scripts/npm_install.py', root)), ...args],
      { stdio: 'inherit', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } });
    if (run.error) { console.error('Installer could not start: ' + run.error.code); process.exitCode = 2; }
    else process.exitCode = run.status ?? 2;
  }
}
