#!/usr/bin/env node
// Builds the pinned benchmark snapshot that recommend_flow_model reads.
// Usage: node scripts/build-benchmark-snapshot.mjs --source <public_html/ai/benchmark> [--out <dir>]
// Static parts of the site's routing (model recency policy, access routes, role exclusions,
// successor candidates, quality-band spans) are computed here with the site's own modules,
// so the runtime port only repeats the per-request ranking. Output is byte-deterministic.
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const SITE_URL = 'https://nobrainer.tech/ai/benchmark/';
const LICENCES = ['terminal-bench-LICENSE.txt', 'terminal-bench-2-1-LICENSE.txt'];
const MODULES = ['task-router-core.js', 'task-app-defaults.js', 'task-model-policy.js'];
const DAY = 86400000;

function args(argv) {
  const out = {};
  for (let i = 0; i < argv.length; i += 2) {
    if (!['--source', '--out'].includes(argv[i]) || !argv[i + 1]) throw new Error('Usage: build-benchmark-snapshot.mjs --source <dir> [--out <dir>]');
    out[argv[i].slice(2)] = argv[i + 1];
  }
  if (!out.source) throw new Error('Missing --source <path to public_html/ai/benchmark>');
  return out;
}

const sha256 = buf => createHash('sha256').update(buf).digest('hex');
const finite = v => typeof v === 'number' && Number.isFinite(v);
const positive = v => finite(v) && v > 0;
const ascii = s => String(s).replace(/[\u2013\u2014]/g, '-').replace(/[\u2018\u2019]/g, "'").replace(/[^\x20-\x7e]/g, '');

