// Read-only check: how many days of validity are left on the benchmark snapshot that
// recommend_flow_model ships with. The advisor refuses a snapshot 14 days after its fetch
// time (empty shortlist, `expired: true`), and the tests pin the clock, so CI never warns.
// Reads the same file and the same expiry rule as the server (src/advisor/snapshot.ts).
//
// Usage: node scripts/check-freshness.mjs [--now <ISO 8601>]
//   --now   pretend it is this moment (tests and dry runs); defaults to the real clock.
// Always prints the days left. Exit 0: at least MIN_DAYS_LEFT days remain.
// Exit 1: fewer remain or the snapshot has expired. Exit 2: the snapshot or --now is unusable.
// To fix a failure: refresh the snapshot and redeploy (docs/DEPLOY.md, section 6).
import { EXPIRES_AFTER_DAYS, SNAPSHOT, expiresAt } from '../src/advisor/snapshot.ts';

const MIN_DAYS_LEFT = 3;
const DAY_MS = 86400000;

function fail(code, message) {
  console.error(message);
  if (process.env.GITHUB_ACTIONS === 'true') console.log(`::error title=Advisor snapshot::${message}`);
  process.exit(code);
}

function readNow(argv) {
  const flag = argv.findIndex(a => a === '--now' || a.startsWith('--now='));
  if (flag === -1) return new Date();
  const raw = argv[flag].startsWith('--now=') ? argv[flag].slice('--now='.length) : argv[flag + 1];
  const parsed = Date.parse(raw ?? '');
  if (!Number.isFinite(parsed)) fail(2, `--now needs an ISO 8601 date, got ${JSON.stringify(raw ?? null)}`);
  return new Date(parsed);
}

const now = readNow(process.argv.slice(2));
const expiry = expiresAt();
if (!expiry) fail(2, `snapshot fetched_at is unreadable: ${JSON.stringify(SNAPSHOT.fetched_at)}`);

const daysLeft = (expiry.getTime() - now.getTime()) / DAY_MS;
// Floor to one decimal so the printed number is never above the threshold when the check fails.
const shown = Math.floor(Math.abs(daysLeft) * 10) / 10;
const state = daysLeft < 0 ? `EXPIRED ${shown.toFixed(1)} days ago` : `${shown.toFixed(1)} days left`;
console.log(
  `advisor snapshot: fetched ${SNAPSHOT.fetched_at}, expires ${expiry.toISOString()} ` +
  `(${EXPIRES_AFTER_DAYS} days after fetch), checked ${now.toISOString()}: ${state} (minimum ${MIN_DAYS_LEFT})`,
);

if (daysLeft < MIN_DAYS_LEFT) {
  fail(1, `advisor snapshot: ${state}; refresh it and redeploy (mcp/docs/DEPLOY.md, section 6).`);
}
