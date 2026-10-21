// Secret screening (spec 7.5). Returns pattern ids and field paths, never values.
// Regexes use bounded quantifiers and left boundaries so scanning stays linear.

const MAX_DEPTH = 8;

const SIMPLE: ReadonlyArray<readonly [string, RegExp]> = [
  ['pem_private_key', /-----BEGIN (?:[A-Z0-9]{1,20} ){0,3}PRIVATE KEY(?: BLOCK)?-----/],
  ['aws_access_key_id', /(?<![A-Za-z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Za-z0-9])/],
  [
    'github_token',
    /(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{36,255})/,
  ],
  ['anthropic_key', /(?<![A-Za-z0-9_-])sk-ant-[A-Za-z0-9_-]{20,200}/],
  [
    'openai_key',
    /(?<![A-Za-z0-9_-])sk-(?:(?:proj|svcacct|admin)-[A-Za-z0-9_-]{40,200}|[A-Za-z0-9]{32,200})(?![A-Za-z0-9_-])/,
  ],
  ['slack_token', /(?<![A-Za-z0-9])xox[abposr]-[A-Za-z0-9-]{10,200}/],
];

const JWT =
  /(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{2,2000}\.[A-Za-z0-9_-]{2,2000}\.[A-Za-z0-9_-]{2,2000}/g;

const ASSIGNMENT =
  /(?:password|passwd|secret|token|api[_-]?key|secret[_-]?key|access[_-]?key)["']?[ \t]{0,3}[:=][ \t]{0,3}["']?([^\s"',;]{12,200})/gi;

const PLACEHOLDER = /^(?:<.*>|\$\{.*\}|\$[A-Za-z_]\w*$|\{\{|\*{3}|x{3}|changeme|example|your[_-]|placeholder|redacted)/i;
const PLACEHOLDER_ANYWHERE = /\*{3}|x{6}|changeme|example/i;
const IDENTIFIER_PATH = /^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$/;
const CONSTANT_NAME = /^[A-Z][A-Z0-9_]+$/;

function isPlaceholder(value: string): boolean {
  return (
    PLACEHOLDER.test(value) ||
    PLACEHOLDER_ANYWHERE.test(value) ||
    value.includes('(') ||
    value.includes(')') ||
    IDENTIFIER_PATH.test(value) ||
    CONSTANT_NAME.test(value)
  );
}

/** Returns the id of the first secret pattern found in `value`, or null. */
export function findSecret(value: string): string | null {
  for (const [id, re] of SIMPLE) {
    if (re.test(value)) return id;
  }
  for (const m of value.matchAll(JWT)) {
    if (m[0].length >= 40) return 'jwt';
  }
  for (const m of value.matchAll(ASSIGNMENT)) {
    const v = m[1];
    if (v !== undefined && !isPlaceholder(v)) return 'assignment';
  }
  return null;
}

type Hit = { field: string; pattern: string };

function childPath(path: string, key: string | number, known?: ReadonlySet<string>): string {
  if (typeof key === 'number') return `${path}[${key}]`;
  // Keys are user input until the schema has rejected unknown ones: only schema names are echoed.
  if (!/^[A-Za-z_]\w{0,63}$/.test(key) || (known && !known.has(key))) return `${path}["*"]`;
  return path === '' ? key : `${path}.${key}`;
}

function walk(v: unknown, path: string, depth: number, known?: ReadonlySet<string>): Hit | null {
  if (typeof v === 'string') {
    const pattern = findSecret(v);
    return pattern === null ? null : { field: path === '' ? '$' : path, pattern };
  }
  if (typeof v !== 'object' || v === null) return null;
  if (depth > MAX_DEPTH) return { field: path === '' ? '$' : path, pattern: 'too_deep' };
  if (Array.isArray(v)) {
    for (let i = 0; i < v.length; i++) {
      const hit = walk(v[i], childPath(path, i, known), depth + 1, known);
      if (hit) return hit;
    }
    return null;
  }
  for (const key of Object.keys(v)) {
    const hit = walk((v as Record<string, unknown>)[key], childPath(path, key, known), depth + 1, known);
    if (hit) return hit;
  }
  return null;
}

/**
 * Walks strings in objects and arrays (container depth limit 8). Returns the first hit with a
 * field path such as `evidence[0].out`, or `too_deep` for deeper nesting. A bare string input
 * reports the field `$`. With `known`, keys outside that set are reported as `["*"]`.
 */
export function scanInput(input: unknown, known?: ReadonlySet<string>): Hit | null {
  return walk(input, '', 0, known);
}
