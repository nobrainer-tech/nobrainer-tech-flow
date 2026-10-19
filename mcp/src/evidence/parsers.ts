// Recognised test-runner summaries (spec 7.3). Line-by-line, anchored, bounded regexes only.
//
// Disambiguation: every runner has its own anchor, so shapes never collide.
//   pytest      "N passed, M failed in T.TTs" (optionally wrapped in === ... ===), time required
//               unless the line is wrapped in ===.
//   Playwright  one count per line, "N passed (T)" with a parenthesised time, or "N failed" /
//               "N flaky" lines in a run that printed "Running N tests".
//   Mocha       "N passing (T)" with a time, "N failing" within 3 lines after it.
//   A bare "12 passed" line is not recognised by any runner.
// The latest recognised summary (highest line index) wins. Multi-binary runners (Go, cargo,
// dotnet) are summed across the whole output. Playwright counts flaky as passed.
import { normaliseOut } from './normalise.ts';

export type RunnerSummary = { runner: string; passed: number; failed: number };
type Found = RunnerSummary & { at: number };

const MAX_LINE = 300;
const num = (s: string | undefined): number => (s === undefined ? 0 : Number.parseInt(s, 10));

function parts(body: string): Map<string, number> | null {
  const out = new Map<string, number>();
  for (const part of body.split(', ')) {
    const m = /^(\d{1,9}) ([a-z ]{2,20})$/.exec(part.trim());
    if (!m || m[2] === undefined) return null;
    out.set(m[2], (out.get(m[2]) ?? 0) + num(m[1]));
  }
  return out;
}

const PYTEST_WORDS = /^(?:passed|failed|errors?|skipped|xfailed|xpassed|warnings?|deselected|rerun)$/;

function pytestLine(line: string): RunnerSummary | null {
  const timed = /^=*\s*(.{1,200}?)\s+in\s+[\d.]{1,10}s(?:\s+\(\d{1,3}:\d{2}:\d{2}\))?\s*=*$/.exec(line);
  const wrapped = /^={2,}\s*(.{1,200}?)\s*={2,}$/.exec(line);
  const body = timed?.[1] ?? wrapped?.[1];
  if (body === undefined) return null;
  const p = parts(body);
  if (!p) return null;
  for (const k of p.keys()) if (!PYTEST_WORDS.test(k)) return null;
  if (!p.has('passed') && !p.has('failed') && !p.has('error') && !p.has('errors')) return null;
  const failed = (p.get('failed') ?? 0) + (p.get('error') ?? 0) + (p.get('errors') ?? 0);
  return { runner: 'pytest', passed: p.get('passed') ?? 0, failed };
}

function keyedCounts(body: string, sep: string): Map<string, number> | null {
  const out = new Map<string, number>();
  for (const part of body.split(sep)) {
    const m = /^(\d{1,9}) ([a-z]{2,10})$/.exec(part.trim());
    if (!m || m[2] === undefined) return null;
    out.set(m[2], num(m[1]));
  }
  return out;
}

function vitestLine(line: string): RunnerSummary | null {
  const m = /^\s*Tests {2,}(.{1,200}?) \((\d{1,9})\)\s*$/.exec(line);
  const p = m?.[1] === undefined ? null : keyedCounts(m[1], ' | ');
  if (!p || (!p.has('passed') && !p.has('failed'))) return null;
  return { runner: 'vitest', passed: p.get('passed') ?? 0, failed: p.get('failed') ?? 0 };
}

function jestLine(line: string): RunnerSummary | null {
  const m = /^\s*Tests:\s+(.{1,200}?), (\d{1,9}) total\s*$/.exec(line);
  const p = m?.[1] === undefined ? null : keyedCounts(m[1], ', ');
  if (!p || (!p.has('passed') && !p.has('failed'))) return null;
  return { runner: 'jest', passed: p.get('passed') ?? 0, failed: p.get('failed') ?? 0 };
}

