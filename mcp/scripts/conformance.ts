// Run the official MCP conformance suite against a local server with the documented baseline.
// Usage: node scripts/conformance.ts   (exit code from the suite)
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { startServer } from "./serve.ts";
import { createHttpHandler } from "../src/http.ts";
import { optionsFromEnv } from "../src/config.ts";

const server = await startServer(createHttpHandler({ ...optionsFromEnv({}), log: () => {} }), 0);
const address = server.address();
const url = `http://127.0.0.1:${typeof address === "object" && address ? address.port : 0}/mcp`;
const out = mkdtempSync(join(tmpdir(), "nbf-conformance-"));
const bin = fileURLToPath(new URL("../node_modules/.bin/conformance", import.meta.url));
const baseline = fileURLToPath(new URL("../test/conformance-baseline.yml", import.meta.url));
// Async spawn: the server runs in this process and must keep answering while the suite runs.
const child = spawn(bin, ["server", "--url", url, "--spec-version", "2025-11-25", "--expected-failures", baseline, "-o", out]);
let stdout = "";
let stderr = "";
child.stdout.on("data", (d) => { stdout += String(d); });
child.stderr.on("data", (d) => { stderr += String(d); });
const status: number = await new Promise((resolve) => child.on("close", (code) => resolve(code ?? 1)));
console.log((stdout.split("=== SUMMARY ===")[1] ?? stdout).trim());
if (stderr.trim()) console.error(stderr.trim().split("\n").slice(-5).join("\n"));
rmSync(out, { recursive: true, force: true });
server.close();
process.exit(status);
