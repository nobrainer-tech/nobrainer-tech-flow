// Pre-dispatch checks on the parsed JSON-RPC message. The SDK echoes unknown tool, prompt and
// resource names in its errors; this layer answers those cases first with fixed text, so no
// caller-supplied string reaches a response or a log line (review finding 3 and 4).
import { TOOLS } from "./tools/index.ts";
import { cardIds } from "./content/cards.ts";
import { findSecret } from "./evidence/secrets.ts";

export const TOOL_NAMES: readonly string[] = TOOLS.map((t) => t.name);
const CARD_IDS = new Set(cardIds());
function knownCard(uri: unknown): boolean {
  if (typeof uri !== "string" || !uri.startsWith("flow://card/")) return false;
  try {
    return CARD_IDS.has(decodeURIComponent(uri.slice("flow://card/".length)));
  } catch {
    return false;
  }
}
const KNOWN_METHODS = new Set([
  "initialize", "ping", "server/discover", "tools/list", "tools/call", "prompts/list", "prompts/get",
  "resources/list", "resources/templates/list", "resources/read", "subscriptions/listen", "logging/setLevel",
  "completion/complete", "notifications/initialized", "notifications/cancelled", "notifications/progress",
  "notifications/roots/list_changed",
]);

export type Rejection = { status: number; body: Record<string, unknown> };

const rpcError = (status: number, id: unknown, code: number, message: string): Rejection => ({
  status,
  body: { jsonrpc: "2.0", id, error: { code, message } },
});

const validId = (id: unknown): boolean =>
  id === null || (typeof id === "number" && Number.isFinite(id)) || (typeof id === "string" && id.length <= 128);

/** Returns a fixed-text rejection, or null when the message may go to the SDK (possibly sanitised). */
export function guardMessage(body: unknown): Rejection | null {
  if (Array.isArray(body)) return rpcError(400, null, -32600, "Batch requests are not supported");
  if (!body || typeof body !== "object") return rpcError(400, null, -32600, "Invalid request");
  const msg = body as Record<string, unknown>;
  if ("id" in msg && !validId(msg.id)) return rpcError(400, null, -32600, "Invalid request id");
  if (!("id" in msg)) return null; // Let the transport accept notifications without a response.
  const params = (msg.params && typeof msg.params === "object" ? msg.params : {}) as Record<string, unknown>;
  const id = msg.id ?? null;
  switch (msg.method) {
    case "tools/call":
      if (typeof params.name !== "string" || !TOOL_NAMES.includes(params.name)) {
        return rpcError(200, id, -32602, "Unknown tool. tools/list returns the tool names.");
      }
      return null;
    case "prompts/get":
      if (params.name !== "flow") return rpcError(200, id, -32602, "Unknown prompt. prompts/list returns the prompt names.");
      delete params.arguments; // the prompt takes no arguments and never reflects caller text
      return null;
    case "resources/read":
      if (!knownCard(params.uri)) {
        return rpcError(200, id, -32602, "Unknown resource. resources/list returns the card URIs.");
      }
      return null;
    default:
      return null;
  }
}

/** Log-safe forms of caller-supplied identifiers: canonical names or a fixed marker. */
export function logSafe(method: unknown, tool: unknown, version: unknown, client: unknown) {
  const name = typeof client === "string" ? (findSecret(client) ? "redacted" : client.replace(/[^A-Za-z0-9 ._-]/g, "").slice(0, 40)) : undefined;
  return {
    rpc_method: typeof method === "string" ? (KNOWN_METHODS.has(method) ? method : "other") : undefined,
    tool: method === "tools/call" ? (typeof tool === "string" && TOOL_NAMES.includes(tool) ? tool : "unknown") : undefined,
    protocol_version: typeof version === "string" ? (/^\d{4}-\d{2}-\d{2}$/.test(version) ? version : "other") : undefined,
    client_name: name ? (findSecret(name) ? "redacted" : name) : undefined,
  };
}

const FIXED: Record<number, string> = {
  [-32700]: "Parse error",
  [-32600]: "Invalid request",
  [-32601]: "Method not found",
  [-32602]: "Invalid params",
  [-32603]: "Internal error",
  [-32020]: "MCP request headers and body disagree",
};

/**
 * Protocol errors from the SDK may quote caller input (method names, header values, URIs).
 * Replace every message with fixed text per code and keep only a version list as data, which
 * clients need to negotiate the protocol revision.
 */
export function sanitizeErrorBody(text: string): string {
  let msg: Record<string, any>;
  try {
    msg = JSON.parse(text);
  } catch {
    return text;
  }
  const err = msg && typeof msg === "object" && !Array.isArray(msg) ? msg.error : undefined;
  if (!err || typeof err !== "object") return text;
  const code = Number.isInteger(err.code) ? err.code : -32603;
  const supported = Array.isArray(err.data?.supported) ? err.data.supported.filter((v: unknown) => typeof v === "string" && /^\d{4}-\d{2}-\d{2}$/.test(v)) : null;
  const clean: Record<string, unknown> = { code, message: FIXED[code] ?? `Request failed (${code})` };
  if (supported?.length) clean.data = { supported };
  const id = typeof msg.id === "number" || (typeof msg.id === "string" && msg.id.length <= 128) ? msg.id : null;
  return JSON.stringify({ jsonrpc: "2.0", id, error: clean });
}
