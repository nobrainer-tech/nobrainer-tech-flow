import * as z from 'zod';
import { SNAPSHOT } from './snapshot.ts';

// The site's task ids that this snapshot can answer: tasks with rows, or whose scores are
// withheld for licensing (the note then points to the site).
export const TASKS = Object.keys(SNAPSHOT.tasks)
  .filter(t => SNAPSHOT.tasks[t]?.withheld || SNAPSHOT.table.some(r => r.task === t)) as [string, ...string[]];
// The site's public priorities (PRIORITIES in task-router-core.js): g, b, e.
export const PRIORITY_CODES = { quality: 'g', balanced: 'b', efficient: 'e' } as const;

export const recommendInput = z.object({
  task: z.enum(TASKS),
  have: z.array(z.string().min(1).max(64)).max(30).optional().describe('Providers, models or client apps you can use'),
  priority: z.enum(['quality', 'balanced', 'efficient']).optional(),
  role: z.enum(['main', 'worker']).optional()
}).strict();

export type RecommendInput = z.infer<typeof recommendInput>;

export const RECOMMEND_TOOL = {
  name: 'recommend_flow_model',
  title: 'Recommend Flow model',
  description: 'Use when picking a model for a Flow task: top-3 from a pinned NoBrainer benchmark snapshot, no invented scores.'
} as const;

export const RECOMMEND_ANNOTATIONS = { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false } as const;

export class AdvisorInputError extends Error {
  readonly code = 'INVALID_INPUT';
  readonly why: string;
  readonly fix: string;
  constructor(why: string, fix: string) {
    super(why);
    this.name = 'AdvisorInputError';
    this.why = why;
    this.fix = fix;
  }
}

const PROBLEMS: Record<string, string> = { invalid_value: 'unsupported value', invalid_type: 'wrong type', too_big: 'too long or too many items',
  too_small: 'empty value', unrecognized_keys: 'unknown field' };

export function parseInput(input: unknown): RecommendInput {
  // Direct callers may send "Coding" or a site job alias ("agentic"); the published schema stays exact.
  let raw = input;
  if (input && typeof input === 'object' && typeof (input as { task?: unknown }).task === 'string') {
    const task = (input as { task: string }).task.trim().toLowerCase();
    raw = { ...input, task: SNAPSHOT.jobs[task] && !TASKS.includes(task) ? SNAPSHOT.jobs[task] : task };
  }
  const parsed = recommendInput.safeParse(raw);
  if (parsed.success) return parsed.data;
  const issue = parsed.error.issues[0];
  const field = issue?.path.join('.') || 'input';
  const fix = field === 'task' ? 'Use one of: ' + TASKS.join(', ') + '.'
    : field.startsWith('have') ? 'Send up to 30 provider or model ids, each 1-64 characters.'
    : 'Send only task, have, priority and role.';
  throw new AdvisorInputError('Invalid ' + field + ': ' + (PROBLEMS[issue?.code ?? ''] ?? 'bad value') + '.', fix);
}
