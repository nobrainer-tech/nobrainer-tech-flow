// Parity with the site's own router (task-router-core.js rank()) and snapshot regeneration.
// Live checks need the website checkout: NB_BENCHMARK_SOURCE=<website>/public_html/ai/benchmark.
// Without it (CI) they skip, and the fixed cases below still pin the expected order.
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { createRequire } from 'node:module';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { recommendFlowModel } from '../../src/advisor/index.ts';
import { TASKS } from '../../src/advisor/schema.ts';
import { SNAPSHOT } from '../../src/advisor/snapshot.ts';

type Entry = { model: string; effort: string | null; eligible?: boolean };
const SOURCE = process.env.NB_BENCHMARK_SOURCE;
const live = SOURCE && existsSync(join(SOURCE, 'task-router-core.js')) ? SOURCE : null;
const SKIP = live ? false : 'NB_BENCHMARK_SOURCE is not set to the website benchmark directory';
const NOW = new Date(Date.parse(SNAPSHOT.fetched_at) + 3600000);
const pickOf = (input: Record<string, unknown>) =>
  ((recommendFlowModel(input, NOW) as { shortlist: Entry[] }).shortlist).filter(e => e.eligible !== false).map(e => e.model + '@' + (e.effort ?? 'default'));

// Captured from the website's rank() on 2026-10-23, fetchedAt 2026-10-23T14:31:44.973108+00:00,
// snapshotId sha256:973ea034541b00585a763f3ca0f3bca57b7cf87e1b02b55ce9315a0b25a9cbe6.
// Date.now() at fetchedAt + 1 h, app opencode via ocx:
// the first three distinct models of its eligible pool.
const CAPTURE_INPUTS = {
  'task-data.json': '17328e0d94178363ebd4973d7d6910ac805c19430210088183856f8f55bd27fc',
  'task-router-core.js': 'ba815adbd3d86ccc40aa4870cd3719fe0c079d6835877a32ce4c258091b9fe68',
  'task-app-defaults.js': 'b48ab17d41a1ffec623c8dc59098cfe2b5e4dc916107374fdab871eaa7755c06',
  'task-model-policy.js': '32d5ce2785b7da143101eda2a0cef81749007eaf68adb4b8986c643e0fe18f71'
};
const FIXED: [Record<string, unknown>, string[]][] = [
  [{ task: 'orchestration', have: ['openai', 'anthropic'] }, ['openai/gpt-6.1-sol@max', 'anthropic/claude-sonnet-5-5@max']],
  [{ task: 'frontend', have: ['anthropic'], priority: 'quality' }, ['anthropic/claude-sonnet-5-5@xhigh', 'anthropic/claude-haiku-5-5@high']],
  [{ task: 'research', have: ['openai', 'anthropic', 'zai'], role: 'main' }, ['anthropic/claude-opus-5-5@high']],
  [{ task: 'writing', have: ['openai'], priority: 'efficient' }, ['openai/gpt-6.1-sol@max']],
  [{ task: 'terminal-coding', have: ['openai', 'anthropic'], priority: 'quality' },
    ['anthropic/claude-sonnet-5-5@max', 'openai/gpt-6.1-sol@max', 'openai/gpt-6-luna@max']],
  ...['coding', 'Coding', 'CODING', 'cOdInG', ' Coding ', '\tcOdInG\n'].map(task =>
    [{ task, have: ['openai', 'anthropic'], priority: 'quality' },
      ['anthropic/claude-sonnet-5-5@max', 'openai/gpt-6.1-sol@max', 'openai/gpt-6-luna@max']] as [Record<string, unknown>, string[]]),
  [{ task: 'instructions' }, ['openai/gpt-6.1-sol@max']]
];

