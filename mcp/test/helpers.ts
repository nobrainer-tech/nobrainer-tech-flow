// Shared test helpers: o200k_base token counting, a local server and SDK clients for both eras.
import { randomBytes } from "node:crypto";
import { Tiktoken } from "js-tiktoken/lite";
import o200k from "js-tiktoken/ranks/o200k_base";
import { Client, StreamableHTTPClientTransport } from "@modelcontextprotocol/client";
import { Client as LegacyClient } from "@modelcontextprotocol/sdk/client/index.js";
import { StreamableHTTPClientTransport as LegacyTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";
import { startServer } from "../scripts/serve.ts";
import { createHttpHandler, type HttpOptions } from "../src/http.ts";
import { parseKeyRing } from "../src/token.ts";
import { memoryLimiter } from "../src/ratelimit.ts";
import type { LogLine } from "../src/log.ts";

const enc = new Tiktoken(o200k);
export const tokens = (text: string): number => enc.encode(text).length;

export const TEST_RING = parseKeyRing(`7:${randomBytes(32).toString("base64")}`);

export type Local = { url: URL; logs: LogLine[]; close: () => Promise<void> };

export async function startLocal(overrides: Partial<HttpOptions> = {}): Promise<Local> {
  const logs: LogLine[] = [];
  const handler = createHttpHandler({
    ring: TEST_RING,
    limiter: memoryLimiter(),
    allowedOrigins: ["https://claude.ai", "https://chatgpt.com"],
    allowedHosts: "loopback",
    log: (l) => logs.push(l),
    ...overrides,
  });
  const server = await startServer(handler, 0);
  const address = server.address();
  const port = typeof address === "object" && address ? address.port : 0;
  return {
    url: new URL(`http://127.0.0.1:${port}/mcp`),
    logs,
    close: () => new Promise((resolve) => server.close(() => resolve())),
  };
}

/** v2 SDK client: `legacy` = 2025-11-25 initialize, `modern` = pinned 2026-07-28. */
export async function connect(url: URL, era: "legacy" | "modern" = "modern"): Promise<Client> {
  const mode = era === "modern" ? { pin: "2026-07-28" } : "legacy";
  const client = new Client({ name: `test-${era}`, version: "1.0.0" }, { versionNegotiation: { mode } } as never);
  await client.connect(new StreamableHTTPClientTransport(url));
  return client;
}

/** v1 SDK client (@modelcontextprotocol/sdk 1.x), as most shipped clients still use. */
export async function connectV1(url: URL): Promise<LegacyClient> {
  const client = new LegacyClient({ name: "test-v1", version: "1.0.0" });
  await client.connect(new LegacyTransport(url));
  return client;
}

type TextResult = { content?: Array<{ type: string; text?: string }>; isError?: boolean };

/** Parse the single TextContent block of a tool result. */
export function body(result: unknown): Record<string, any> {
  const r = result as TextResult;
  assertOneText(r);
  return JSON.parse(r.content?.[0]?.text ?? "{}");
}

function assertOneText(r: TextResult): void {
  if (r.content?.length !== 1 || r.content[0]?.type !== "text") throw new Error("expected exactly one text block");
}

export const rawText = (result: unknown): string => (result as TextResult).content?.[0]?.text ?? "";
