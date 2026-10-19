// Parity with the site's own router (task-router-core.js rank()) and snapshot regeneration.
// Live checks need the website checkout: NB_BENCHMARK_SOURCE=<website>/public_html/ai/benchmark.
// Without it (CI) they skip, and the fixed cases below still pin the expected order.
import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { createRequire } from 'node:module';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { recommendFlowModel } from '../../src/advisor/index.ts';
import { TASKS } from '../../src/advisor/schema.ts';
import { SNAPSHOT } from '../../src/advisor/snapshot.ts';

const SNAPSHOT_WITHHELD = (JSON.parse(readFileSync(new URL('../../data/benchmark/snapshot.json', import.meta.url), 'utf8')) as { withheld_sources: Record<string, string> }).withheld_sources;

type Entry = { model: string; effort: string | null; eligible?: boolean };
const SOURCE = process.env.NB_BENCHMARK_SOURCE;
const live = SOURCE && existsSync(join(SOURCE, 'task-router-core.js')) ? SOURCE : null;
const SKIP = live ? false : 'NB_BENCHMARK_SOURCE is not set to the website benchmark directory';
const NOW = new Date(Date.parse(SNAPSHOT.as_of + 'T12:00:00Z'));
const pickOf = (input: Record<string, unknown>) =>
  ((recommendFlowModel(input, NOW) as { shortlist: Entry[] }).shortlist).filter(e => e.eligible !== false).map(e => e.model + '@' + (e.effort ?? 'default'));

// Derived on 2026-10-20 by running the site's rank() on task-data.json (snapshot 2026-10-16)
// without the withheld aa-aligned-v1 rows, Date.now() at fetchedAt + 1 h, app opencode via ocx:
// the first three distinct models of its eligible pool.
const FIXED: [Record<string, unknown>, string[]][] = [
  [{ task: 'orchestration', have: ['openai', 'anthropic'] }, ['openai/gpt-6.1-sol@max', 'anthropic/claude-sonnet-5-5@max']],
  [{ task: 'frontend', have: ['anthropic'], priority: 'quality' }, ['anthropic/claude-sonnet-5-5@xhigh', 'anthropic/claude-haiku-5-5@high']],
  [{ task: 'research', have: ['openai', 'anthropic', 'zai'], role: 'main' }, ['anthropic/claude-opus-5-5@high']],
  [{ task: 'writing', have: ['openai'], priority: 'efficient' }, ['openai/gpt-6.1-sol@max']],
  [{ task: 'terminal-coding', have: ['openai', 'anthropic'], priority: 'quality' },
    ['anthropic/claude-sonnet-5-5@max', 'openai/gpt-6.1-sol@max', 'openai/gpt-6-luna@max']],
  [{ task: 'instructions' }, ['openai/gpt-6.1-sol@max']]
];

describe('ranking parity with the site router', () => {
  it('matches fixed expectations derived from the site', () => {
    for (const [input, expected] of FIXED) assert.deepEqual(pickOf(input), expected, JSON.stringify(input));
  });

  it('matches the live site rank() across tasks, priorities, roles, plans and model lists', { skip: SKIP }, () => {
    const dir = live as string;
    const data = JSON.parse(readFileSync(join(dir, 'task-data.json'), 'utf8')) as { fetchedAt: string; models: { id: string }[]; measurements: { qualitySource: string }[] };
    // The snapshot withholds the Artificial Analysis-derived cohort; compare on the same data.
    data.measurements = data.measurements.filter(r => !(r.qualitySource in SNAPSHOT_WITHHELD));
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
    } finally {
      Date.now = realNow;
    }
  });
});

describe('snapshot regeneration', () => {
  it('is byte-identical across runs and matches the committed snapshot for the same inputs', { skip: SKIP }, () => {
    const script = fileURLToPath(new URL('../../scripts/build-benchmark-snapshot.mjs', import.meta.url));
    const outs = [mkdtempSync(join(tmpdir(), 'nb-snap-a-')), mkdtempSync(join(tmpdir(), 'nb-snap-b-'))];
    try {
      for (const out of outs) {
        const res = spawnSync(process.execPath, [script, '--source', live as string, '--out', out], { encoding: 'utf8' });
        assert.equal(res.status, 0, res.stderr);
      }
      for (const name of ['snapshot.json', 'SOURCE.json', 'terminal-bench-LICENSE.txt', 'terminal-bench-2-1-LICENSE.txt'])
        assert.ok(readFileSync(join(outs[0] as string, name)).equals(readFileSync(join(outs[1] as string, name))), name + ' is deterministic');
      const committed = JSON.parse(readFileSync(new URL('../../data/benchmark/SOURCE.json', import.meta.url), 'utf8')) as { inputs: Record<string, string> };
      const fresh = JSON.parse(readFileSync(join(outs[0] as string, 'SOURCE.json'), 'utf8')) as { inputs: Record<string, string>; snapshot_sha256: string };
      if (JSON.stringify(fresh.inputs) === JSON.stringify(committed.inputs)) {
        const bytes = readFileSync(new URL('../../data/benchmark/snapshot.json', import.meta.url));
        assert.equal(createHash('sha256').update(bytes).digest('hex'), fresh.snapshot_sha256, 'committed snapshot is current');
      }
    } finally {
      for (const out of outs) rmSync(out, { recursive: true, force: true });
    }
  });
});
