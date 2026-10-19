// Builds src/generated/cards.json from content/cards.yaml and the pinned Flow
// release (spec section 8.2). The core (buildContent) is pure; the CLI below it
// only reads git, files and flags. cards.yaml maps card id -> {source, heading,
// rules, next?}; module entries default to skills/<module>/SKILL.md and its H1, add
// at most 5 rules to the description, and fail the build if the module is gone.
// Flags: --repo <checkout> --tag <tag> --check | --dry-run | --pin --cards <yaml>.
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { parse } from 'yaml';

export const STAGES = ['DRIFT_CHECK', 'BUDDY', 'SCOPE', 'AUTOPILOT', 'VERIFY', 'RECEIVE_AUDIT', 'LEARN'];
export const EVENTS = ['blocked', 'review_failed', 'decision_changed', 'worker_reported', 'repeated_failure', 'resume'];
export const BASE_CARD_IDS = ['overview', ...STAGES.map((s) => `stage:${s}`), ...EVENTS.map((e) => `event:${e}`), 'handoff', 'gates'];
const TOOLS = ['start_flow_task', 'get_flow_step', 'check_flow_evidence', 'check_flow_done', 'draft_flow_handoff'];
export const MAX_CARD_TOKENS = 350;
const MODULE_FILE = /^skills\/([^/]+)\/SKILL\.md$/;

export type SourcePin = { repo: string; tag: string; commit: string; files: Record<string, string> };
export type Release = { tag: string; commit: string; files: Record<string, string> };
export type BuildInput = {
  source: SourcePin; // with pin: true only repo is read; tag, commit and hashes come from the release
  cards: unknown; // parsed cards.yaml
  release: Release;
  countTokens: (text: string) => number;
  pin?: boolean;
};
export type BuiltCard = { description?: string; rules: string[]; source: string; next?: string; full?: string };
export type BuildResult = { json: string; source: SourcePin; warnings: string[]; tokens: Record<string, number> };
type CardDef = { source: string; heading: string | null; rules: string[]; next?: string }; // null: the H1

export class BuildError extends Error {}

export const collapse = (text: string): string => text.replace(/\s+/g, ' ').trim();
const sha256 = (text: string): string => createHash('sha256').update(text, 'utf8').digest('hex');
const isAscii = (text: string): boolean => /^[\x20-\x7e]*$/.test(text);

// GitHub heading anchor: rendered text, lowercased, punctuation dropped, spaces to hyphens.
export function slug(heading: string): string {
  const text = heading.replace(/\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/`/g, '');
  return text.toLowerCase().replace(/[^\p{L}\p{M}\p{N}\p{Pc} -]/gu, '').replace(/ /g, '-');
}

export function splitFrontmatter(markdown: string): { meta: Record<string, unknown>; body: string } {
  const match = /^---\n([\s\S]*?)\n---\n/.exec(markdown);
  if (!match) return { meta: {}, body: markdown };
  const meta: unknown = parse(match[1] ?? '');
  return { meta: meta && typeof meta === 'object' ? (meta as Record<string, unknown>) : {}, body: markdown.slice(match[0].length) };
}

type Heading = { level: number; text: string; anchor: string; line: number };

function headings(lines: string[]): Heading[] {
  const found: Heading[] = [];
  const seen = new Map<string, number>();
  let fenced = false;
  lines.forEach((line, index) => {
    if (/^\s*(```|~~~)/.test(line)) fenced = !fenced;
    const match = fenced ? null : /^(#{1,6})\s+(.*?)\s*#*\s*$/.exec(line);
    if (!match) return;
    const text = match[2] ?? '';
    const base = slug(text);
    const count = seen.get(base) ?? 0;
    seen.set(base, count + 1);
    found.push({ level: (match[1] ?? '').length, text, anchor: count ? `${base}-${count}` : base, line: index });
  });
  return found;
}