function lastWhere(lines: string[], f: (l: string, i: number) => Found | null): Found | null {
  let best: Found | null = null;
  lines.forEach((l, i) => {
    const r = f(l, i);
    if (r) best = r;
  });
  return best;
}

function unittest(lines: string[]): Found | null {
  let best: Found | null = null;
  lines.forEach((l, i) => {
    const ran = /^Ran (\d{1,9}) tests? in [\d.]{1,10}s$/.exec(l);
    if (!ran) return;
    const total = num(ran[1]);
    for (let j = i + 1; j <= i + 3 && j < lines.length; j++) {
      const line = lines[j] ?? '';
      if (/^OK(?: \([^)]{0,100}\))?$/.test(line)) {
        best = { runner: 'unittest', passed: total, failed: 0, at: j };
        return;
      }
      const f = /^FAILED \(([^)]{1,100})\)$/.exec(line);
      if (f?.[1] !== undefined) {
        const bad = num(/failures=(\d+)/.exec(f[1])?.[1]) + num(/errors=(\d+)/.exec(f[1])?.[1]);
        best = { runner: 'unittest', passed: Math.max(0, total - bad), failed: bad, at: j };
        return;
      }
    }
  });
  return best;
}

function nodeTest(lines: string[]): Found | null {
  let pass: { n: number; at: number } | null = null;
  let best: Found | null = null;
  lines.forEach((l, i) => {
    const m = /^\s*(?:#|\u2139)\s+(pass|fail)\s+(\d{1,9})\s*$/.exec(l);
    if (!m) return;
    if (m[1] === 'pass') pass = { n: num(m[2]), at: i };
    else if (pass && i - pass.at <= 10) {
      best = { runner: 'node:test', passed: pass.n, failed: num(m[2]), at: i };
    }
  });
  return best;
}

function mocha(lines: string[]): Found | null {
  let cur: Found | null = null;
  lines.forEach((l, i) => {
    const p = /^\s*(\d{1,9}) passing \(\d+(?:\.\d+)?(?:ms|s|m)\)\s*$/.exec(l);
    if (p) {
      cur = { runner: 'mocha', passed: num(p[1]), failed: 0, at: i };
      return;
    }
    const f = /^\s*(\d{1,9}) failing\s*$/.exec(l);
    if (!f) return;
    if (cur && i - cur.at <= 3 && cur.failed === 0) cur = { ...cur, failed: num(f[1]), at: i };
    else cur = { runner: 'mocha', passed: 0, failed: num(f[1]), at: i };
  });
  return cur;
}

function playwright(lines: string[]): Found | null {
  let start = 0;
  let sawRunning = false;
  lines.forEach((l, i) => {
    if (/^\s*Running \d{1,9} tests? using \d{1,5} workers?\s*$/.test(l)) {
      start = i;
      sawRunning = true;
    }
  });
  let passed = 0;
  let failed = 0;
  let at = -1;
  let anchored = false;
  for (let i = start; i < lines.length; i++) {
    const m = /^\s*(\d{1,9}) (passed|failed|flaky|skipped|interrupted|did not run)( \([\d.]{1,10}(?:ms|s|m)\))?\s*$/.exec(
      lines[i] ?? '',
    );
    if (!m) continue;
    const n = num(m[1]);
    if (m[2] === 'passed' || m[2] === 'flaky') passed += n;
    else if (m[2] === 'failed' || m[2] === 'interrupted') failed += n;
    if (m[2] === 'passed' && m[3] !== undefined) anchored = true;
    if (m[2] === 'passed' || m[2] === 'failed' || m[2] === 'flaky' || m[2] === 'interrupted') at = i;
  }
  if (at < 0 || !(anchored || sawRunning)) return null;
  return { runner: 'playwright', passed, failed, at };
}

function goTest(lines: string[]): Found | null {
  let okPkgs = 0;
  let failPkgs = 0;
  let subPass = 0;
  let subFail = 0;
  let at = -1;
  lines.forEach((l, i) => {
    const pkg = /^(ok|FAIL)\s+\S{1,200}\s+(?:\(cached\)|[\d.]{1,10}s(?:\s+coverage:.{0,60})?|\[(?:build|setup) failed\])\s*$/.exec(l);
    if (pkg) {
      if (pkg[1] === 'ok') okPkgs++;
      else failPkgs++;
      at = i;
    } else if (/^\s*--- PASS: \S/.test(l)) subPass++;
    else if (/^\s*--- FAIL: \S/.test(l)) subFail++;
  });
  if (at < 0) return null;
  return {
    runner: 'go',
    passed: subPass > 0 ? subPass : okPkgs,
    failed: subFail > 0 ? subFail : failPkgs,
    at,
  };
}

function summed(lines: string[], runner: string, re: RegExp, swap = false): Found | null {
  let passed = 0;
  let failed = 0;
  let at = -1;
  lines.forEach((l, i) => {
    const m = re.exec(l);
    if (!m) return;
    passed += num(swap ? m[2] : m[1]);
    failed += num(swap ? m[1] : m[2]);
    at = i;
  });
  return at < 0 ? null : { runner, passed, failed, at };
}

function rspec(lines: string[]): Found | null {
  return lastWhere(lines, (l, at) => {
    const m = /^\s*(\d{1,9}) examples?, (\d{1,9}) failures?(?:, (\d{1,9}) pending)?(?:, (\d{1,9}) errors? occurred outside of examples)?\s*$/.exec(l);
    if (!m) return null;
    const failed = num(m[2]) + num(m[4]);
    return { runner: 'rspec', passed: Math.max(0, num(m[1]) - num(m[2]) - num(m[3])), failed, at };
  });
}

function phpunit(lines: string[]): Found | null {
  return lastWhere(lines, (l, at) => {
    const ok = /^OK \((\d{1,9}) tests?, \d{1,9} assertions?\)$/.exec(l);
    if (ok) return { runner: 'phpunit', passed: num(ok[1]), failed: 0, at };
    const m = /^Tests: (\d{1,9}), Assertions: \d{1,9}((?:, [A-Za-z]{3,12}: \d{1,9}){0,8})\.?$/.exec(l);
    if (!m) return null;
    const bad = num(/Failures: (\d+)/.exec(m[2] ?? '')?.[1]) + num(/Errors: (\d+)/.exec(m[2] ?? '')?.[1]);
    return { runner: 'phpunit', passed: Math.max(0, num(m[1]) - bad), failed: bad, at };
  });
}

const RUNNERS: Array<(lines: string[]) => Found | null> = [
  (ls) => lastWhere(ls, (l, at) => withAt(pytestLine(l), at)),
  unittest,
  nodeTest,
  (ls) => lastWhere(ls, (l, at) => withAt(vitestLine(l), at)),
  (ls) => lastWhere(ls, (l, at) => withAt(jestLine(l), at)),
  mocha,
  playwright,
  goTest,
  (ls) => summed(ls, 'cargo', /^test result: (?:ok|FAILED)\. (\d{1,9}) passed; (\d{1,9}) failed;/),
  rspec,
  phpunit,
  (ls) => summed(ls, 'dotnet', /^(?:Passed|Failed)!\s+-\s+Failed:\s*(\d{1,9}),\s*Passed:\s*(\d{1,9})/, true),
];

function withAt(r: RunnerSummary | null, at: number): Found | null {
  return r ? { ...r, at } : null;
}

/** The last recognised runner summary in `out`, or null. */
export function parseTestSummary(out: string): RunnerSummary | null {
  const lines = normaliseOut(out)
    .split('\n')
    .map((l) => (l.length > MAX_LINE ? '' : l));
  let best: Found | null = null;
  for (const run of RUNNERS) {
    const r = run(lines);
    if (r && (best === null || r.at > best.at)) best = r;
  }
  return best === null ? null : { runner: best.runner, passed: best.passed, failed: best.failed };
}

/** True when a recognised summary reports at least one failure. */
export function hasFailingSummary(out: string): boolean {
  const s = parseTestSummary(out);
  return s !== null && s.failed > 0;
}
