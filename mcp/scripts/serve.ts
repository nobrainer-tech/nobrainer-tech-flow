// Local server: the same web handler as the Vercel function, on node:http.
// Usage: node scripts/serve.ts [--port 8787]   (binds 127.0.0.1 only)
import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { readFileSync } from "node:fs";
import { Readable } from "node:stream";
import { createHttpHandler } from "../src/http.ts";
import { optionsFromEnv } from "../src/config.ts";

const PUBLIC = new URL("../public/", import.meta.url);

export function startServer(handler: (req: Request) => Promise<Response>, port: number) {
  const server = createServer(async (req: IncomingMessage, res: ServerResponse) => {
    try {
      const url = new URL(req.url ?? "/", `http://${req.headers.host ?? "127.0.0.1"}`);
      if (url.pathname === "/" || url.pathname === "/.well-known/openai-apps-challenge") {
        const file = url.pathname === "/" ? "index.html" : ".well-known/openai-apps-challenge";
        const type = url.pathname === "/" ? "text/html; charset=utf-8" : "text/plain; charset=utf-8";
        res.writeHead(200, { "content-type": type }).end(readFileSync(new URL(file, PUBLIC)));
        return;
      }
      if (url.pathname !== "/mcp" && url.pathname !== "/api/mcp") {
        res.writeHead(404, { "content-type": "text/plain" }).end("Not found");
        return;
      }
      const headers = new Headers();
      for (const [k, v] of Object.entries(req.headers)) if (v !== undefined) headers.set(k, Array.isArray(v) ? v.join(", ") : v);
      const hasBody = req.method !== "GET" && req.method !== "HEAD";
      const request = new Request(url, {
        method: req.method,
        headers,
        body: hasBody ? (Readable.toWeb(req) as ReadableStream) : undefined,
        duplex: "half",
      } as RequestInit);
      const response = await handler(request);
      res.writeHead(response.status, Object.fromEntries(response.headers));
      res.end(Buffer.from(await response.arrayBuffer()));
    } catch {
      if (!res.headersSent) res.writeHead(500, { "content-type": "text/plain" });
      res.end("Internal error");
    }
  });
  return new Promise<typeof server>((resolve) => server.listen(port, "127.0.0.1", () => resolve(server)));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const i = process.argv.indexOf("--port");
  const port = Number(i > 0 ? process.argv[i + 1] : process.env.PORT ?? 8787);
  const server = await startServer(createHttpHandler(optionsFromEnv()), port);
  const address = server.address();
  console.error(`nobrainer-tech-flow MCP listening on http://127.0.0.1:${typeof address === "object" && address ? address.port : port}/mcp`);
}
