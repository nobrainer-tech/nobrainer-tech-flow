// Environment configuration for the deployed function and the local server.
import { randomBytes } from "node:crypto";
import { parseKeyRing, type KeyRing } from "./token.ts";
import { createRateLimiter } from "./ratelimit.ts";
import type { HttpOptions } from "./http.ts";

export const DEFAULT_ORIGINS = ["https://chatgpt.com", "https://claude.ai", "https://platform.openai.com"];
export const PRODUCTION_HOST = "mcp.nobrainer.tech";

const list = (v: string | undefined): string[] => (v ?? "").split(",").map((s) => s.trim()).filter(Boolean);

/** Keys come from FLOW_TOKEN_KEYS. Outside Vercel a missing value gets an ephemeral dev key. */
export function loadKeyRing(env: NodeJS.ProcessEnv): KeyRing {
  if (env.FLOW_TOKEN_KEYS) return parseKeyRing(env.FLOW_TOKEN_KEYS);
  if (env.VERCEL) throw new Error("FLOW_TOKEN_KEYS is required on Vercel");
  return parseKeyRing(`0:${randomBytes(32).toString("base64")}`);
}

export function optionsFromEnv(env: NodeJS.ProcessEnv = process.env): HttpOptions {
  const onVercel = Boolean(env.VERCEL);
  const hosts = onVercel
    ? [PRODUCTION_HOST, env.VERCEL_URL, env.VERCEL_BRANCH_URL, env.VERCEL_PROJECT_PRODUCTION_URL, ...list(env.ALLOWED_HOSTS)]
    : "loopback";
  const origins = env.ALLOWED_ORIGINS ? list(env.ALLOWED_ORIGINS) : [...DEFAULT_ORIGINS];
  if (!onVercel || env.VERCEL_ENV === "preview") origins.push("http://localhost:6274");
  return {
    ring: loadKeyRing(env),
    limiter: createRateLimiter(env),
    allowedOrigins: origins,
    allowedHosts: hosts === "loopback" ? hosts : hosts.filter((h): h is string => Boolean(h)).map((h) => h.toLowerCase()),
  };
}
