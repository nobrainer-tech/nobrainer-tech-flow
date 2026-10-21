// OpenAI submission package: manifest shape (Agent Plugins 1.0.0 schemas) and ZIP contents.
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pluginEntries, zip } from "../../scripts/build-plugin.ts";

const entries = pluginEntries();
const json = (name: string) => JSON.parse(entries.find((e) => e.name === name)!.data.toString("utf8"));

test("ZIP holds only plugin.json, mcp.json, brand assets and LICENSE: no skills, hooks or .app.json", () => {
  assert.deepEqual(entries.map((e) => e.name), ["plugin.json", "mcp.json", "assets/logo.png", "assets/icon.png", "assets/logo.svg", "LICENSE"]);
});

test("plugin.json follows the Agent Plugins manifest schema and OpenAI limits", () => {
  const p = json("plugin.json");
  const allowed = ["$schema", "name", "version", "description", "author", "homepage", "repository", "license", "keywords", "extensions"];
  for (const k of Object.keys(p)) assert.ok(allowed.includes(k), k);
  assert.equal(p.$schema, "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json");
  assert.match(p.name, /^(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?$/);
  const ui = p.extensions["com.openai"].interface;
  assert.ok(ui.displayName.length <= 30 && ui.shortDescription.length <= 30);
  assert.ok(ui.longDescription.length <= 4000);
  assert.ok(!/MCP|Plugin/.test(ui.displayName));
  assert.equal(ui.brandColor, "#3B65F0");
  assert.equal(ui.privacyPolicyURL, "https://nobrainer.tech/flow/privacy/");
  assert.equal(ui.termsOfServiceURL, "https://nobrainer.tech/flow/terms/");
  for (const ref of [ui.logo, ui.composerIcon]) assert.ok(entries.some((e) => `./${e.name}` === ref), ref);
});

test("mcp.json: one streamable-http server, HTTPS, no headers, no properties outside the schema", () => {
  const m = json("mcp.json");
  assert.deepEqual(Object.keys(m).sort(), ["$schema", "mcpServers"]);
  const servers = Object.entries(m.mcpServers) as Array<[string, Record<string, unknown>]>;
  assert.equal(servers.length, 1);
  const [name, server] = servers[0]!;
  assert.equal(name, "nobrainer-tech-flow");
  assert.deepEqual(Object.keys(server).sort(), ["type", "url"]);
  assert.equal(server.type, "streamable-http");
  assert.equal(server.url, "https://mcp.nobrainer.tech/mcp");
});

test("logo is the brand PNG, square 512 x 512", () => {
  const png = entries.find((e) => e.name === "assets/logo.png")!.data;
  assert.equal(png.subarray(1, 4).toString(), "PNG");
  assert.equal(png.readUInt32BE(16), 512);
  assert.equal(png.readUInt32BE(20), 512);
  assert.match(entries.find((e) => e.name === "assets/logo.svg")!.data.toString(), /#3B65F0/);
});

test("the ZIP is valid and deterministic", (t) => {
  const a = zip(entries);
  assert.deepEqual(a, zip(entries));
  let listing: string;
  const dir = mkdtempSync(join(tmpdir(), "nbf-zip-"));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  const file = join(dir, "p.zip");
  writeFileSync(file, a);
  try {
    listing = execFileSync("python3", ["-c", "import sys,zipfile;z=zipfile.ZipFile(sys.argv[1]);assert z.testzip() is None;print('\\n'.join(z.namelist()))", file], { encoding: "utf8" });
  } catch (err) {
    t.skip(`python3 unavailable: ${(err as Error).message.slice(0, 60)}`);
    return;
  }
  assert.deepEqual(listing.trim().split("\n"), entries.map((e) => e.name));
});
