// Read-only check: how many days of validity are left on the benchmark snapshot that
// recommend_flow_model ships with. The advisor refuses a snapshot 14 days after its fetch
// time (empty shortlist, `expired: true`), and the tests pin the clock, so CI never warns.
// Reads the same file and the same expiry rule as the server (src/advisor/snapshot.ts).
//
// Usage: node scripts/check-freshness.mjs [--now <ISO 8601>]
//   --now   pretend it is this moment (tests and dry runs): YYYY-MM-DD, or a date-time with
//           Z or a UTC offset. Defaults to the real clock. Any other argument is an error.
// Always prints the days left. Exit 0: at least MIN_DAYS_LEFT days remain.
// Exit 1: fewer remain or the snapshot has expired. Exit 2: the snapshot or the arguments
// are unusable. To fix a failure: refresh the snapshot and redeploy (docs/DEPLOY.md, section 6).
const MIN_DAYS_LEFT = 3;
const DAY_MS = 86400000;
const USAGE = 'usage: check-freshness.mjs [--now <ISO 8601>]';
const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2}))?$/;

function fail(code, message) {
  console.error(message);
  if (process.env.GITHUB_ACTIONS === 'true') console.log(`::error title=Advisor snapshot::${message}`);
  process.exit(code);
}

function readNow(argv) {
  let raw = null;
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if ((arg !== '--now' && !arg.startsWith('--now=')) || raw !== null) {
      fail(2, `unsupported or repeated argument ${JSON.stringify(arg)}; ${USAGE}`);
    }
    raw = arg === '--now' ? (argv[++i] ?? '') : arg.slice('--now='.length);
  }
  if (raw === null) return new Date();
  const match = ISO_DATE.exec(raw);
  const parsed = match ? Date.parse(raw) : NaN;
  // Date.parse rolls 2026-02-30 over to March 2, so check the calendar day as well.
  const realDay = match && new Date(Date.UTC(+match[1], +match[2] - 1, +match[3])).getUTCDate() === +match[3];
  if (!Number.isFinite(parsed) || !realDay) fail(2, `--now needs an ISO 8601 date, got ${JSON.stringify(raw)}; ${USAGE}`);
  return new Date(parsed);
}

const now = readNow(process.argv.slice(2));

// Load the server's own snapshot module (same file, same expiry rule). It reads and parses the
// snapshot on import, so a missing or malformed file is reported here as exit 2, not a stack trace.
let advisor;
try {
  advisor = await import('../src/advisor/snapshot.ts');
} catch (error) {
  fail(2, `cannot load the advisor snapshot: ${error.message}`);
}
const { EXPIRES_AFTER_DAYS, SNAPSHOT, expiresAt } = advisor;

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
