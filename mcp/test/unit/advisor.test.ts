import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { AdvisorInputError, recommendFlowModel, snapshotInfo, STALE_AFTER_DAYS } from '../../src/advisor/index.ts';

type Entry = { model: string; effort: string | null; quality: number; cost_usd: number | null; seconds: number | null; eligible?: boolean };
type Out = { task: string; shortlist: Entry[]; note?: string; why: string | null; snapshot: string; snapshot_sha: string; source: string; cohort: string | null };

const SNAPSHOT_DAY = new Date('2026-10-17T12:00:00Z');
const run = (input: unknown, now = SNAPSHOT_DAY) => recommendFlowModel(input, now) as unknown as Out;
const dataUrl = (name: string) => new URL('../../data/benchmark/' + name, import.meta.url);
const sourceInfo = JSON.parse(readFileSync(dataUrl('SOURCE.json'), 'utf8')) as { snapshot_date: string; snapshot_sha256: string };
const snapshot = JSON.parse(readFileSync(dataUrl('snapshot.json'), 'utf8')) as { row_fields: string[]; rows: unknown[][] };

describe('recommend_flow_model ranking', () => {
  it('returns a ranked shortlist with evidence taken from the snapshot', () => {
    const out = run({ task: 'terminal-coding', have: ['openai', 'anthropic'], priority: 'quality' });
    assert.equal(out.shortlist.length, 3);
    const ids = new Set(snapshot.rows.filter(r => r[2] === 'terminal-coding').map(r => r[1] + '@' + r[3] + '@' + Number((r[4] as number).toFixed(1))));
    for (const e of out.shortlist) {
      const id = e.model.split('/').pop();
      assert.ok([...ids].some(x => x.endsWith('/' + id + '@' + e.effort + '@' + e.quality)), 'evidence for ' + e.model + ' comes from a snapshot row');
    }
    const qualities = out.shortlist.map(e => e.quality);
    assert.deepEqual(qualities, qualities.slice().sort((a, b) => b - a), 'quality priority sorts by quality');
  });

  it('maps site job aliases to task ids for direct callers', () => {
    assert.equal(run({ task: 'agentic' }).task, 'orchestration');
    assert.equal(run({ task: 'bulk' }).task, 'writing');
  });

  it('maps client apps in have to their native routes, like the site', () => {
    const codex = run({ task: 'writing', have: ['codex'] });
    assert.ok(codex.shortlist.length > 0);
    for (const e of codex.shortlist) assert.match(e.model, /^openai\//);
    assert.doesNotMatch(codex.note ?? '', /assumed site defaults/);
    const claude = run({ task: 'writing', have: ['Claude-Code'] });
    assert.ok(claude.shortlist.length > 0);
    for (const e of claude.shortlist) assert.match(e.model, /^anthropic\//);
    // An app restricts given providers to its native ones.
    const both = run({ task: 'writing', have: ['codex', 'openai', 'anthropic'] });
    for (const e of both.shortlist) assert.match(e.model, /^openai\//);
    assert.match(run({ task: 'writing', have: ['claude', 'openai'] }).note ?? '', /reach none of the given providers/);
    // Cursor maps to the site's "other" app: every route stays open.
    assert.deepEqual(run({ task: 'writing', have: ['cursor', 'zai'] }).shortlist.map(e => e.model.split('/')[0]).every(r => r === 'zai'), true);
  });

  it('treats provider ids and common aliases in have as plans', () => {
    for (const e of run({ task: 'writing', have: ['ChatGPT'] }).shortlist) assert.match(e.model, /^openai\//);
  });

  it('flags fill rows outside the pick pool as not eligible', () => {
    const out = run({ task: 'orchestration', have: ['openai', 'anthropic'] });
    assert.equal(out.shortlist[0]?.eligible, undefined, 'the pick itself is eligible');
    assert.ok(out.shortlist.slice(1).every(e => e.eligible === false || e.eligible === undefined));
  });
});

describe('recommend_flow_model notes', () => {
  it('notes requested models that are unknown, retired, escalation-only or without task data', () => {
    const out = run({ task: 'writing', have: ['gpt-6.1-sol', 'not-a-model-xyz', 'claude-opus-4-8', 'claude-opus-5-5'] });
    assert.ok(out.shortlist.length > 0 && out.shortlist.every(e => e.model.endsWith('gpt-6.1-sol')));
    assert.match(out.note ?? '', /Not in snapshot: have\[1\]\./);
    assert.doesNotMatch(JSON.stringify(out), /not-a-model-xyz/, 'user free text is never echoed');
    assert.match(out.note ?? '', /Retired by site model policy: claude-opus-4-8\./);
    assert.match(out.note ?? '', /Escalation-only, not ranked for workers: claude-opus-5-5\./);
  });

  it('notes a requested model the given providers cannot reach', () => {
    const out = run({ task: 'writing', have: ['openai', 'claude-sonnet-5-5', 'gpt-6.1-sol'] });
    assert.match(out.note ?? '', /Not reachable with these providers: claude-sonnet-5-5\./);
  });

  it('says when it assumed the site default providers', () => {
    assert.match(run({ task: 'writing' }).note ?? '', /assumed site defaults/);
    assert.doesNotMatch(run({ task: 'writing', have: ['openai'] }).note ?? '', /assumed site defaults/);
  });

  it('adds a stale note only after the threshold', () => {
    const fresh = run({ task: 'writing', have: ['openai'] });
    assert.doesNotMatch(fresh.note ?? '', /stale/);
    const later = new Date(Date.parse(fresh.snapshot + 'T00:00:00Z') + 100 * 86400000);
    const stale = run({ task: 'writing', have: ['openai'] }, later);
    assert.match(stale.note ?? '', new RegExp('Snapshot is 100 days old \\(stale after ' + STALE_AFTER_DAYS + '\\)'));
    assert.ok(stale.shortlist.length > 0, 'stale data still ranks, with a note');
  });

  it('returns an empty shortlist with a note when no available model has data', () => {
    const none = run({ task: 'writing', have: ['not-a-model-xyz'] });
    assert.deepEqual(none.shortlist, []);
    assert.match(none.note ?? '', /No available model has qualifying writing data/);
  });

  it('withholds Artificial Analysis-derived scores and points to the site', () => {
    const coding = run({ task: 'coding', have: ['openai', 'anthropic'] });
    assert.deepEqual(coding.shortlist, []);
    assert.match(coding.note ?? '', /Artificial Analysis-derived coding scores are not redistributed here; see https:\/\/nobrainer\.tech\/ai\/benchmark\/\. For a shortlist, use task terminal-coding \(Terminal-Bench\)\./);
    const orch = run({ task: 'orchestration', have: ['openai', 'anthropic'] });
    assert.equal(orch.cohort, 'arena-agent');
    assert.match(orch.note ?? '', /not redistributed here/);
    const text = readFileSync(dataUrl('snapshot.json'), 'utf8');
    assert.ok(!snapshot.rows.some(r => r[7] === 'aa-aligned-v1'), 'no AA-derived rows');
    assert.doesNotMatch(text, /"ii"|artificialanalysis\.ai\/models/);
  });

  it('never invents values: unknown time stays null', () => {
    const out = run({ task: 'frontend', have: ['anthropic'], priority: 'quality' });
    const haiku = out.shortlist.find(e => e.model.includes('haiku'));
    assert.ok(haiku);
    assert.equal(haiku.seconds, null);
  });
});

describe('recommend_flow_model input errors', () => {
  it('throws INVALID_INPUT with why and fix for an unknown task type', () => {
    assert.throws(() => run({ task: 'cooking' }), (e: unknown) => {
      assert.ok(e instanceof AdvisorInputError);
      assert.equal(e.code, 'INVALID_INPUT');
      assert.match(e.why, /task/);
      assert.match(e.fix, /coding/);
      return true;
    });
  });

  it('accepts a differently cased task from direct callers', () => {
    assert.equal(run({ task: ' Coding ' }).task, 'coding');
  });

  it('rejects unknown fields, oversize lists and tasks without data', () => {
    assert.throws(() => run({ task: 'coding', extra: true }), AdvisorInputError);
    assert.throws(() => run({ task: 'coding', providers: ['openai'] }), AdvisorInputError);
    assert.throws(() => run({ task: 'coding', have: Array(31).fill('x') }), AdvisorInputError);
    assert.throws(() => run({ task: 'terminal-coding-2.1' }), AdvisorInputError);
  });
});

describe('snapshot identity', () => {
  it('reports the date and hash recorded in SOURCE.json', () => {
    const bytes = readFileSync(dataUrl('snapshot.json'));
    const sha = createHash('sha256').update(bytes).digest('hex');
    assert.equal(sha, sourceInfo.snapshot_sha256, 'SOURCE.json matches the committed snapshot');
    const info = snapshotInfo();
    assert.deepEqual(info, { date: sourceInfo.snapshot_date, sha: sha.slice(0, 8), source: 'https://nobrainer.tech/ai/benchmark/', stale_after_days: 45 });
    const out = run({ task: 'coding' });
    assert.equal(out.snapshot, info.date);
    assert.equal(out.snapshot_sha, info.sha);
    assert.equal(out.source, info.source);
  });

  it('keeps the snapshot small and ASCII-only', () => {
    const bytes = readFileSync(dataUrl('snapshot.json'));
    assert.ok(bytes.length < 150 * 1024, 'snapshot is ' + bytes.length + ' bytes');
    assert.ok(!/[^\x00-\x7f]/.test(bytes.toString('utf8')));
  });
});
