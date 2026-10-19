// Context budget for tools/list, instructions and the prompt (spec 10.1, 10.3), measured live.
import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import type { Client } from "@modelcontextprotocol/client";
import { connect, startLocal, tokens, type Local } from "../helpers.ts";
import { INSTRUCTIONS } from "../../src/server.ts";

let local: Local;
let client: Client;
before(async () => {
  local = await startLocal();
  client = await connect(local.url);
});
after(async () => {
  await client.close();
  await local.close();
});

export const DEFINITION_CAP = 1500;

test("six tool definitions fit 1,500 o200k_base tokens; each description <= 300 characters", async () => {
  const { tools } = await client.listTools();
  assert.equal(tools.length, 6);
  const sizes: Record<string, number> = {};
  for (const t of tools) {
    const def = { name: t.name, title: t.title, description: t.description, inputSchema: t.inputSchema, annotations: t.annotations };
    sizes[t.name] = tokens(JSON.stringify(def));
    assert.ok((t.description ?? "").length <= 300, `${t.name} description ${t.description?.length}`);
  }
  const total = Object.values(sizes).reduce((a, b) => a + b, 0);
  console.log(`DEFINITION_TOKENS ${JSON.stringify({ total, ...sizes })}`);
  assert.ok(total <= DEFINITION_CAP, `total ${total}`);
  assert.ok((sizes.recommend_flow_model ?? 0) <= 300, "advisor definition <= 300 tokens");
});

test("server instructions <= 120 tokens and self-contained in 512 characters", async () => {
  assert.equal(client.getInstructions(), INSTRUCTIONS);
  assert.ok(INSTRUCTIONS.length <= 512, String(INSTRUCTIONS.length));
  const n = tokens(INSTRUCTIONS);
  console.log(`INSTRUCTION_TOKENS ${n} chars=${INSTRUCTIONS.length}`);
  assert.ok(n <= 120);
});

test("prompt definition <= 100 tokens", async () => {
  const { prompts } = await client.listPrompts();
  assert.equal(prompts.length, 1);
  const n = tokens(JSON.stringify(prompts[0]));
  console.log(`PROMPT_TOKENS ${n}`);
  assert.ok(n <= 100);
});
