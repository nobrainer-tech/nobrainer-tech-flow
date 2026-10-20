import { rankTask, routing, type RankState, type Ranked } from './rank.ts';
import { PRIORITY_CODES, parseInput } from './schema.ts';
import { SNAPSHOT as S, expiresAt, type SnapshotModel } from './snapshot.ts';

export const MAX_RESPONSE_BYTES = 1500;
const SHORTLIST = 3;
const API_ROUTES = ['xai', 'google', 'meta'];
const EXPIRED_NOTE = 'Snapshot expired. Refresh the released sources before generating a routing policy.';
const QUALITY_FIRST = 'Quality first: highest quality lower bound; cost and time do not decide.';
// Common names for the site's provider ids (task-app-defaults.js ROUTES) and client apps (APPS).
const PROVIDER_ALIASES: Record<string, string> = { chatgpt: 'openai', 'z.ai': 'zai', glm: 'zai', grok: 'xai', gemini: 'google', 'opencode-zen': 'zen' };
const APP_ALIASES: Record<string, string> = { 'claude-code': 'claude', 'github-copilot': 'copilot', cursor: 'other', windsurf: 'other', gemini_cli: 'other', 'gemini-cli': 'other' };

const keyOf = (id: string) => id.split('/').pop()?.toLowerCase() ?? '';
const round = (v: number, digits: number) => Number(v.toFixed(digits));
const sig = (v: number) => Number(v.toPrecision(3));

function matchModels(wanted: string): SnapshotModel[] {
  const s = wanted.trim().toLowerCase();
  return S.models.filter(m => m.id.toLowerCase() === s || keyOf(m.id) === s || m.family.toLowerCase() === s ||
    Object.values(m.routes).some(r => r.toLowerCase() === s || keyOf(r) === s));
}

/** The provider whose route ID equals `wanted` exactly, if any. */
function routeProvider(wanted: string): string | null {
  for (const m of S.models) {
    for (const [provider, route] of Object.entries(m.routes)) if (route.toLowerCase() === wanted) return provider;
  }
  return null;
}

function evidence(r: Ranked, eligible: boolean) {
  return {
    model: r.routeId,
    effort: r.effort === 'default' ? null : r.effort,
    quality: round(r.score, 1),
    ...(r.upper > r.lower ? { range: [round(r.lower, 1), round(r.upper, 1)] } : {}),
    cost_usd: r.cost == null ? null : sig(r.cost),
    ...(r.costKind === 'observed' && r.successCost != null ? { cost_per_success_usd: sig(r.successCost) } : {}),
    cost_kind: r.costKind,
    seconds: r.time == null ? null : Math.round(r.time),
    time_kind: r.timeKind,
    ...(r.harness ? { harness: r.harness } : {}),
    ...(eligible ? {} : { eligible: false })
  };
}

function list(label: string, names: string[]): string | null {
  if (!names.length) return null;
  const shown = names.slice(0, 3).join(', ');
  return label + ': ' + shown + (names.length > 3 ? ' +' + (names.length - 3) + ' more' : '') + '.';
}

