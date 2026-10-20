import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import * as z from 'zod';
import { Tiktoken } from 'js-tiktoken/lite';
import o200k_base from 'js-tiktoken/ranks/o200k_base';
import { recommendFlowModel, recommendInput, RECOMMEND_ANNOTATIONS, RECOMMEND_TOOL } from '../../src/advisor/index.ts';
import { TASKS } from '../../src/advisor/schema.ts';
import { SNAPSHOT } from '../../src/advisor/snapshot.ts';

const enc = new Tiktoken(o200k_base);
const tokens = (s: string) => enc.encode(s).length;
// Latest still-valid moment (13 days after fetched_at): the worst case for note length.
const STALE = new Date(Date.parse(SNAPSHOT.fetched_at) + 13 * 86400000);

// Model lists that maximise notes: retired, escalation-only, junk and real ids.
const JUNK = [
  Array.from({ length: 30 }, (_, i) => ('z9.' + i + '/').repeat(16).slice(0, 64)),
  Array.from({ length: 20 }, (_, i) => (i + ':q-7_x.' + 'k'.repeat(i)).repeat(8).slice(0, 64)),
  Array.from({ length: 20 }, (_, i) => '\u00e9\u4e2d' + 'x'.repeat(40) + i)
];
const REAL = [...SNAPSHOT.retired.slice(0, 6), ...SNAPSHOT.models.map(m => m.id)].slice(0, 30);
const MIXED = [...SNAPSHOT.retired.slice(0, 4), ...SNAPSHOT.models.slice(0, 10).map(m => m.id), ...(JUNK[0] ?? []).slice(0, 6), 'openai', 'claude'];

describe('recommend_flow_model budgets', () => {
  it('tool definition stays within 200 o200k tokens and 300-character description', () => {
    const def = { ...RECOMMEND_TOOL, inputSchema: z.toJSONSchema(recommendInput), annotations: RECOMMEND_ANNOTATIONS };
    const n = tokens(JSON.stringify(def));
    assert.ok(n <= 200, 'definition tokens ' + n);
    assert.ok(RECOMMEND_TOOL.description.length <= 300);
    assert.match(RECOMMEND_TOOL.description, /^Use when /);
  });

  it('schema has no root combinators and bounded names', () => {
    const schema = z.toJSONSchema(recommendInput) as Record<string, unknown>;
    for (const k of ['anyOf', 'oneOf', 'allOf']) assert.equal(schema[k], undefined);
    for (const name of Object.keys(schema.properties as object)) assert.match(name, /^[a-z0-9_]+$/);
    assert.equal(schema.additionalProperties, false);
  });

  it('worst-case response stays within 1,500 bytes and 600 o200k tokens', () => {
    let maxBytes = 0, maxTokens = 0, total = 0, count = 0, worst = '';
    const providerSets = [[], [...SNAPSHOT.policy.route_order], ['openai'], ['xai', 'google', 'meta']];
    for (const task of TASKS) for (const priority of ['quality', 'balanced', 'efficient'] as const)
      for (const role of ['main', 'worker'] as const) for (const providers of providerSets)
        for (const models of [undefined, REAL, MIXED, ...JUNK]) {
          const have = [...providers, ...(models ?? [])].slice(0, 30);
          const json = JSON.stringify(recommendFlowModel({ task, priority, role, ...(have.length ? { have } : {}) }, STALE));
          const bytes = Buffer.byteLength(json), n = tokens(json);
          assert.ok(!/[^\x20-\x7e]/.test(json), 'ASCII only: ' + json);
          if (models && JUNK.includes(models)) assert.ok(models.every(m => !json.includes(m.slice(0, 12))), 'no user text echoed: ' + json);
          if (n > maxTokens) worst = json;
          maxBytes = Math.max(maxBytes, bytes); maxTokens = Math.max(maxTokens, n);
          if (!models) { total += n; count++; }
        }
    console.log(`# worst bytes=${maxBytes} worst tokens=${maxTokens} typical(no models) mean tokens=${Math.round(total / count)}`);
    assert.ok(maxBytes <= 1500, 'worst bytes ' + maxBytes + ': ' + worst);
    assert.ok(maxTokens <= 600, 'worst tokens ' + maxTokens + ': ' + worst);
  });
});
