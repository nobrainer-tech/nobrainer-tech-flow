import { test } from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { createSpendHook } from "../../src/spend.ts";

const SECRET = "test-webhook-secret-value";
const env = { SPEND_WEBHOOK_SECRET: SECRET, FLOW_PAUSE_TOKEN: "pause-token-for-tests", FLOW_PROJECT_ID: "prj_test", FLOW_TEAM_ID: "team_test" };
const signed = (payload: object, secret = SECRET) => {
  const raw = JSON.stringify(payload);
  return new Request("https://mcp.example/api/spend-hook", {
    method: "POST",
    headers: { "x-vercel-signature": createHmac("sha1", secret).update(raw).digest("hex") },
    body: raw,
  });
};

function recorder() {
  const calls: Array<{ url: string; init: RequestInit }> = [];
  const f = (async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    return new Response("{}", { status: 200 });
  }) as unknown as typeof fetch;
  return { calls, f };
}

test("pauses only this project at the threshold, with the team id", async () => {
  const { calls, f } = recorder();
  const res = await createSpendHook(env, f)(signed({ budgetAmount: 50, currentSpend: 38, teamId: "team_test", thresholdPercent: 75 }));
  assert.equal(res.status, 200);
  assert.equal(calls.length, 1);
  assert.equal(calls[0]!.url, "https://api.vercel.com/v1/projects/prj_test/pause?teamId=team_test");
  assert.equal(calls[0]!.init.method, "POST");
});

test("below the threshold, another team, or a bad signature: no pause", async () => {
  const { calls, f } = recorder();
  const hook = createSpendHook(env, f);
  assert.equal((await hook(signed({ teamId: "team_test", thresholdPercent: 50 }))).status, 200);
  assert.equal((await hook(signed({ teamId: "team_other", thresholdPercent: 100 }))).status, 200);
  assert.equal((await hook(signed({ teamId: "team_test", thresholdPercent: 100 }, "wrong-secret"))).status, 403);
  const unsigned = new Request("https://mcp.example/api/spend-hook", { method: "POST", body: "{}" });
  assert.equal((await hook(unsigned)).status, 403);
  assert.equal(calls.length, 0);
});

test("missing configuration fails closed", async () => {
  const { calls, f } = recorder();
  assert.equal((await createSpendHook({}, f)(signed({ thresholdPercent: 100 }))).status, 503);
  assert.equal((await createSpendHook({ SPEND_WEBHOOK_SECRET: SECRET }, f)(signed({ thresholdPercent: 100 }))).status, 503);
  assert.equal(calls.length, 0);
});

test("a malformed SPEND_PAUSE_PERCENT falls back to 75 instead of pausing on every alert", async () => {
  const { calls, f } = recorder();
  const hook = createSpendHook({ ...env, SPEND_PAUSE_PERCENT: "75%" }, f);
  await hook(signed({ teamId: "team_test", thresholdPercent: 50 }));
  assert.equal(calls.length, 0);
  await hook(signed({ teamId: "team_test", thresholdPercent: 75 }));
  assert.equal(calls.length, 1);
});
