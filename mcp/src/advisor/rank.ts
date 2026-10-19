// Port of rank() in the site's task-router-core.js (nobrainer.tech/ai/benchmark/) for its three
// public priorities: g (quality), b (balanced), e (efficient). Request-independent filters
// (recency policy, source age, effort catalog, zero-success runs, band spans) were applied
// by scripts/build-benchmark-snapshot.mjs with the site's own modules. Legacy codes
// (c/f/gc/gf/cf), owner soft preferences, manual overrides and quota state are out of scope.
import type { LoadedSnapshot, Row, SnapshotModel } from './snapshot.ts';

export type Code = 'g' | 'b' | 'e';
export type RankState = { task: string; have: string[]; native: string[] | null; role: 'main' | 'subs'; excluded: Set<string> };
export type Ranked = Row & { route: string; routeId: string; fallbackOnly: boolean; cohort: string };
export type RankResult = { pool: Ranked[]; ranked: Ranked[]; chosen: Ranked | null; cohort: string | null; reason: string | null };

const TELEMETRY = ['telemetry', 'telemetry-api'];
const EFFORT_ORDER = ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max', 'default'];
const positive = (v: number | null): v is number => typeof v === 'number' && Number.isFinite(v) && v > 0;
const completeEvidence = (r: Ranked) => positive(r.cost) && positive(r.time) &&
  ['observed', 'estimate', ...TELEMETRY].includes(r.costKind) && ['observed', 'estimate', ...TELEMETRY].includes(r.timeKind);

// routesFor/routeFor, roleAllowed and successorFor from the site, on precomputed model fields.
export function routing(S: LoadedSnapshot, state: RankState) {
  const order = S.policy.route_order;
  const routePriority = (r: string) => { const i = order.indexOf(r); return i < 0 ? 999 : i; };
  // Selected plans in owner route order; named apps restrict them to their native routes
  // (the site's allowedRoutes with via: native). Without an app: via ocx, no restriction.
  const wanted = [...new Set(state.have)].filter(r => order.includes(r) && (!state.native || state.native.includes(r)))
    .sort((a, b) => routePriority(a) - routePriority(b));
  const routeFor = (m: SnapshotModel) => {
    if (state.excluded.has(m.id)) return null;
    const route = wanted.find(r => m.routes[r]);
    return route ? { route, routeId: m.routes[route] as string } : null;
  };
  const roleAllowed = (m: SnapshotModel) => state.role === 'main' ? m.main : m.worker;
  const fallbackOnly = (m: SnapshotModel) => m.fallback || m.successors.some(id => {
    const x = S.byId.get(id);
    return Boolean(x && routeFor(x) && roleAllowed(x));
  });
  return { routePriority, routeFor, roleAllowed, fallbackOnly };
}