function git(source, ...cmd) {
  try { return execFileSync('git', ['-C', source, ...cmd], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim(); } catch { return null; }
}

export function build(source) {
  const read = name => readFileSync(join(source, name));
  const inputs = ['task-data.json', ...MODULES, ...LICENCES];
  const hashes = Object.fromEntries(inputs.map(name => [name, sha256(read(name))]));
  const D = JSON.parse(read('task-data.json').toString('utf8'));
  if (D.schema !== 'nobrainer-open-task-data/1') throw new Error('Unsupported task data schema: ' + D.schema);
  const R = createRequire(join(resolve(source), 'x.js'))('./task-router-core.js');
  const P = R.MODEL_POLICY, A = R.APP_DEFAULTS, AP = R.ACCESS_POLICY;
  const fetchedAt = Date.parse(D.fetchedAt);
  if (!finite(fetchedAt)) throw new Error('task-data.json has no valid fetchedAt');

  // Every static access route, from the site's routesFor with all plans selected.
  const allRoutes = R.stateOf({ have: A.ROUTE_ORDER, app: 'opencode', via: 'ocx' });
  const routesOf = m => Object.fromEntries(R.routesFor(m, allRoutes).map(p => [p.route, p.routeId]));
  const modelKey = m => String(m.canonical || m.id || '').split('/').pop();
  const lineageKey = m => String(m.canonical || m.id || '').toLowerCase().replace(/\d+(?:\.\d+)*(?:-\d+)?/g, '#');
  const dated = m => /^\d{4}-\d{2}-\d{2}$/.test(m.releaseDate || '');
  const roleOk = (m, list) => !list.some(x => modelKey(m).toLowerCase().includes(x));
  // Mirrors successorFor in task-router-core.js: an explicit successor wins; otherwise newer
  // dated releases of the same lineage, newest first. Availability is checked per request.
  function successors(m) {
    const explicit = AP.successors[modelKey(m)];
    if (explicit) return D.models.filter(x => x.id !== m.id && modelKey(x) === explicit).map(x => x.id);
    if (!dated(m)) return [];
    return D.models.filter(x => x.id !== m.id && lineageKey(x) === lineageKey(m) && dated(x) && x.releaseDate > m.releaseDate)
      .sort((a, b) => b.releaseDate.localeCompare(a.releaseDate)).map(x => x.id);
  }
  const reachable = new Map(D.models.map(m => [m.id, routesOf(m)]).filter(([, r]) => Object.keys(r).length));
  const current = new Set(D.models.filter(m => P.isCurrent(m, D.models)).map(m => m.id));
  const models = D.models.filter(m => reachable.has(m.id)).map(m => ({
    id: m.id, family: ascii(m.family), routes: reachable.get(m.id), fallback: P.isFallback(m),
    main: roleOk(m, AP.mainExcludedFamilies), worker: roleOk(m, AP.workerEscalationFamilies),
    successors: successors(m).filter(id => reachable.has(id))
  }));
  const retired = [...new Set(D.models.filter(m => !current.has(m.id) && !reachable.has(m.id)).map(m => modelKey(m).toLowerCase()))].sort();

  // Rows the site could ever rank at fetch time (filters in rank() that do not depend on the request).
  const byId = new Map(D.models.map(m => [m.id, m]));
  const sourceById = new Map(D.sources.map(s => [s.id, s]));
  const taskIds = D.tasks.map(t => t.id);
  const ageOk = r => {
    const at = Date.parse(r.publishedAt || sourceById.get(r.qualitySource)?.publishedAt || '');
    return finite(at) && (fetchedAt - at) / DAY <= D.policy.maxSourceAgeDays;
  };
  const effortOk = (r, m) => ['none', 'default'].includes(r.effort) || !(m.efforts || []).length || m.efforts.includes(r.effort);
  const scored = D.measurements.filter(r => taskIds.includes(r.task) && finite(r.score));
  const rows = scored.filter(r => current.has(r.modelId) && reachable.has(r.modelId) && ageOk(r) && effortOk(r, byId.get(r.modelId)) &&
    !(r.costKind === 'observed' && r.successRate === 0))
    .map(r => [r.id, r.modelId, r.task, r.effort, r.score, finite(r.lower) ? r.lower : r.score, finite(r.upper) ? r.upper : r.score,
      r.qualitySource, positive(r.cost) ? r.cost : null, r.costKind, positive(r.time) ? r.time : null, r.timeKind,
      r.harness || null, positive(r.successCost) ? r.successCost : null]);
  // Quality-band span per task cohort: every current model's scored row, as in rank().
  const tasks = Object.fromEntries(D.tasks.map(t => {
    const span = {};
    for (const src of [...new Set(scored.filter(r => r.task === t.id).map(r => r.qualitySource))].sort()) {
      const s = scored.filter(r => r.task === t.id && r.qualitySource === src && current.has(r.modelId)).map(r => r.score);
      if (s.length) span[src] = Math.max(...s) - Math.min(...s);
    }
    return [t.id, { label: ascii(t.label), scale: ascii(t.qualityLabel), span }];
  }));
  const used = new Set(rows.map(r => r[7]));
  const sources = Object.fromEntries(D.sources.filter(s => used.has(s.id)).map(s => [s.id,
    { label: ascii(s.label), url: s.url, license: ascii(s.license), published: s.publishedAt || null }]));
  const snapshot = {
    schema: 'nobrainer-flow-benchmark-snapshot/1', source: SITE_URL, as_of: D.fetchedAt.slice(0, 10),
    fetched_at: D.fetchedAt, compiled_at: D.compiledAt || null, data_snapshot_id: D.snapshotId || null,
    policy: { quality_band_fraction: D.policy.qualityBandFraction, max_source_age_days: D.policy.maxSourceAgeDays,
      source_priority: D.policy.qualitySourcePriority, route_order: AP.routeOrder, apps: A.APPS,
      native_routes: { codex: ['openai'], claude: ['anthropic'], copilot: ['copilot'] },
      default_providers: R.DEFAULT.have, providers: A.ROUTES, api_access_note: ascii(A.API_ACCESS_NOTE) },
    jobs: R.JOBS, tasks, sources, retired, models,
    row_fields: ['id', 'model', 'task', 'effort', 'score', 'lower', 'upper', 'source', 'cost', 'cost_kind', 'time', 'time_kind', 'harness', 'success_cost'],
    rows,
    attribution: [
      'Derived by NoBrainer from released third-party data; the source publishers do not endorse these recommendations.',
      'Arena ratings: lmarena-ai leaderboard-dataset, CC BY 4.0; values filtered and transformed.',
      'Terminal-Bench submissions: harbor-framework terminal-bench and terminal-bench-2-1, Apache 2.0; licence copies included.',
      'Model catalog and prices: models.dev, MIT.',
      'Own agent telemetry: NoBrainer aggregated metadata; no prompts or content.'
    ]
  };
  const json = JSON.stringify(snapshot) + '\n';
  const repo = git(source, 'rev-parse', '--show-toplevel');
  const sourceInfo = {
    source_url: SITE_URL, source_path: repo ? relative(repo, resolve(source)) : null,
    website_commit: git(source, 'rev-parse', 'HEAD'),
    website_dirty: repo ? Boolean(git(source, 'status', '--porcelain', '--', '.')) : null,
    snapshot_date: snapshot.as_of, snapshot_sha256: sha256(Buffer.from(json)), inputs: hashes
  };
  return { json, sourceInfo };
}

function main() {
  const opts = args(process.argv.slice(2));
  const here = dirname(fileURLToPath(import.meta.url));
  const out = resolve(opts.out || join(here, '..', 'data', 'benchmark'));
  const { json, sourceInfo } = build(resolve(opts.source));
  mkdirSync(out, { recursive: true });
  writeFileSync(join(out, 'snapshot.json'), json);
  writeFileSync(join(out, 'SOURCE.json'), JSON.stringify(sourceInfo, null, 2) + '\n');
  for (const name of LICENCES) copyFileSync(join(opts.source, name), join(out, name));
  console.log(JSON.stringify({ out, bytes: Buffer.byteLength(json), sha256: sourceInfo.snapshot_sha256, as_of: sourceInfo.snapshot_date }));
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();
