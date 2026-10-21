import { execFileSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Tiktoken } from 'js-tiktoken/lite';
import o200k from 'js-tiktoken/ranks/o200k_base';
import { BASE_CARD_IDS, BuildError, MAX_CARD_TOKENS, buildContent, type Release } from '../../scripts/build-content.ts';
import { FLOW_TAG, FLOW_VERSION, MODULES, cardIds, cardRules, getCard } from '../../src/content/cards.ts';

const MCP_ROOT = fileURLToPath(new URL('../../', import.meta.url));
const REPO_ROOT = fileURLToPath(new URL('../../../', import.meta.url));
const source = JSON.parse(readFileSync(`${MCP_ROOT}content/SOURCE.json`, 'utf8')) as { tag: string; commit: string; repo: string };
const generated = JSON.parse(readFileSync(`${MCP_ROOT}src/generated/cards.json`, 'utf8')) as {
  tag: string;
  modules: string[];
  cards: Record<string, { rules: string[]; source: string; description?: string; full?: string }>;
};
const encoder = new Tiktoken(o200k);
const countTokens = (text: string): number => encoder.encode(text).length;

function git(...args: string[]): string | undefined {
  try {
    return execFileSync('git', ['-C', REPO_ROOT, ...args], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  } catch {
    return undefined;
  }
}

const tagCommit = git('rev-parse', '--verify', '--quiet', `refs/tags/${source.tag}^{commit}`);
const requireTag = process.env.NOBRAINER_REQUIRE_RELEASE_TAG === '1';
const needsTag = tagCommit || requireTag ? false : `tag ${source.tag} is not available in ${REPO_ROOT} (fetch tags, or set NOBRAINER_REQUIRE_RELEASE_TAG=1 to fail)`;

test('cards.json matches a fresh build from the pinned tag', { skip: needsTag }, () => {
  assert.ok(tagCommit, `tag ${source.tag} is required but missing`);
  execFileSync(process.execPath, ['scripts/build-content.ts', '--check'], { cwd: MCP_ROOT, stdio: ['ignore', 'pipe', 'pipe'] });
});

test('SOURCE.json commit equals the tag commit', { skip: needsTag }, () => {
  assert.equal(source.commit, tagCommit);
  assert.equal(generated.tag, source.tag);
});

test('module list equals the skills/*/SKILL.md files at the tag', { skip: needsTag }, () => {
  const tree = git('ls-tree', '-r', '--name-only', source.commit) ?? '';
  const released = tree.split('\n').flatMap((p) => /^skills\/([^/]+)\/SKILL\.md$/.exec(p)?.[1] ?? []).sort();
  assert.deepEqual(generated.modules, released);
});

test('every expected card id exists and nothing else', () => {
  const expected = [...BASE_CARD_IDS, ...generated.modules.map((m) => `module:${m}`)].sort();
  assert.deepEqual(Object.keys(generated.cards).sort(), expected);
  if (source.tag === 'v2.4.1') {
    assert.equal(generated.modules.length, 18);
    assert.equal(expected.length, 34);
  }
});

test('every card respects rule counts, ASCII and the token budget', () => {
  for (const [id, card] of Object.entries(generated.cards)) {
    const compact = JSON.stringify({ id, ...card });
    assert.match(compact, /^[\x20-\x7e]*$/, `${id} is not ASCII`);
    assert.ok(countTokens(compact) <= MAX_CARD_TOKENS, `${id} exceeds ${MAX_CARD_TOKENS} tokens`);
    if (id.startsWith('module:')) {
      assert.ok(card.description, `${id} has no description`);
      assert.ok(card.full?.includes(source.repo), `${id} has no full-module pointer`);
      assert.ok(card.rules.length <= 5, `${id} has more than 5 rules`);
    } else {
      assert.ok(card.rules.length >= 1 && card.rules.length <= 6, `${id} needs 1-6 rules`);
    }
  }
});

test('the loader exposes typed cards', () => {
  assert.equal(FLOW_TAG, source.tag);
  assert.match(FLOW_VERSION, /^\d+\.\d+\.\d+/);
  assert.deepEqual([...MODULES], generated.modules);
  assert.deepEqual(cardIds().sort(), Object.keys(generated.cards).sort());
  const card = getCard('event:blocked');
  assert.equal(card?.id, 'event:blocked');
  assert.equal(card?.next, 'AUTOPILOT');
  assert.equal(getCard('stage:NOPE'), undefined);
  assert.equal(getCard('toString'), undefined);
  assert.equal(cardRules('gates').length, 1);
  assert.match(cardRules('gates')[0] ?? '', /^Merge, deploy, publish, spend, delete, contact people, .* unless the owner already authorized that exact action\.$/);
  assert.deepEqual(cardRules('stage:NOPE'), []);
});

// ---- builder core against an in-memory release (no git) ----

const ALPHA = `---
name: nobrainer-alpha
description: "Use when testing the alpha module."
---

# Alpha

## Rules

Keep proofs current. Never trust a report; inspect the artifact.
`;

function fakeRelease(): Release {
  return {
    tag: 'v9.9.9',
    commit: 'f'.repeat(40),
    files: {
      'package.json': '{"version":"9.9.9"}',
      'skills/nobrainer-alpha/SKILL.md': ALPHA,
      'skills/nobrainer-beta/SKILL.md': ALPHA.replace(/alpha/g, 'beta'),
    },
  };
}

function fakeCards(extra: Record<string, unknown> = {}): Record<string, unknown> {
  const base = { source: 'skills/nobrainer-alpha/SKILL.md', heading: 'Rules', rules: ['Keep proofs current.'] };
  return { ...Object.fromEntries(BASE_CARD_IDS.map((id) => [id, base])), ...extra };
}

const build = (cards: Record<string, unknown>) =>
  buildContent({ source: { repo: 'https://example.invalid/flow', tag: '', commit: '', files: {} }, cards, release: fakeRelease(), countTokens, pin: true });

test('builder warns for a released module without an entry', () => {
  const result = build(fakeCards({ 'module:nobrainer-alpha': { rules: ['Never trust a report'] } }));
  assert.deepEqual(result.warnings, ['WARNING: module:nobrainer-beta has no cards.yaml entry; emitting a description-only card']);
  const out = JSON.parse(result.json) as typeof generated;
  assert.deepEqual(out.modules, ['nobrainer-alpha', 'nobrainer-beta']);
  assert.deepEqual(out.cards['module:nobrainer-beta']?.rules, []);
  assert.equal(out.cards['module:nobrainer-beta']?.description, 'Use when testing the alpha module.'.replace('alpha', 'beta'));
  assert.ok(result.source.files['skills/nobrainer-alpha/SKILL.md']);
  assert.equal(out.cards['module:nobrainer-alpha']?.source, 'skills/nobrainer-alpha/SKILL.md#alpha');
});

test('builder fails for a module entry absent from the release', () => {
  assert.throws(
    () => build(fakeCards({ 'module:nobrainer-codex-context': { heading: 'Rules', rules: ['Keep proofs current.'] } })),
    (error: unknown) => error instanceof BuildError && /module:nobrainer-codex-context: module "nobrainer-codex-context" is not in the release v9\.9\.9/.test(error.message),
  );
});

test('builder rejects paraphrase, mid-sentence cuts and a stale pin', () => {
  const paraphrase = fakeCards({ 'stage:VERIFY': { source: 'skills/nobrainer-alpha/SKILL.md', heading: 'Rules', rules: ['Keep all proofs current.'] } });
  assert.throws(() => build(paraphrase), /stage:VERIFY: rule does not occur verbatim/);
  const fragment = fakeCards({ 'stage:VERIFY': { source: 'skills/nobrainer-alpha/SKILL.md', heading: 'Rules', rules: ['trust a report'] } });
  assert.throws(() => build(fragment), /stage:VERIFY: rule is not cut at a sentence/);
  const stale = { repo: 'x', tag: 'v9.9.9', commit: 'f'.repeat(40), files: { 'skills/nobrainer-alpha/SKILL.md': '0'.repeat(64) } };
  assert.throws(
    () => buildContent({ source: stale, cards: fakeCards(), release: fakeRelease(), countTokens }),
    /sha256 mismatch for skills\/nobrainer-alpha\/SKILL\.md/,
  );
});
