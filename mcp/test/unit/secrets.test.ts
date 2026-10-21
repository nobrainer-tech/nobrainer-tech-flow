import { test } from 'node:test';
import assert from 'node:assert/strict';
import * as fc from 'fast-check';
import { findSecret, scanInput } from '../../src/evidence/secrets.ts';

// Every fake secret is assembled at runtime so no literal secret exists in the tree.
const A = (n: number): string => 'A'.repeat(n);
const lower = (n: number): string => 'k9'.repeat(n / 2);
const FAKES: Record<string, string> = {
  pem_private_key: ['-----BEGIN ', 'RSA PRIVATE', ' KEY-----'].join(''),
  aws_access_key_id: 'AK' + 'IA' + 'ABCDEFGH12345678',
  github_token: 'gh' + 'p_' + A(36),
  openai_key: 'sk' + '-' + 'proj-' + lower(48),
  anthropic_key: 'sk' + '-ant-' + 'api03-' + lower(40),
  slack_token: 'xo' + 'xb-' + '1234567890-abcdefghij',
  jwt: 'ey' + 'J' + 'h'.repeat(20) + '.' + 'p'.repeat(20) + '.' + 's'.repeat(20),
  assignment: ['pass', 'word'].join('') + '=' + 'Zq7vL2mNp9Xr4TwY',
};

for (const [id, value] of Object.entries(FAKES)) {
  test(`detects ${id}`, () => {
    assert.equal(findSecret(`log line before ${value} after`), id);
    const hit = scanInput({ evidence: [{ kind: 'command' }, { out: `x ${value}` }] });
    assert.deepEqual(hit, { field: 'evidence[1].out', pattern: id });
    assert.ok(!JSON.stringify(hit).includes(value));
  });
}

test('more token shapes', () => {
  assert.equal(findSecret('as' + 'ia' + 'ABCDEFGH12345678'), null);
  assert.equal(findSecret('AS' + 'IA' + 'ABCDEFGH12345678'), 'aws_access_key_id');
  for (const p of ['gho_', 'ghu_', 'ghs_', 'ghr_']) {
    assert.equal(findSecret('gh' + p.slice(2) + A(40)), 'github_token');
  }
  assert.equal(findSecret('github' + '_pat_' + 'a1'.repeat(30)), 'github_token');
  assert.equal(findSecret('sk' + '-' + 'a1'.repeat(24)), 'openai_key');
  assert.equal(findSecret('-----BEGIN ' + 'PRIVATE KEY-----'), 'pem_private_key');
  assert.equal(findSecret('-----BEGIN ' + 'OPENSSH PRIVATE KEY-----'), 'pem_private_key');
});

test('assignment forms', () => {
  const v = 'Zq7vL2mNp9Xr4TwY';
  assert.equal(findSecret(`{"to` + `ken": "${v}"}`), 'assignment');
  assert.equal(findSecret(`API_` + `KEY: ${v}`), 'assignment');
  assert.equal(findSecret(`SEC` + `RET = '${v}'`), 'assignment');
  assert.equal(findSecret(`api-` + `key=${v}`), 'assignment');
});

test('look-alikes and placeholders are not secrets', () => {
  const t = 'to' + 'ken';
  const pw = 'pass' + 'word';
  for (const s of [
    'a'.repeat(64),
    '0123456789abcdef'.repeat(4),
    'da39a3ee5e6b4b0d3255bfef95601890afd80709',
    '123e4567-e89b-12d3-a456-426614174000',
    'test_decodes_base64_QWxhZGRpbjpvcGVuIHNlc2FtZQ',
    'sk-1',
    'sk-learn-is-a-kebab-case-name-that-is-long-enough-to-matter',
    'task-' + 'a'.repeat(40),
    'xoxb-1',
    'eyJhbGciOiJIUzI1NiJ9.e30.x',
    `${t}=<your-${t}>`,
    `${t}=***************`,
    `${pw}=xxxxxxxxxxxxxxxx`,
    `${pw}=\${DB_PASSWORD_VALUE}`,
    `${pw}=$DB_PASSWORD_VALUE`,
    `${pw}=changeme-changeme`,
    `${t}=example-example-example`,
    `${pw}=short`,
    `${pw}=process.env.DB_PASSWORD`,
    `${t}=getToken(request)`,
    `max_${t}s=1000000000000`,
    'ghp_short',
    'AKIA is a prefix',
  ]) {
    assert.equal(findSecret(s), null, s.slice(0, 40));
  }
});

test('scanInput paths, depth limit and non-strings', () => {
  const v = FAKES['github_token'] as string;
  assert.deepEqual(scanInput({ dod: [{}, {}, { text: v }] }), { field: 'dod[2].text', pattern: 'github_token' });
  assert.deepEqual(scanInput(v), { field: '$', pattern: 'github_token' });
  assert.deepEqual(scanInput({ 'we ird': v }), { field: '["*"]', pattern: 'github_token' });
  assert.equal(scanInput({ n: 1, b: true, z: null, s: 'fine', a: [1, 'ok'] }), null);
  assert.equal(scanInput(null), null);
  let ok: unknown = 'leaf';
  for (let i = 0; i < 8; i++) ok = { c: ok };
  assert.equal(scanInput(ok), null);
  let deep: unknown = 'leaf';
  for (let i = 0; i < 12; i++) deep = { c: deep };
  assert.equal(scanInput(deep)?.pattern, 'too_deep');
  assert.equal(scanInput(deep)?.field, 'c.c.c.c.c.c.c.c.c');
});

test('property: scanInput never throws, findSecret fast', () => {
  fc.assert(
    fc.property(fc.jsonValue({ maxDepth: 12 }), (v) => {
      scanInput(v);
    }),
    { numRuns: 300 },
  );
  const worst = [
    'eyJ'.repeat(1300),
    'eyJ' + 'a'.repeat(3900),
    ('eyJ' + 'a'.repeat(30) + '.').repeat(100),
    'sk-' + 'a'.repeat(3990),
    'password=' + 'a '.repeat(1990),
    'token:'.repeat(660),
    ('password="' + 'b'.repeat(190) + ' ').repeat(19),
    '-----BEGIN '.repeat(360),
    'AKIA'.repeat(1000),
  ];
  for (const s of worst) {
    const t0 = performance.now();
    findSecret(s);
    assert.ok(performance.now() - t0 < 50, 'slow input');
  }
});
