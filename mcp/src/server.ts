// McpServer factory: six tools, one prompt, one resource template and the instructions (spec 9).
import * as z from "zod";
import { McpServer, ResourceTemplate } from "@modelcontextprotocol/server";
import { ToolError, internalError } from "./errors.ts";
import { serialise, toAscii } from "./budget.ts";
import { scanInput } from "./evidence/secrets.ts";
import { FLOW_VERSION, cardIds, getCard } from "./content/cards.ts";
import { ANNOTATIONS, jsonSchemaOf, parseArgs, type ToolContext, type ToolDef } from "./tools/common.ts";
import { TOOLS } from "./tools/index.ts";

export const SERVER_NAME = "nobrainer-tech-flow";
export const SERVER_VERSION = `1.0.0+flow.${FLOW_VERSION}`;

export const INSTRUCTIONS =
  "NoBrainer Tech Flow keeps one task contract and one done gate across every MCP client. For non-trivial work: start_flow_task fixes outcome and definition of done, check_flow_evidence records proof, check_flow_done gates the completion claim. Guidance already loaded from a local Flow skill need not be fetched again with get_flow_step.";

/** Per-request facts the content-free log line reports. */
export type CallRecord = { tool?: string; result?: string };

/** Advertise the zod-derived JSON Schema but validate inside the handler, after secret screening. */
function passThrough(schema: z.ZodObject) {
  const json = jsonSchemaOf(schema);
  return {
    "~standard": {
      version: 1 as const,
      vendor: "nobrainer-tech-flow",
      validate: (value: unknown) => ({ value }),
      jsonSchema: { input: () => json, output: () => json },
    },
  };
}

const knownKeys = new WeakMap<ToolDef, ReadonlySet<string>>();

/** Every property name in a tool's input schema; error texts may name only these. */
function schemaKeys(def: ToolDef): ReadonlySet<string> {
  let keys = knownKeys.get(def);
  if (!keys) {
    const found = new Set<string>();
    const visit = (node: unknown): void => {
      if (!node || typeof node !== "object") return;
      const props = (node as { properties?: Record<string, unknown> }).properties;
      if (props) for (const k of Object.keys(props)) found.add(k);
      Object.values(node as object).forEach(visit);
    };
    visit(jsonSchemaOf(def.input));
    keys = found;
    knownKeys.set(def, keys);
  }
  return keys;
}

export async function runTool(def: ToolDef, raw: unknown, ctx: ToolContext, record?: CallRecord) {
  if (record) record.tool = def.name;
  try {
    const hit = scanInput(raw, schemaKeys(def));
    if (hit?.pattern === "too_deep") throw new ToolError("INVALID_INPUT", "the input is nested more than 8 levels deep", "send arguments shaped like the tool schema");
    if (hit) {
      throw new ToolError("SECRET_DETECTED", `${hit.field} looks like it contains a secret (${hit.pattern})`, `remove the secret from ${hit.field} and resend`);
    }
    const result = await def.run(parseArgs(def.input, raw), ctx);
    const text = serialise(result);
    if (record) record.result = "OK";
    return { content: [{ type: "text" as const, text }] };
  } catch (err) {
    const e = err instanceof ToolError ? err : internalError();
    if (!(err instanceof ToolError)) console.error(JSON.stringify({ level: "error", code: "INTERNAL", tool: def.name, name: (err as Error)?.name ?? "unknown" }));
    if (record) record.result = e.code;
    return { content: [{ type: "text" as const, text: toAscii(e.toJSON()) }], isError: true };
  }
}

export function buildServer(ctx: ToolContext, record?: CallRecord): McpServer {
  const server = new McpServer(
    { name: SERVER_NAME, version: SERVER_VERSION, title: "NoBrainer Tech Flow" },
    { instructions: INSTRUCTIONS, capabilities: { tools: {}, prompts: {}, resources: {} } },
  );
  for (const def of TOOLS) {
    server.registerTool(
      def.name,
      { title: def.title, description: def.description, inputSchema: passThrough(def.input), annotations: { ...ANNOTATIONS } },
      (raw: unknown) => runTool(def, raw, ctx, record),
    );
  }
  server.registerPrompt(
    "flow",
    {
      title: "Run a task with Flow",
      description: "Run one task with the Flow contract, evidence and done gate.",
      argsSchema: z.object({ task: z.string().max(500).describe("The task to run") }),
    },
    ({ task }) => ({
      messages: [{
        role: "user" as const,
        content: {
          type: "text" as const,
          text: `Run this task with the NoBrainer Tech Flow tools: start_flow_task first, check_flow_evidence after each check, check_flow_done before calling it done, then draft_flow_handoff.\n\nTask: ${task}`,
        },
      }],
    }),
  );
  server.registerResource(
    "flow-card",
    new ResourceTemplate("flow://card/{id}", {
      list: async () => ({ resources: cardIds().map((id) => ({ uri: `flow://card/${id}`, name: id, mimeType: "application/json" })) }),
    }),
    { title: "Flow guidance card", description: "One guidance card from the pinned Flow release.", mimeType: "application/json" },
    async (uri, vars) => {
      const id = decodeURIComponent(String(Array.isArray(vars.id) ? vars.id[0] : vars.id));
      const card = getCard(id);
      if (!card) throw new ToolError("UNKNOWN_CARD", "no guidance card with that id", "list resources to see valid card ids");
      return { contents: [{ uri: uri.href, mimeType: "application/json", text: toAscii({ ...card, flow_version: FLOW_VERSION }) }] };
    },
  );
  return server;
}
