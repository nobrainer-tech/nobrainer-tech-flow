// Vercel Function for /mcp (rewritten to /api/mcp). The logic lives in dist/, built from src/ by `npm run build`.
import { createHttpHandler } from "../dist/http.js";
import { optionsFromEnv } from "../dist/config.js";

let handler;
let failed = false;

function serve(request) {
  if (!handler && !failed) {
    try {
      handler = createHttpHandler(optionsFromEnv());
    } catch {
      failed = true;
      console.error(JSON.stringify({ level: "error", code: "CONFIG", route: "/api/mcp" }));
    }
  }
  if (!handler) return new Response("Service not configured", { status: 503, headers: { "cache-control": "no-store" } });
  return handler(request);
}

export { serve as GET, serve as POST, serve as DELETE, serve as PUT, serve as PATCH, serve as OPTIONS, serve as HEAD };

// Build for x86_64 even when `vercel build` runs on an arm64 machine (owner rule for prebuilt uploads).
export const config = { architecture: "x86_64" };
