// Web-standard HTTP entry: method, size, Host and Origin guards, then the SDK handler (spec 3, 12).
import {
  CLIENT_INFO_META_KEY, PROTOCOL_VERSION_META_KEY, WebStandardStreamableHTTPServerTransport, createMcpHandler, isLegacyRequest,
} from "@modelcontextprotocol/server";
import { buildServer, type CallRecord } from "./server.ts";
import type { KeyRing } from "./token.ts";
import type { RateLimiter } from "./ratelimit.ts";
import { logLine, type LogLine } from "./log.ts";

export const MAX_BODY_BYTES = 32 * 1024;
const MAX_DEPTH = 8; // spec 12.2; the deepest valid message nests about 6 levels

export type HttpOptions = {
  ring: KeyRing;
  limiter: RateLimiter;
  allowedOrigins: readonly string[];
  allowedHosts: readonly string[] | "loopback"; // "loopback": local server, Host and Origin may be 127.0.0.1/localhost
  now?: () => number;
  log?: (line: LogLine) => void;
};

const SECURITY_HEADERS = { "cache-control": "no-store", "x-content-type-options": "nosniff" };

function plain(status: number, text: string, extra: Record<string, string> = {}): Response {
  return new Response(text, { status, headers: { "content-type": "text/plain; charset=utf-8", ...SECURITY_HEADERS, ...extra } });
}

function rpcError(status: number, code: number, message: string): Response {
  return new Response(JSON.stringify({ jsonrpc: "2.0", id: null, error: { code, message } }), {
    status,
    headers: { "content-type": "application/json", ...SECURITY_HEADERS },
  });
}

/** Container nesting depth, iterative and stopping at the limit (no recursion on hostile input). */
export function tooDeep(v: unknown, limit = MAX_DEPTH): boolean {
  const stack: Array<[unknown, number]> = [[v, 1]];
  while (stack.length) {
    const [node, d] = stack.pop() as [unknown, number];
    if (!node || typeof node !== "object") continue;
    if (d > limit) return true;
    for (const child of Object.values(node as object)) stack.push([child, d + 1]);
  }
  return false;
}

async function readCapped(req: Request): Promise<string | null> {
  const declared = Number(req.headers.get("content-length") ?? "0");
  if (declared > MAX_BODY_BYTES) return null;
  if (!req.body) return "";
  const reader = req.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > MAX_BODY_BYTES) {
      await reader.cancel();
      return null;
    }
    chunks.push(value);
  }
  return Buffer.concat(chunks).toString("utf8");
}

const LOOPBACK = /^(127\.0\.0\.1|localhost|\[::1\])(:\d{1,5})?$/;
const isLoopback = (host: string): boolean => LOOPBACK.test(host);
function isLoopbackOrigin(origin: string): boolean {
  const m = /^https?:\/\/([^/]+)$/i.exec(origin);
  return Boolean(m?.[1] && isLoopback(m[1].toLowerCase()));
}

const short = (v: unknown, n = 40): string | undefined => (typeof v === "string" ? v.replace(/[^\x20-\x7e]/g, "").slice(0, n) : undefined);

function describe(body: unknown, req: Request): Pick<LogLine, "rpc_method" | "tool" | "protocol_version" | "client_name"> {
  const msg = (Array.isArray(body) ? body[0] : body) as Record<string, any> | undefined;
  const params = (msg?.params ?? {}) as Record<string, any>;
  const meta = (params._meta ?? {}) as Record<string, any>;
  return {
    rpc_method: short(msg?.method),
    tool: msg?.method === "tools/call" ? short(params.name, 64) : undefined,
    protocol_version: short(req.headers.get("mcp-protocol-version") ?? meta[PROTOCOL_VERSION_META_KEY] ?? params.protocolVersion, 20),
    client_name: short(params.clientInfo?.name ?? meta[CLIENT_INFO_META_KEY]?.name),
  };
}

