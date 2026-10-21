// Per-contract rate limit (spec 14.3, layer 2). On Vercel, a Firewall rule checked through
// @vercel/firewall when FLOW_RATE_LIMIT_ID is set; otherwise, and whenever the firewall check
// fails, a best-effort in-memory window per function instance.
import { checkRateLimit } from "@vercel/firewall";

export const CONTRACT_LIMIT = 60;
export const WINDOW_MS = 10 * 60 * 1000;
const MAX_KEYS = 10_000;

export type RateLimiter = (key: string, request?: Request) => Promise<boolean>; // true = limited

export function memoryLimiter(limit = CONTRACT_LIMIT, windowMs = WINDOW_MS, clock = () => Date.now()): RateLimiter {
  const hits = new Map<string, number[]>();
  return async (key) => {
    const now = clock();
    const recent = (hits.get(key) ?? []).filter((t) => now - t < windowMs);
    if (recent.length >= limit) {
      hits.set(key, recent);
      return true;
    }
    recent.push(now);
    hits.delete(key);
    hits.set(key, recent);
    if (hits.size > MAX_KEYS) hits.delete(hits.keys().next().value as string);
    return false;
  };
}

export function createRateLimiter(env: NodeJS.ProcessEnv = process.env): RateLimiter {
  const memory = memoryLimiter();
  const ruleId = env.FLOW_RATE_LIMIT_ID;
  if (!ruleId || !env.VERCEL) return memory;
  return async (key, request) => {
    try {
      const { rateLimited, error } = await checkRateLimit(ruleId, { rateLimitKey: `contract:${key}`, request, timeout: 300 });
      if (error === "not-found") return memory(key);
      return rateLimited;
    } catch {
      return memory(key);
    }
  };
}
