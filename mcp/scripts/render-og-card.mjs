// Renders public/media/og-card.png (1200x630), the link-preview image for mcp.nobrainer.tech.
// It is a manual step: the PNG is committed and served as a static file, nothing in the build calls this.
// Same direction as the Flo and MC P social banners: the brand card ("nobrainer.tech/flow", "From task to done."
// and one MCP line) on the day horizon, Flo on the left, MC P on the right.
//
// Brand assets are unchanged: scripts/og/*.svg are the outlined lockup and tagline from the nobrainer-tech-brand
// skill, the font, horizon and sprite sheets are the ones the landing page already serves from public/.
// Usage: node scripts/render-og-card.mjs [--out path.png]
// Needs headless Chrome or Chromium: set CHROME_BIN, or install it in a standard location.
import { spawnSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const W = 1200;
const H = 630;
const here = (rel) => fileURLToPath(new URL(rel, import.meta.url));
const fileUrl = (rel) => new URL(rel, import.meta.url).href;
const args = process.argv.slice(2);
const flag = (name) => args.indexOf(name);
const out = flag("--out") >= 0 ? args[flag("--out") + 1] : here("../public/media/og-card.png");

const LINE = "<b>Free remote MCP server</b> for your AI coding agent";
const LOCKUP = { file: "og/nobrainer-tech-flow-icon32.svg", ratio: 1086.7 / 95.4, width: 440 }; // -32 master: lockup type 21..48 px
const TAGLINE = { file: "og/tagline.svg", ratio: 843.8 / 74.6, width: 700 };
const SKY = "#BCD2FF";    // top row of horizon-day.png
const GROUND = "#FFF7EC"; // ground of horizon-day.png and the logo fin cream

// horizon-day.png is a 400x150 pixel tile; every pixel is drawn K px wide. Sprites sit on art row 119.
const K = 4;
const FEET = 532;
const TILE_TOP = FEET - 119 * K;
// Trimmed frames cut out of the sprite sheets in public/media: sheet size, then the frame's x, y, w, h in art pixels.
const FLO = { sheet: "../public/media/flo-dance.png", sw: 1248, sh: 123, x: 4 * 156 + 42, y: 1, w: 76, h: 121, scale: 2 };
const MCP = { sheet: "../public/media/mcp-poses.png", sw: 928, sh: 60, x: 34, y: 4, w: 47, h: 55, scale: 4 };
const CARD = { x: 214, y: 96, w: 772, h: 296 };

const sprite = ({ sheet, sw, sh, x, y, w, h, scale }, left) => {
  const style = `left:${left}px;top:${FEET - h * scale}px;width:${w * scale}px;height:${h * scale}px;`
    + `background:url(${fileUrl(sheet)}) -${x * scale}px -${y * scale}px / ${sw * scale}px ${sh * scale}px no-repeat`;
  return `<div class="abs px" style="${style}"></div>`;
};
const svg = ({ file, ratio, width }, alt) =>
  `<img src="${fileUrl(file)}" style="display:block;width:${width}px;height:${(width / ratio).toFixed(2)}px" alt="${alt}">`;

const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><style>
@font-face{font-family:"NoBrainer Sans";src:url(${fileUrl("../public/fonts/NoBrainerSans-var.woff2")}) format("woff2");font-weight:100 900}
:root{--card:#FFFCF7;--ink:#202124;--muted:#485162}
*{box-sizing:border-box}
html,body{margin:0;width:${W}px;height:${H}px;overflow:hidden;background:${GROUND};color:var(--ink);
font-family:"NoBrainer Sans",system-ui,sans-serif;-webkit-font-smoothing:antialiased}
.abs{position:absolute}
.px{image-rendering:pixelated}
.card{left:${CARD.x}px;top:${CARD.y}px;width:${CARD.w}px;height:${CARD.h}px;background:var(--card);border-radius:28px 8px 28px 8px;
box-shadow:0 2px 4px #17294314,0 9px 22px #17294320;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
.line{margin-top:22px;font-size:31px;line-height:1.2;font-weight:500;color:var(--muted);white-space:nowrap}
.line b{font-weight:700;color:var(--ink)}
</style></head><body>
<div class="abs" style="inset:0;background:url(${fileUrl("../public/media/horizon-day.png")}) ${W / 2 - 200 * K}px ${TILE_TOP}px / ${400 * K}px ${150 * K}px repeat-x,linear-gradient(${SKY} 0 ${TILE_TOP + 2}px,${GROUND} ${TILE_TOP + 2}px);image-rendering:pixelated"></div>
<div class="abs card">${svg(LOCKUP, "nobrainer.tech/flow")}<div style="height:22px"></div>${svg(TAGLINE, "From task to done.")}<div class="line">${LINE}</div></div>
${sprite(FLO, 38)}
${sprite(MCP, W - 38 - MCP.w * MCP.scale)}
</body></html>`;

const work = mkdtempSync(join(tmpdir(), "nbf-og-"));
try {
  const page = join(work, "card.html");
  writeFileSync(page, html);
  const candidates = [
    process.env.CHROME_BIN,
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
  ].filter(Boolean);
  const chrome = candidates.find((c) => (c.includes("/") ? existsSync(c) : spawnSync(c, ["--version"]).status === 0));
  if (!chrome) throw new Error("no Chrome or Chromium found: set CHROME_BIN");
  const run = spawnSync(chrome, [
    "--headless=new", `--screenshot=${out}`, `--window-size=${W},${H}`, "--force-device-scale-factor=1",
    "--disable-gpu", "--hide-scrollbars", "--no-sandbox", "--allow-file-access-from-files",
    `--user-data-dir=${join(work, "profile")}`, "--virtual-time-budget=6000", `file://${page}`,
  ], { encoding: "utf8", timeout: 120000 });
  if (run.status !== 0) throw new Error(`chrome exited ${run.status}: ${run.stderr.slice(-300)}`);
  // PNG signature, then IHDR width and height at bytes 16..23
  const png = readFileSync(out);
  const ok = png.length > 1000 && png.subarray(1, 4).toString() === "PNG" && png.readUInt32BE(16) === W && png.readUInt32BE(20) === H;
  if (!ok) throw new Error(`${out} is not a ${W}x${H} PNG`);
  console.log(`wrote ${out} (${png.length} bytes, ${W}x${H})`);
} catch (err) {
  console.error(`og-card: ${err.message}`);
  process.exitCode = 1;
} finally {
  rmSync(work, { recursive: true, force: true });
}