export function recommendFlowModel(input: unknown, now: Date = new Date()): Record<string, unknown> {
  const req = parseInput(input);
  const task = S.jobs[req.task] ?? req.task;
  const priority = req.priority ?? 'balanced';
  const role = req.role ?? 'worker';
  // The website refuses an expired snapshot (rank(), fetchedAt + 14 days); so does the advisor.
  // Freshness lives in structured fields, which the note trimming in fit() never touches.
  const expiry = expiresAt();
  const fresh = { expired: !expiry || now.getTime() > expiry.getTime(), expires: expiry?.toISOString().slice(0, 10) ?? null };
  if (fresh.expired) {
    return { task, priority, role, ...fresh, shortlist: [], note: EXPIRED_NOTE, snapshot: S.as_of, snapshot_sha: S.sha.slice(0, 8), source: S.source };
  }
  const notes: string[] = [];
  // Each "have" entry is a provider id (or common alias); anything else is matched as a model.
  const providers: string[] = [];
  const apps: string[] = [];
  const matched: { name: string; at: number; models: SnapshotModel[]; route: string | null }[] = [];
  (req.have ?? []).forEach((name, at) => {
    const s = name.trim().toLowerCase();
    // An exact provider id wins ("copilot" is the plan); "github-copilot" names the app.
    const provider = S.policy.route_order.includes(s) ? s : PROVIDER_ALIASES[s];
    const app = provider ? undefined : S.policy.apps.includes(s) ? s : APP_ALIASES[s];
    if (app) apps.push(app);
    if (provider) providers.push(provider);
    else if (!app) matched.push({ name, at, models: matchModels(name), route: routeProvider(s) });
  });
  // An app alone selects its native plans (codex: openai, claude: anthropic, copilot: copilot);
  // opencode and other (e.g. Cursor) allow every route, like the site's NATIVE map.
  const restrict = apps.length && apps.every(a => S.policy.native_routes[a]) ? [...new Set(apps.flatMap(a => S.policy.native_routes[a] ?? []))] : null;
  // A qualified route ID ("github-copilot/gpt-6.1-sol") keeps its provider; a bare model name
  // may be reached through any route.
  const routed = matched.every(m => m.route) ? [...new Set(matched.map(m => m.route as string))] : S.policy.route_order;
  const have = providers.length ? providers : matched.length ? routed : restrict ?? S.policy.default_providers;
  if (providers.length && restrict && !providers.some(p => restrict.includes(p))) notes.push('These apps reach none of the given providers natively.');
  if (!providers.length && !matched.length && !restrict) notes.push('No providers or models given; assumed site defaults: ' + have.join(', ') + '.');
  const allowed = new Set(matched.flatMap(x => x.models.map(m => m.id)));
  const state: RankState = {
    task, have, native: restrict, role: role === 'main' ? 'main' : 'subs',
    excluded: new Set(matched.length ? S.models.filter(m => !allowed.has(m.id)).map(m => m.id) : [])
  };
  const result = rankTask(S, state, PRIORITY_CODES[priority]);
  // The pick pool first; when it holds fewer than three models, the site's remaining display
  // order (ranked, quality-sorted) fills the list, flagged eligible: false. Best variant per model.
  const inPool = new Set(result.pool.map(r => r.id));
  const fill = result.pool.length ? result.ranked.filter(r => !inPool.has(r.id) && !r.fallbackOnly) : [];
  const seen = new Set<string>();
  const shortlist = [...result.pool, ...fill].filter(r => !seen.has(r.model) && Boolean(seen.add(r.model))).slice(0, SHORTLIST);

  const taskRows = S.table.filter(r => r.task === task);
  if (S.tasks[task]?.withheld) notes.push('Artificial Analysis-derived ' + task + ' scores are not redistributed here; see ' + S.source + '.' +
    (taskRows.length ? '' : task === 'coding' ? ' For a shortlist, use task terminal-coding (Terminal-Bench).' : ''));
  else if (!taskRows.length) notes.push('No current ' + task + ' measurements in this snapshot.');
  if (taskRows.length && !shortlist.length) notes.push('No available model has qualifying ' + task + ' data in this snapshot.');
  if (matched.length) {
    const { routeFor, roleAllowed } = routing(S, state);
    const listed = new Set(shortlist.map(r => r.model));
    const ranked = new Set(result.ranked.filter(r => !r.fallbackOnly).map(r => r.model));
    const groups: Record<string, string[]> = { unknown: [], retired: [], nodata: [], role: [], unreachable: [], fallback: [] };
    // Never echo user text: unmatched names are reported by position, matches by snapshot id.
    matched.forEach(({ name, at, models }) => {
      const model = models[0];
      const retired = model ? undefined : S.retired.find(k => k === keyOf(name.trim()));
      const key = model ? keyOf(model.id) : retired ?? 'have[' + at + ']';
      const group = !model ? (retired ? 'retired' : 'unknown')
        : models.some(m => listed.has(m.id) || ranked.has(m.id)) ? null
        : !taskRows.some(r => r.model === model.id) ? 'nodata'
        : !roleAllowed(model) ? 'role'
        : !routeFor(model) ? 'unreachable'
        : 'fallback';
      if (group && !groups[group]?.includes(key)) groups[group]?.push(key);
    });
    notes.push(...[
      list('Not in snapshot', groups.unknown ?? []),
      list('Retired by site model policy', groups.retired ?? []),
      list('No ' + task + ' data', groups.nodata ?? []),
      list(role === 'main' ? 'Not ranked as main (worker-only)' : 'Escalation-only, not ranked for workers', groups.role ?? []),
      list('Not reachable with these providers', groups.unreachable ?? []),
      list('Fallback only (newer successor reachable)', groups.fallback ?? [])
    ].filter((x): x is string => x != null));
  }
  if (shortlist.length) notes.push('Cost and time are per-task reference figures, not invoices.');
  if (shortlist.some(r => API_ROUTES.includes(r.route))) notes.push('xai/google/meta routes need separate API access.');

  const out: Record<string, unknown> = {
    task, priority, role, ...fresh,
    cohort: result.cohort,
    scale: result.cohort ? S.tasks[task]?.scale ?? null : null,
    shortlist: shortlist.map(r => evidence(r, inPool.has(r.id))),
    why: priority === 'quality' ? (shortlist.length ? QUALITY_FIRST : null) : result.reason,
    snapshot: S.as_of, snapshot_sha: S.sha.slice(0, 8), source: S.source
  };
  return fit(out, notes.join(' '));
}

// Hard byte budget: the note is the only variable-length text, so trim it last.
function fit(out: Record<string, unknown>, note: string): Record<string, unknown> {
  const bytes = (o: unknown) => Buffer.byteLength(JSON.stringify(o));
  if (!note) return out;
  const withNote = (text: string) => {
    const { snapshot, snapshot_sha, source, ...head } = out;
    return { ...head, note: text, snapshot, snapshot_sha, source };
  };
  let text = note, result = withNote(text);
  while (bytes(result) > MAX_RESPONSE_BYTES && text.length > 3) {
    text = text.slice(0, Math.max(0, text.length - Math.max(8, bytes(result) - MAX_RESPONSE_BYTES) - 3)).trimEnd() + '...';
    result = withNote(text);
  }
  return result;
}