export function rankTask(S: LoadedSnapshot, state: RankState, code: Code): RankResult {
  const { routePriority, routeFor, roleAllowed, fallbackOnly } = routing(S, state);

  let ranked: Ranked[] = S.table.filter(r => r.task === state.task).flatMap(r => {
    const m = S.byId.get(r.model);
    if (!m || !roleAllowed(m)) return [];
    const route = routeFor(m);
    if (!route) return [];
    return [{ ...r, ...route, fallbackOnly: fallbackOnly(m), cohort: r.source + (r.harness ? ':' + r.harness : '') }];
  });
  // One task uses one source metric; policy.qualitySourcePriority picks the cohort.
  const prio = S.policy.source_priority;
  const rankOf = (s: string) => { const i = prio.indexOf(s); return i < 0 ? 99 : i; };
  const cohorts = [...new Set(ranked.map(r => r.source))].sort((a, b) => rankOf(a) - rankOf(b) || a.localeCompare(b));
  const kept = cohorts[0] ?? null;
  if (kept) ranked = ranked.filter(r => r.source === kept);
  const span = kept ? S.tasks[state.task]?.span[kept] ?? 0 : 0;
  const band = S.policy.quality_band_fraction;
  const primary = ranked.filter(r => !r.fallbackOnly);
  const bestLower = primary.length ? Math.max(...primary.map(r => r.lower)) : null;
  const admits = (r: Ranked, boundary: number | null, leader: number) => boundary != null &&
    (r.upper > r.lower ? r.score >= boundary && r.upper >= leader : r.lower >= boundary);
  const floor = bestLower == null ? null : bestLower - span * band;
  const wideFloor = bestLower == null ? null : bestLower - span * band * 2;
  const qualified = primary.filter(r => admits(r, floor, bestLower ?? 0));
  const wide = primary.filter(r => admits(r, wideFloor, bestLower ?? 0));

  const moneyKey = (r: Ranked) => r.costKind === 'observed' && positive(r.successCost) ? r.successCost : r.cost ?? Infinity;
  const costSort = (a: Ranked, b: Ranked) => {
    const delta = moneyKey(a) - moneyKey(b);
    if (delta) return delta;
    if (a.model === b.model && a.costKind === 'estimate' && b.costKind === 'estimate') {
      const effortDelta = EFFORT_ORDER.indexOf(a.effort) - EFFORT_ORDER.indexOf(b.effort);
      if (effortDelta) return effortDelta;
    }
    return b.lower - a.lower || a.id.localeCompare(b.id);
  };
  const qualitySort = (a: Ranked, b: Ranked) => b.lower - a.lower || costSort(a, b);
  const comparable = (rows: Ranked[]) => {
    // Without an explicit plan order, direct plans precede Copilot and gateways; two or more
    // own-telemetry rows are compared only among themselves.
    const direct = rows.filter(r => routePriority(r.route) < routePriority('copilot'));
    const usable = direct.length ? direct : rows;
    const own = usable.filter(r => TELEMETRY.includes(r.costKind));
    return own.length >= 2 ? own : usable;
  };
  const evidenceGroup = (rows: Ranked[]) => {
    const sourceOrder = (a: Ranked, b: Ranked) => b.lower - a.lower || moneyKey(a) - moneyKey(b) || (a.time as number) - (b.time as number) || a.id.localeCompare(b.id);
    const groups = new Map<string, Ranked[]>();
    for (const r of comparable(rows.filter(completeEvidence))) {
      const key = JSON.stringify([r.cohort, r.costKind, r.timeKind]);
      groups.set(key, [...(groups.get(key) ?? []), r]);
    }
    const head = (g: Ranked[]) => g.slice().sort(sourceOrder)[0] as Ranked;
    return [...groups.values()].sort((a, b) => sourceOrder(head(a), head(b)))[0] ?? [];
  };
  // Dense ordinal ranks give equal values equal weight, irrespective of row order/count.
  const ordinalSort = (rows: Ranked[], balanced: boolean) => {
    const valueRank = (value: (r: Ranked) => number, descending = false) => {
      const values = [...new Set(rows.map(value))].sort((a, b) => descending ? b - a : a - b);
      const ranks = new Map(values.map((v, i) => [v, i]));
      return (r: Ranked) => ranks.get(value(r)) as number;
    };
    const costRank = valueRank(moneyKey), timeRank = valueRank(r => r.time as number), qualityRank = valueRank(r => r.lower, true);
    const sum = (r: Ranked) => costRank(r) + timeRank(r) + (balanced ? qualityRank(r) : 0);
    return rows.slice().sort((a, b) => sum(a) - sum(b) || (balanced ? b.lower - a.lower : 0) || moneyKey(a) - moneyKey(b) ||
      (a.time as number) - (b.time as number) || b.lower - a.lower || a.id.localeCompare(b.id));
  };

  const qualityWinner = primary.slice().sort(qualitySort)[0] ?? null;
  let pool = code === 'g' ? primary.slice().sort(qualitySort) : ordinalSort(evidenceGroup(code === 'b' ? qualified : wide), code === 'b');
  let reason: string | null = null;
  if (code !== 'g') {
    reason = pool.length ? (code === 'b'
      ? 'Equal ordinal ranks of quality lower bound, cost and time within the normal quality band.'
      : 'Equal ordinal ranks of cost and time within the wider quality band.') + ' Comparable harness and evidence kinds after plan order; a policy heuristic.'
      : code === 'b' && qualityWinner ? 'Cost or time evidence is missing or incomplete within the normal quality band. Retained the highest quality lower bound; no cost/time comparison.'
      : 'No quality-qualified candidate has complete positive cost and time evidence. Keep the current model.';
    if (!pool.length && code === 'b' && qualityWinner) pool = [qualityWinner];
  }
  const index = new Map(pool.map((r, i) => [r.id, i]));
  ranked.sort((a, b) => (index.get(a.id) ?? 1e6) - (index.get(b.id) ?? 1e6) || qualitySort(a, b));
  return { pool, ranked, chosen: pool[0] ?? null, cohort: kept, reason };
}