export function createHttpHandler(opts: HttpOptions): (req: Request) => Promise<Response> {
  const now = opts.now ?? (() => Math.floor(Date.now() / 1000));
  const log = opts.log ?? logLine;
  const records = new WeakMap<Request, CallRecord>();
  const ctxFor = (request: Request) => ({ ring: opts.ring, limiter: opts.limiter, now, request });
  // 2026-07-28 traffic: the SDK's modern leg, JSON responses only.
  const modern = createMcpHandler(
    (rc) => buildServer(ctxFor(rc.requestInfo as Request), rc.requestInfo ? records.get(rc.requestInfo) : undefined),
    { legacy: "reject", responseMode: "json", maxSubscriptions: 0, maxRequestBodySize: MAX_BODY_BYTES, onerror: () => {} },
  );
  // 2025-era traffic: a fresh stateless server per request with JSON responses (no SSE),
  // the established stateless idiom (sessionIdGenerator undefined).
  async function legacy(request: Request, parsedBody: unknown, record: CallRecord): Promise<Response> {
    const server = buildServer(ctxFor(request), record);
    const transport = new WebStandardStreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
    await server.connect(transport);
    try {
      return await transport.handleRequest(request, { parsedBody });
    } finally {
      await server.close();
    }
  }

  return async function handle(req: Request): Promise<Response> {
    const started = performance.now();
    const url = new URL(req.url);
    const line: LogLine = { route: url.pathname.slice(0, 40), status: 0 };
    const finish = async (res: Response): Promise<Response> => {
      line.status = res.status;
      if ((res.headers.get("content-type") ?? "").includes("text/event-stream")) {
        // Never buffer a stream (it may not end); this server is not expected to produce one.
        line.duration_ms = Math.round(performance.now() - started);
        line.result_code ??= "STREAM";
        log(line);
        return res;
      }
      const buf = await res.arrayBuffer();
      line.response_bytes = buf.byteLength;
      line.duration_ms = Math.round(performance.now() - started);
      log(line);
      const headers = new Headers(res.headers);
      for (const [k, v] of Object.entries(SECURITY_HEADERS)) headers.set(k, v);
      return new Response(req.method === "HEAD" ? null : buf, { status: res.status, headers });
    };
    const host = (req.headers.get("host") ?? url.host).toLowerCase();
    const local = opts.allowedHosts === "loopback";
    if (local ? !isLoopback(host) : !opts.allowedHosts.includes(host)) return finish(plain(403, "Forbidden host"));
    const origin = req.headers.get("origin");
    if (origin !== null && !opts.allowedOrigins.includes(origin) && !(local && isLoopbackOrigin(origin))) {
      line.rejected_origin = short(origin.replace(/^[a-z]+:\/\//i, "").split("/")[0], 80);
      return finish(plain(403, "Forbidden origin"));
    }
    if (req.method !== "POST") return finish(plain(405, "Method not allowed. Use POST with JSON-RPC.", { allow: "POST" }));
    if (!(req.headers.get("content-type") ?? "").toLowerCase().includes("application/json")) {
      return finish(plain(415, "Content-Type must be application/json"));
    }
    const text = await readCapped(req);
    if (text === null) return finish(plain(413, "Request body is larger than 32 KiB"));
    let body: unknown;
    try {
      body = JSON.parse(text);
      if (tooDeep(body)) return finish(rpcError(400, -32600, "Request nesting is too deep"));
      Object.assign(line, describe(body, req));
    } catch {
      return finish(rpcError(400, -32700, "Parse error"));
    }
    const inner = new Request(req.url, { method: "POST", headers: req.headers, body: text });
    const record: CallRecord = {};
    records.set(inner, record);
    let res: Response;
    try {
      res = (await isLegacyRequest(inner, body, { maxRequestBodySize: MAX_BODY_BYTES }))
        ? await legacy(inner, body, record)
        : await modern.fetch(inner, { parsedBody: body });
    } catch {
      res = rpcError(500, -32603, "Internal error");
    }
    line.result_code = record.result;
    return finish(res);
  };
}
