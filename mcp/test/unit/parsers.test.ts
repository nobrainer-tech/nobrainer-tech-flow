import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import * as fc from 'fast-check';
import { parseTestSummary, hasFailingSummary } from '../../src/evidence/parsers.ts';
import { normaliseOut, normaliseText } from '../../src/evidence/normalise.ts';

const fx = (name: string): string =>
  readFileSync(join(import.meta.dirname, '..', 'fixtures', 'runners', `${name}.txt`), 'utf8');

const CASES: Array<[string, string, number, number]> = [
  ['pytest', 'pytest', 12, 0],
  ['unittest', 'unittest', 10, 0],
  ['node', 'node:test', 3, 0],
  ['vitest', 'vitest', 7, 0],
  ['jest', 'jest', 9, 0],
  ['mocha', 'mocha', 3, 0],
  ['playwright', 'playwright', 5, 0],
  ['go', 'go', 2, 0],
  ['cargo', 'cargo', 4, 0],
  ['rspec', 'rspec', 5, 0],
  ['phpunit', 'phpunit', 5, 0],
  ['dotnet', 'dotnet', 10, 0],
];
const FAILS: Record<string, [number, number]> = {
  pytest: [10, 2],
  unittest: [8, 2],
  node: [3, 1],
  vitest: [6, 1],
  jest: [7, 1],
  mocha: [2, 1],
  playwright: [5, 1],
  go: [1, 1],
  cargo: [2, 1],
  rspec: [2, 2],
  phpunit: [3, 2],
  dotnet: [9, 1],
};

for (const [file, runner, passed] of CASES) {
  test(`${runner}: pass fixture`, () => {
    const got = parseTestSummary(fx(`${file}-pass`));
    assert.equal(got?.runner, runner);
    assert.equal(got?.failed, 0);
    assert.equal(got?.passed, passed);
    assert.equal(hasFailingSummary(fx(`${file}-pass`)), false);
  });
  test(`${runner}: fail fixture`, () => {
    const [p, f] = FAILS[file] as [number, number];
    assert.deepEqual(parseTestSummary(fx(`${file}-fail`)), { runner, passed: p, failed: f });
    assert.equal(hasFailingSummary(fx(`${file}-fail`)), true);
  });
}

test('pytest: errors count as failed, quiet and ANSI output parse', () => {
  assert.deepEqual(parseTestSummary('=== 1 failed, 3 passed, 2 errors in 0.5s ==='), {
    runner: 'pytest',
    passed: 3,
    failed: 3,
  });
  assert.equal(parseTestSummary('3 passed in 0.12s')?.passed, 3);
  assert.equal(parseTestSummary('1 failed, 2 passed in 0.10s (0:00:00)')?.failed, 1);
  const ansi = '\u001b[32m============ \u001b[1m4 passed\u001b[0m\u001b[32m in 0.02s ============\u001b[0m\r\n';
  assert.deepEqual(parseTestSummary(ansi), { runner: 'pytest', passed: 4, failed: 0 });
});

test('node:test: spec reporter lines with the info prefix', () => {
  const out = ['\u2139 tests 4', '\u2139 pass 3', '\u2139 fail 1'].join('\n');
  assert.deepEqual(parseTestSummary(out), { runner: 'node:test', passed: 3, failed: 1 });
});

test('vitest and jest extras (skipped, todo)', () => {
  assert.equal(parseTestSummary('      Tests  1 failed | 2 skipped | 1 todo | 4 passed (8)')?.passed, 4);
  assert.equal(parseTestSummary('Tests:       2 todo, 3 passed, 5 total')?.passed, 3);
});

test('prose and look-alike lines are not summaries', () => {
  for (const s of [
    'All 3 tests passed successfully, 2 failed earlier',
    'the build passed in 3s',
    '12 passed',
    '5 passing checks',
    '5 passing',
    'ok  that works fine',
    'Tests: passed',
    'I ran 12 examples, 0 failures yesterday',
    'Passed! all good',
    'test result: ok. nothing to see',
    '=== FAILURES ===',
    'Ran 5 tests in 0.1s but nobody said OK',
    'x'.repeat(5000) + ' 3 passed in 0.1s',
    '',
  ]) {
    assert.equal(parseTestSummary(s), null, s.slice(0, 40));
  }
});

test('last recognised summary wins', () => {
  assert.equal(parseTestSummary(fx('jest-fail') + '\n' + fx('pytest-pass'))?.runner, 'pytest');
  assert.equal(parseTestSummary(fx('pytest-pass') + '\n' + fx('vitest-fail'))?.runner, 'vitest');
  assert.equal(parseTestSummary(fx('pytest-fail') + '\n' + fx('pytest-pass'))?.failed, 0);
  assert.equal(parseTestSummary(fx('pytest-pass') + '\n' + fx('pytest-fail'))?.failed, 2);
});

test('playwright: needs a Running line or a timed passed line', () => {
  assert.equal(parseTestSummary('  1 failed'), null);
  assert.equal(parseTestSummary('Running 2 tests using 1 worker\n  1 failed')?.failed, 1);
});

test('normalise helpers', () => {
  assert.equal(normaliseOut('\u001b[31mred\u001b[0m\r\nline\rend\u0007  '), 'red\nline\nend');
  assert.equal(normaliseOut('a\tb\u0000c'), 'a\tbc');
  assert.equal(normaliseOut('x'.repeat(5000)).length, 4000);
  assert.equal(normaliseOut('0' + 'y'.repeat(4000)), 'y'.repeat(4000));
  assert.equal(normaliseText(' a \u0001\n\t b  c '), 'a b c');
});

test('property: never throws, fast on 4,000-char inputs', () => {
  const alphabet = fc.constantFrom('=', ' ', '1', 'p', 'a', 's', 'e', 'd', ',', '|', '(', ')', ':', '\n', 'T');
  fc.assert(
    fc.property(fc.oneof(fc.string({ maxLength: 8000 }), fc.array(alphabet, { maxLength: 8000 }).map((a) => a.join(''))), (s) => {
      parseTestSummary(s);
      hasFailingSummary(s);
    }),
    { numRuns: 300 },
  );
  const worst = [
    '='.repeat(4000),
    ' '.repeat(4000),
    '1 passed, '.repeat(400),
    '= 1 passed '.repeat(350),
    ('# pass 1\n').repeat(450),
    'Tests  ' + '1 passed | '.repeat(300),
    ('ok ' + 'a'.repeat(100) + '\n').repeat(38),
  ];
  for (const s of worst) {
    const t0 = performance.now();
    parseTestSummary(s.slice(0, 4000));
    assert.ok(performance.now() - t0 < 50, 'slow input');
  }
});
