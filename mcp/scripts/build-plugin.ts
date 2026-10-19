// Build the OpenAI plugin submission ZIP (MCP only: no skills, no hooks, no .app.json).
// Usage: node scripts/build-plugin.ts [--output <file.zip>]
import { crc32, deflateRawSync } from "node:zlib";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const MCP = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const ROOT = resolve(MCP, "..");

export type Entry = { name: string; data: Buffer };

/** The files the submission ZIP contains, in order. */
export function pluginEntries(): Entry[] {
  const manifest = JSON.parse(readFileSync(resolve(MCP, "plugin/plugin.json"), "utf8"));
  const mcp = JSON.parse(readFileSync(resolve(MCP, "plugin/mcp.json"), "utf8"));
  const version = JSON.parse(readFileSync(resolve(MCP, "package.json"), "utf8")).version;
  if (manifest.version !== version) throw new Error(`plugin.json version ${manifest.version} != package.json ${version}`);
  const urls = Object.values(mcp.mcpServers as Record<string, { url: string }>).map((s) => s.url);
  if (urls.length !== 1 || !urls[0]!.startsWith("https://")) throw new Error("exactly one HTTPS MCP server is required");
  const logo = readFileSync(resolve(ROOT, "assets/plugin-logo.png"));
  return [
    { name: "plugin.json", data: Buffer.from(`${JSON.stringify(manifest, null, 2)}\n`) },
    { name: "mcp.json", data: Buffer.from(`${JSON.stringify(mcp, null, 2)}\n`) },
    { name: "assets/logo.png", data: logo },
    { name: "assets/icon.png", data: logo },
    { name: "assets/logo.svg", data: readFileSync(resolve(ROOT, "assets/nobrainer-tech-logo.svg")) },
    { name: "LICENSE", data: readFileSync(resolve(ROOT, "LICENSE")) },
  ];
}

/** Minimal deterministic ZIP writer (deflate, fixed 1980-01-01 timestamps). */
export function zip(entries: Entry[]): Buffer {
  const locals: Buffer[] = [];
  const centrals: Buffer[] = [];
  let offset = 0;
  for (const { name, data } of entries) {
    const nameBuf = Buffer.from(name, "utf8");
    const packed = deflateRawSync(data, { level: 9 });
    const crc = crc32(data);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4); local.writeUInt16LE(0x0800, 6); local.writeUInt16LE(8, 8);
    local.writeUInt16LE(0, 10); local.writeUInt16LE(0x21, 12);
    local.writeUInt32LE(crc, 14); local.writeUInt32LE(packed.length, 18); local.writeUInt32LE(data.length, 22);
    local.writeUInt16LE(nameBuf.length, 26); local.writeUInt16LE(0, 28);
    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(0x0314, 4); central.writeUInt16LE(20, 6); central.writeUInt16LE(0x0800, 8); central.writeUInt16LE(8, 10);
    central.writeUInt16LE(0, 12); central.writeUInt16LE(0x21, 14);
    central.writeUInt32LE(crc, 16); central.writeUInt32LE(packed.length, 20); central.writeUInt32LE(data.length, 24);
    central.writeUInt16LE(nameBuf.length, 28);
    central.writeUInt32LE((0o100644 << 16) >>> 0, 38);
    central.writeUInt32LE(offset, 42);
    locals.push(local, nameBuf, packed);
    centrals.push(central, nameBuf);
    offset += local.length + nameBuf.length + packed.length;
  }
  const cd = Buffer.concat(centrals);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(entries.length, 8); end.writeUInt16LE(entries.length, 10);
  end.writeUInt32LE(cd.length, 12); end.writeUInt32LE(offset, 16);
  return Buffer.concat([...locals, cd, end]);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const i = process.argv.indexOf("--output");
  const version = JSON.parse(readFileSync(resolve(MCP, "package.json"), "utf8")).version;
  const out = resolve(i > 0 ? process.argv[i + 1]! : resolve(MCP, `dist/nobrainer-tech-flow-${version}.zip`));
  if (existsSync(out)) throw new Error(`${out} exists; choose a fresh path`);
  mkdirSync(dirname(out), { recursive: true });
  const entries = pluginEntries();
  const data = zip(entries);
  writeFileSync(out, data);
  console.log(`PLUGIN_ZIP_READY ${out} files=${entries.length} bytes=${data.length} skills=0 hooks=none`);
}
