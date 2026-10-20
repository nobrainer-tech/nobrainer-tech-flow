import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

// Same depth from src/advisor/ and dist/advisor/, so this resolves in both layouts.
const SNAPSHOT_URL = new URL('../../data/benchmark/snapshot.json', import.meta.url);

// Mirrors task-router-core.js rank(): a snapshot expires 14 days after fetchedAt.
export const EXPIRES_AFTER_DAYS = 14;

export type SnapshotModel = {
  id: string;
  family: string;
  routes: Record<string, string>;
  fallback: boolean;
  main: boolean;
  worker: boolean;
  successors: string[];
};

export type Row = {
  id: string;
  model: string;
  task: string;
  effort: string;
  score: number;
  lower: number;
  upper: number;
  source: string;
  cost: number | null;
  costKind: string;
  time: number | null;
  timeKind: string;
  harness: string | null;
  successCost: number | null;
};

type RawRow = [string, string, string, string, number, number, number, string, number | null, string, number | null, string, string | null, number | null];

export type Snapshot = {
  source: string;
  as_of: string;
  fetched_at: string;
  policy: {
    quality_band_fraction: number;
    source_priority: string[];
    route_order: string[];
    apps: string[];
    native_routes: Record<string, string[]>;
    default_providers: string[];
  };
  jobs: Record<string, string>;
  tasks: Record<string, { label: string; scale: string; span: Record<string, number>; withheld?: boolean }>;
  retired: string[];
  models: SnapshotModel[];
  rows: RawRow[];
};

export type LoadedSnapshot = Snapshot & { sha: string; table: Row[]; byId: Map<string, SnapshotModel> };

function load(): LoadedSnapshot {
  const bytes = readFileSync(SNAPSHOT_URL);
  const data = JSON.parse(bytes.toString('utf8')) as Snapshot;
  const table = data.rows.map(([id, model, task, effort, score, lower, upper, source, cost, costKind, time, timeKind, harness, successCost]) =>
    ({ id, model, task, effort, score, lower, upper, source, cost, costKind, time, timeKind, harness, successCost }));
  return { ...data, sha: createHash('sha256').update(bytes).digest('hex'), table, byId: new Map(data.models.map(m => [m.id, m])) };
}

export const SNAPSHOT: LoadedSnapshot = load();

/** Expiry date (YYYY-MM-DD) of the pinned snapshot, or null when fetched_at is unreadable. */
export function expiresAt(): Date | null {
  const fetched = Date.parse(SNAPSHOT.fetched_at);
  return Number.isFinite(fetched) ? new Date(fetched + EXPIRES_AFTER_DAYS * 86400000) : null;
}

export function snapshotInfo(): { date: string; sha: string; source: string; expires: string | null } {
  return { date: SNAPSHOT.as_of, sha: SNAPSHOT.sha.slice(0, 8), source: SNAPSHOT.source, expires: expiresAt()?.toISOString().slice(0, 10) ?? null };
}