describe('ranking parity with the site router', () => {
  it('matches fixed expectations derived from the site', () => {
    const source = JSON.parse(readFileSync(new URL('../../data/benchmark/SOURCE.json', import.meta.url), 'utf8')) as { inputs: Record<string, string> };
    for (const [name, hash] of Object.entries(CAPTURE_INPUTS)) assert.equal(source.inputs[name], hash, 'fixed baseline capture: ' + name);
    for (const [input, expected] of FIXED) assert.deepEqual(pickOf(input), expected, JSON.stringify(input));
  });

  it('matches the live site rank() across tasks, priorities, roles, plans and model lists', { skip: SKIP }, () => {
    const dir = live as string;
    const data = JSON.parse(readFileSync(join(dir, 'task-data.json'), 'utf8')) as { fetchedAt: string; models: { id: string }[]; measurements: { qualitySource: string }[] };
    const source = JSON.parse(readFileSync(new URL('../../data/benchmark/SOURCE.json', import.meta.url), 'utf8')) as { inputs: Record<string, string> };
    for (const name of Object.keys(CAPTURE_INPUTS)) {
      assert.equal(createHash('sha256').update(readFileSync(join(dir, name))).digest('hex'), source.inputs[name],
        'website input and committed snapshot share exact bytes: ' + name);
    }
    assert.equal(data.fetchedAt, (JSON.parse(readFileSync(new URL('../../data/benchmark/snapshot.json', import.meta.url), 'utf8')) as { fetched_at: string }).fetched_at,
      'website data and committed snapshot share one capture');
    const realNow = Date.now;
    Date.now = () => Date.parse(data.fetchedAt) + 3600000;
    try {
      const R = createRequire(join(dir, 'x.js'))('./task-router-core.js');
      const plans = [['openai', 'anthropic'], ['openai'], ['anthropic'], ['zai', 'kimi', 'minimax', 'copilot'], ['xai', 'google', 'meta', 'zen'], ['copilot'], Object.keys(R.ROUTES)];
      const subsets = [undefined, ['gpt-6.1-sol', 'claude-sonnet-5-5', 'glm-5.3-flash'], ['gpt-6-sol', 'gpt-6-luna', 'kimi-k3']];
      let checked = 0;
      for (const task of TASKS) for (const [priority, pick] of [['quality', 'g'], ['balanced', 'b'], ['efficient', 'e']])
        for (const role of ['main', 'worker']) for (const have of plans) for (const models of subsets) {
          const keep = models && new Set(data.models.filter(m => models.includes(m.id.split('/').pop() as string)).map(m => m.id));
          const site = R.rank(data, { task, have, app: 'opencode', via: 'ocx', pick, role: role === 'main' ? 'main' : 'subs',
            ...(keep ? { overrides: { excluded: data.models.filter(m => !keep.has(m.id)).map(m => m.id) } } : {}) });
          const seen = new Set<string>();
          const expected = (site.ranked as { eligible: boolean; modelId: string; routeId: string; effort: string }[])
            .filter(r => r.eligible && !seen.has(r.modelId) && Boolean(seen.add(r.modelId))).slice(0, 3).map(r => r.routeId + '@' + r.effort);
          const input = { task, priority, role, have: [...have, ...(models ?? [])] };
          assert.deepEqual(pickOf(input), expected, JSON.stringify(input));
          checked++;
        }
      assert.ok(checked >= 500, 'checked ' + checked);
      for (const task of ['coding', 'Coding', 'CODING', 'cOdInG', ' Coding ', '\tcOdInG\n']) {
        const canonical = { task: 'terminal-coding', have: ['openai', 'anthropic'], priority: 'quality' };
        const site = R.rank(data, { ...canonical, app: 'opencode', via: 'ocx', pick: 'g', role: 'subs' });
        const seen = new Set<string>();
        const expected = (site.ranked as { eligible: boolean; modelId: string; routeId: string; effort: string }[])
          .filter(r => r.eligible && !seen.has(r.modelId) && Boolean(seen.add(r.modelId))).slice(0, 3).map(r => r.routeId + '@' + r.effort);
        assert.ok(expected.length > 0, 'site has terminal-coding measurements');
        assert.deepEqual(pickOf({ ...canonical, task }), expected, JSON.stringify(task));
      }
    } finally {
      Date.now = realNow;
    }
  });
});

describe('snapshot regeneration', () => {
  it('is byte-identical across runs and matches the committed snapshot for the same inputs', { skip: SKIP }, () => {
    const script = fileURLToPath(new URL('../../scripts/build-benchmark-snapshot.mjs', import.meta.url));
    const root = fileURLToPath(new URL('../../', import.meta.url));
    const outs = [mkdtempSync(join(root, '.nb-snap-a-')), mkdtempSync(join(root, '.nb-snap-b-'))];
    try {
      for (const out of outs) {
        const res = spawnSync(process.execPath, [script, '--source', live as string, '--out', out], { encoding: 'utf8' });
        assert.equal(res.status, 0, res.stderr);
      }
      for (const name of ['snapshot.json', 'SOURCE.json', 'terminal-bench-LICENSE.txt', 'terminal-bench-2-1-LICENSE.txt']) {
        const fresh = readFileSync(join(outs[0] as string, name));
        assert.ok(fresh.equals(readFileSync(join(outs[1] as string, name))), name + ' is deterministic');
        assert.ok(fresh.equals(readFileSync(new URL('../../data/benchmark/' + name, import.meta.url))), name + ' matches committed bytes');
      }
    } finally {
      for (const out of outs) rmSync(out, { recursive: true, force: true });
    }
  });
});
