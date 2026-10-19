// Spend Management webhook -> pause only this project (spec 14.4). This is the only code path
// that makes an outbound request, and it is not reachable from any MCP tool.
// Vercel signs the raw body with HMAC-SHA1 (hex) in `x-vercel-signature`
// (https://vercel.com/docs/webhooks/webhooks-api#securing-webhooks).
import { createHmac, timingSafeEqual } from "node:crypto";

export type SpendEnv = {
  SPEND_WEBHOOK_SECRET?: string | undefined;
  FLOW_PAUSE_TOKEN?: string | undefined;
  FLOW_PROJECT_ID?: string | undefined;
  FLOW_TEAM_ID?: string | undefined;
  SPEND_PAUSE_PERCENT?: string | undefined;
};

const json = (status: number, body: Record<string, unknown>): Response =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

export function validSignature(raw: string, header: string | null, secret: string): boolean {
  if (!header || !/^[0-9a-f]{40}$/i.test(header)) return false;
  const want = createHmac("sha1", secret).update(raw).digest();
  return timingSafeEqual(want, Buffer.from(header, "hex"));
}

export function createSpendHook(env: SpendEnv, doFetch: typeof fetch = fetch) {
  return async function spendHook(req: Request): Promise<Response> {
    if (req.method !== "POST") return json(405, { error: "method" });
    const secret = env.SPEND_WEBHOOK_SECRET;
    if (!secret) return json(503, { error: "not configured" });
    const raw = await req.text();
    if (raw.length > 4096 || !validSignature(raw, req.headers.get("x-vercel-signature"), secret)) {
      return json(403, { error: "invalid signature" });
    }
    let event: { thresholdPercent?: unknown; teamId?: unknown };
    try {
      event = JSON.parse(raw);
    } catch {
      return json(400, { error: "invalid json" });
    }
    const threshold = Number(event.thresholdPercent);
    const pauseAt = Number(env.SPEND_PAUSE_PERCENT ?? "75");
    console.log(JSON.stringify({ ts: new Date().toISOString(), route: "/api/spend-hook", threshold }));
    if (!Number.isFinite(threshold) || threshold < pauseAt) return json(200, { action: "none", threshold });
    if (env.FLOW_TEAM_ID && event.teamId !== env.FLOW_TEAM_ID) return json(200, { action: "none", reason: "other team" });
    if (!env.FLOW_PAUSE_TOKEN || !env.FLOW_PROJECT_ID) return json(503, { error: "pause not configured" });
    const team = env.FLOW_TEAM_ID ? `?teamId=${encodeURIComponent(env.FLOW_TEAM_ID)}` : "";
    const res = await doFetch(`https://api.vercel.com/v1/projects/${encodeURIComponent(env.FLOW_PROJECT_ID)}/pause${team}`, {
      method: "POST",
      headers: { authorization: `Bearer ${env.FLOW_PAUSE_TOKEN}`, "content-type": "application/json" },
    });
    console.log(JSON.stringify({ ts: new Date().toISOString(), route: "/api/spend-hook", action: "pause", status: res.status }));
    return json(res.ok ? 200 : 502, { action: "pause", status: res.status });
  };
}