// Collapses whitespace inside each block (paragraph, list item, heading, fence or
// table line) and joins blocks with '\n', so a rule never spans two blocks.
function blockText(lines: string[]): string {
  const blocks: string[] = [];
  let current: string[] = [];
  const flush = (): void => {
    if (current.length) blocks.push(collapse(current.join(' ')));
    current = [];
  };
  for (const line of lines) {
    if (line.trim() === '' || /^\s*(#{1,6}\s|```|~~~|[-*+]\s|\d+\.\s|\|)/.test(line)) flush();
    if (line.trim() !== '') current.push(line);
    if (/^\s*(#{1,6}\s|```|~~~)/.test(line)) flush();
  }
  flush();
  return blocks.join('\n');
}

// A section runs from its heading to the next heading of the same or higher level.
export function findSection(markdown: string, heading: string | null): { anchor: string; text: string } {
  const lines = splitFrontmatter(markdown).body.split('\n');
  const all = headings(lines);
  const matches = all.filter((h) => (heading === null ? h.level === 1 : h.text === heading));
  if (matches.length !== 1) throw new BuildError(`heading ${heading ?? '(H1)'} found ${matches.length} times (need exactly 1)`);
  const own = matches[0] as Heading;
  const end = all.find((h) => h.line > own.line && h.level <= own.level)?.line ?? lines.length;
  return { anchor: own.anchor, text: blockText(lines.slice(own.line + 1, end)) };
}

const PUNCT_END = /[.;:!?][*_`"')]*$/;
const LIST_MARKER = /(^|\n)(-|\*|\+|\d+\.)$/;
const END_OK = /^($|\n|[.;:!?])/;

// The rule must occur verbatim and be cut at a sentence, clause or block boundary.
export function ruleProblem(section: string, rule: string): string | undefined {
  if (rule !== collapse(rule) || rule === '') return 'has leading, trailing or repeated whitespace';
  if (!isAscii(rule)) return 'contains non-ASCII characters';
  if (!section.includes(rule)) return 'does not occur verbatim in the section';
  for (let at = section.indexOf(rule); at >= 0; at = section.indexOf(rule, at + 1)) {
    const before = section.slice(0, at);
    const after = section.slice(at + rule.length);
    const trimmed = before.trimEnd();
    const startOk = before === '' || before.endsWith('\n') || LIST_MARKER.test(trimmed) || PUNCT_END.test(trimmed);
    if (startOk && (PUNCT_END.test(rule) || END_OK.test(after))) return undefined;
  }
  return 'is not cut at a sentence, semicolon or block boundary';
}

function readDefs(cards: unknown, errors: string[]): Map<string, CardDef> {
  const defs = new Map<string, CardDef>();
  if (!cards || typeof cards !== 'object' || Array.isArray(cards)) {
    errors.push('cards.yaml: top level must be a mapping of card id -> definition');
    return defs;
  }
  for (const [id, raw] of Object.entries(cards)) {
    const def = raw as Partial<CardDef> | null;
    const module = id.startsWith('module:') ? id.slice(7) : undefined;
    const extra = def && typeof def === 'object' ? Object.keys(def).filter((k) => !['source', 'heading', 'rules', 'next'].includes(k)) : [];
    const source = def?.source ?? (module ? `skills/${module}/SKILL.md` : undefined);
    const rules = def?.rules;
    const heading = def?.heading ?? (module ? null : undefined);
    if (!def) errors.push(`${id}: definition must be a mapping`);
    else if (!module && !BASE_CARD_IDS.includes(id)) errors.push(`${id}: unknown card id`);
    else if (extra.length) errors.push(`${id}: unknown keys ${extra.join(', ')}`);
    else if (typeof source !== 'string' || (heading !== null && typeof heading !== 'string')) errors.push(`${id}: needs string source and heading`);
    else if (!Array.isArray(rules) || rules.length < 1 || rules.length > (module ? 5 : 6) || !rules.every((r) => typeof r === 'string'))
      errors.push(`${id}: rules must be 1-${module ? 5 : 6} strings`);
    else if (def.next !== undefined && ![...STAGES, ...TOOLS].includes(def.next)) errors.push(`${id}: unknown next "${def.next}"`);
    else defs.set(id, { source, heading, rules, ...(def.next ? { next: def.next } : {}) });
  }
  return defs;
}

export function buildContent(input: BuildInput): BuildResult {
  const { release, countTokens } = input;
  const errors: string[] = [];
  const warnings: string[] = [];
  const defs = readDefs(input.cards, errors);
  const pin = input.pin
    ? { repo: input.source.repo, tag: release.tag, commit: release.commit, files: {} as Record<string, string> }
    : input.source;
  if (pin.tag !== release.tag) errors.push(`SOURCE.json tag ${pin.tag} differs from requested tag ${release.tag}`);
  if (pin.commit !== release.commit) errors.push(`SOURCE.json commit ${pin.commit} differs from ${release.tag} -> ${release.commit}`);

  const quoted = new Set<string>();
  const readFile = (id: string, path: string): string | undefined => {
    const text = release.files[path];
    if (text === undefined) errors.push(`${id}: ${path} not found at ${release.tag}`);
    else quoted.add(path);
    return text;
  };
  const modules = Object.keys(release.files).flatMap((p) => MODULE_FILE.exec(p)?.[1] ?? []).sort();
  for (const id of BASE_CARD_IDS) if (!defs.has(id) && !errors.some((e) => e.startsWith(`${id}:`))) errors.push(`${id}: card missing from cards.yaml`);
  for (const id of defs.keys())
    if (id.startsWith('module:') && !modules.includes(id.slice(7)))
      errors.push(`${id}: module "${id.slice(7)}" is not in the release ${release.tag} (renamed or removed? released: ${modules.join(', ')})`);

  const full = `Full module: install the Flow skills from ${pin.repo}`;
  const built = new Map<string, BuiltCard>();
  const fromDef = (id: string, def: CardDef): Omit<BuiltCard, 'description' | 'full'> | undefined => {
    const text = readFile(id, def.source);
    if (text === undefined) return undefined;
    try {
      const section = findSection(text, def.heading);
      for (const rule of def.rules) {
        const problem = ruleProblem(section.text, rule);
        if (problem) errors.push(`${id}: rule ${problem} (${def.source}#${section.anchor}): "${rule}"`);
      }
      return { rules: def.rules, source: `${def.source}#${section.anchor}`, ...(def.next ? { next: def.next } : {}) };
    } catch (error) {
      errors.push(`${id}: ${def.source}: ${(error as Error).message}`);
      return undefined;
    }
  };
  for (const id of BASE_CARD_IDS) {
    const def = defs.get(id);
    const card = def && fromDef(id, def);
    if (card) built.set(id, card);
  }
  for (const name of modules) {
    const id = `module:${name}`;
    const path = `skills/${name}/SKILL.md`;
    const description = collapse(String(splitFrontmatter(readFile(id, path) ?? '').meta.description ?? ''));
    if (!description) errors.push(`${id}: ${path} has no frontmatter description`);
    else if (!isAscii(description)) errors.push(`${id}: description contains non-ASCII characters`);
    const def = defs.get(id);
    if (!def) warnings.push(`WARNING: ${id} has no cards.yaml entry; emitting a description-only card`);
    const card = def ? fromDef(id, def) : { rules: [], source: path };
    if (card) built.set(id, { description, ...card, full });
  }

  const tokens: Record<string, number> = {};
  for (const [id, card] of built) {
    const compact = JSON.stringify({ id, ...card });
    tokens[id] = countTokens(compact);
    if (tokens[id] > MAX_CARD_TOKENS) errors.push(`${id}: ${tokens[id]} tokens exceeds the ${MAX_CARD_TOKENS}-token card budget`);
    if (!isAscii(compact)) errors.push(`${id}: card contains non-ASCII characters`);
  }

  for (const path of [...quoted].sort()) {
    const actual = sha256(release.files[path] ?? '');
    if (input.pin) pin.files[path] = actual;
    else if (pin.files[path] === undefined) errors.push(`SOURCE.json: missing sha256 for quoted file ${path}`);
    else if (pin.files[path] !== actual) errors.push(`SOURCE.json: sha256 mismatch for ${path} (pinned ${pin.files[path]}, tag has ${actual})`);
  }
  for (const path of Object.keys(pin.files)) if (!quoted.has(path)) errors.push(`SOURCE.json: ${path} is pinned but no card quotes it`);

  let flowVersion = '';
  try {
    flowVersion = String((JSON.parse(release.files['package.json'] ?? '') as { version?: unknown }).version ?? '');
  } catch {
    // reported below
  }
  if (!/^\d+\.\d+\.\d+/.test(flowVersion)) errors.push(`package.json at ${release.tag} has no valid version`);
  if (errors.length) throw new BuildError([`content build failed (${errors.length}):`, ...errors.map((e) => `- ${e}`), ...warnings].join('\n'));

  const cards = Object.fromEntries([...built].map(([id, c]) => [id, c]));
  const out = { flow_version: flowVersion, tag: release.tag, commit: release.commit, repo: pin.repo, modules, cards };
  return { json: `${JSON.stringify(out, null, 2)}\n`, source: pin, warnings, tokens };
}

// ---- CLI ----

const MCP_ROOT = fileURLToPath(new URL('..', import.meta.url));
const SOURCE_PATH = `${MCP_ROOT}content/SOURCE.json`;
const OUTPUT_PATH = `${MCP_ROOT}src/generated/cards.json`;

function flag(args: string[], name: string): string | undefined {
  const index = args.indexOf(name);
  if (index < 0) return undefined;
  const value = args[index + 1];
  if (value === undefined || value.startsWith('--')) throw new BuildError(`${name} needs a value`);
  return value;
}

export function loadRelease(repo: string, tag: string, cards: unknown): Release {
  const git = (...args: string[]): Buffer => execFileSync('git', ['-C', repo, ...args], { maxBuffer: 64 << 20, stdio: ['ignore', 'pipe', 'pipe'] });
  let commit: string;
  try {
    commit = git('rev-parse', '--verify', '--quiet', `refs/tags/${tag}^{commit}`).toString().trim();
  } catch {
    throw new BuildError(`tag ${tag} not found in ${repo} (fetch tags first: git fetch --tags)`);
  }
  const tree = git('ls-tree', '-r', '--name-only', commit).toString().split('\n');
  const sources = cards && typeof cards === 'object' ? Object.values(cards).map((d) => (d as { source?: unknown } | null)?.source) : [];
  const wanted = new Set(['package.json', ...tree.filter((p) => MODULE_FILE.test(p)), ...sources.filter((s): s is string => typeof s === 'string')]);
  const files: Record<string, string> = {};
  for (const path of wanted) if (tree.includes(path)) files[path] = git('show', `${commit}:${path}`).toString('utf8');
  return { tag, commit, files };
}

async function main(args: string[]): Promise<void> {
  const { Tiktoken } = await import('js-tiktoken/lite');
  const { default: o200k } = await import('js-tiktoken/ranks/o200k_base');
  const encoder = new Tiktoken(o200k);
  const source = JSON.parse(readFileSync(SOURCE_PATH, 'utf8')) as SourcePin;
  const cards: unknown = parse(readFileSync(flag(args, '--cards') ?? `${MCP_ROOT}content/cards.yaml`, 'utf8'));
  const repo = flag(args, '--repo') ?? fileURLToPath(new URL('../..', import.meta.url));
  const pin = args.includes('--pin');
  const release = loadRelease(repo, flag(args, '--tag') ?? source.tag, cards);
  const result = buildContent({ source, cards, release, countTokens: (t) => encoder.encode(t).length, pin });
  for (const warning of result.warnings) console.error(warning);
  const sizes = Object.values(result.tokens);
  const avg = Math.round(sizes.reduce((a, b) => a + b, 0) / sizes.length);
  const summary = `${sizes.length} cards, ${result.source.tag}, tokens max ${Math.max(...sizes)} avg ${avg}`;
  if (args.includes('--check')) {
    let current = '';
    try {
      current = readFileSync(OUTPUT_PATH, 'utf8');
    } catch {
      // treated as a difference
    }
    if (current !== result.json) throw new BuildError(`${OUTPUT_PATH} is stale: run node scripts/build-content.ts`);
    console.log(`check ok: ${summary}`);
  } else if (args.includes('--dry-run')) {
    console.log(`dry run ok: ${summary}`);
  } else {
    if (pin) writeFileSync(SOURCE_PATH, `${JSON.stringify(result.source, null, 2)}\n`);
    writeFileSync(OUTPUT_PATH, result.json);
    console.log(`wrote ${OUTPUT_PATH}${pin ? ' and content/SOURCE.json' : ''}: ${summary}`);
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main(process.argv.slice(2)).catch((error: unknown) => {
    console.error(error instanceof BuildError ? error.message : error);
    process.exitCode = 1;
  });
}
