// Link previews: both landing pages carry the Open Graph and Twitter card tags, they point at one committed
// 1200x630 PNG on the production host, and the deploy serves that PNG as a static file from public/.
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync, statSync } from "node:fs";

const root = new URL("../../", import.meta.url);
const read = (path: string) => readFileSync(new URL(path, root), "utf8");
const ORIGIN = "https://mcp.nobrainer.tech";
const IMAGE_PATH = "/media/og-card.png";
const IMAGE = `${ORIGIN}${IMAGE_PATH}`;
const pages = {
  en: { html: read("public/index.html"), url: `${ORIGIN}/`, locale: "en_US", alternate: "pl_PL" },
  pl: { html: read("public/pl/index.html"), url: `${ORIGIN}/pl/`, locale: "pl_PL", alternate: "en_US" },
};

function head(html: string): string {
  return html.slice(0, html.indexOf("</head>"));
}

/** Every <meta property|name> in the head, by key; each key may repeat, so values are lists. */
function metas(html: string): Map<string, string[]> {
  const found = new Map<string, string[]>();
  for (const m of head(html).matchAll(/<meta\s+(?:property|name)="([^"]+)"\s+content="([^"]*)"\s*>/g)) {
    found.set(m[1]!, [...(found.get(m[1]!) ?? []), m[2]!]);
  }
  return found;
}

function one(tags: Map<string, string[]>, key: string): string {
  const values = tags.get(key);
  assert.ok(values, `${key} missing`);
  assert.equal(values.length, 1, `${key} must appear exactly once`);
  assert.ok(values[0]!.trim().length > 0, `${key} is empty`);
  return values[0]!;
}

function link(html: string, rel: string, extra = ""): string[] {
  return [...head(html).matchAll(new RegExp(`<link rel="${rel}"${extra} href="([^"]+)">`, "g"))].map((m) => m[1]!);
}

for (const [lang, page] of Object.entries(pages)) {
  test(`${lang}: Open Graph and Twitter card tags are complete and point at the card image`, () => {
    const tags = metas(page.html);
    assert.equal(one(tags, "og:type"), "website");
    assert.equal(one(tags, "og:site_name"), "NoBrainer Tech Flow MCP");
    assert.equal(one(tags, "og:url"), page.url);
    assert.equal(one(tags, "og:image"), IMAGE);
    assert.equal(one(tags, "og:image:type"), "image/png");
    assert.equal(one(tags, "og:image:width"), "1200");
    assert.equal(one(tags, "og:image:height"), "630");
    assert.equal(one(tags, "og:locale"), page.locale);
    assert.deepEqual(tags.get("og:locale:alternate"), [page.alternate]);
    assert.equal(one(tags, "twitter:card"), "summary_large_image");
    assert.equal(one(tags, "twitter:image"), IMAGE);
    assert.equal(one(tags, "twitter:title"), one(tags, "og:title"));
    assert.equal(one(tags, "twitter:description"), one(tags, "og:description"));
    assert.equal(one(tags, "twitter:image:alt"), one(tags, "og:image:alt"));
  });

  test(`${lang}: preview text fits what the platforms show, with plain hyphens only`, () => {
    const tags = metas(page.html);
    const title = one(tags, "og:title");
    const description = one(tags, "og:description");
    const alt = one(tags, "og:image:alt");
    assert.ok(title.length <= 70, `og:title is ${title.length} characters`);
    assert.ok(description.length <= 200, `og:description is ${description.length} characters`);
    assert.ok(alt.length <= 420, `image alt is ${alt.length} characters`);
    for (const key of ["og:title", "og:description", "og:image:alt"]) assert.doesNotMatch(one(tags, key), /[–—]/, `${key} uses a long dash`);
  });

  test(`${lang}: the share URL is the canonical URL and both languages are linked`, () => {
    const og = one(metas(page.html), "og:url");
    assert.deepEqual(link(page.html, "canonical"), [og]);
    for (const [hreflang, href] of [["en", `${ORIGIN}/`], ["pl", `${ORIGIN}/pl/`], ["x-default", `${ORIGIN}/`]]) {
      assert.deepEqual(link(page.html, "alternate", ` hreflang="${hreflang}"`), [href], `hreflang ${hreflang}`);
    }
  });
}

test("pl: the preview text is written in Polish, not left in English", () => {
  const en = metas(pages.en.html);
  const pl = metas(pages.pl.html);
  for (const key of ["og:title", "og:description", "og:image:alt"]) assert.notEqual(one(pl, key), one(en, key), key);
  assert.match(one(pl, "og:title"), /Gotowe/);
  assert.match(one(pl, "og:description"), /Darmowy zdalny serwer MCP/);
  assert.match(one(pl, "og:image:alt"), /Po bokach/);
  assert.equal(one(pl, "og:image"), one(en, "og:image"), "one shared card image");
});

test("the card image is a 1200x630 PNG inside the folder the deploy serves", () => {
  const vercel = JSON.parse(read("vercel.json"));
  assert.equal(vercel.outputDirectory, "public", "static files come from public/");
  for (const rule of vercel.rewrites ?? []) assert.notEqual(rule.source, IMAGE_PATH);

  const file = new URL(`public${IMAGE_PATH}`, root);
  assert.ok(existsSync(file), `public${IMAGE_PATH} is missing`);
  const png = readFileSync(file);
  assert.equal(png.subarray(1, 4).toString("latin1"), "PNG", "not a PNG");
  assert.equal(png.readUInt32BE(16), 1200, "width");
  assert.equal(png.readUInt32BE(20), 630, "height");
  const { size } = statSync(file);
  assert.ok(size > 20_000, `suspiciously small card image (${size} bytes)`);
  assert.ok(size < 1_000_000, `card image is ${size} bytes; X accepts 5 MB, keep previews light`);
});

test("the card renderer and its brand assets stay in the repo and carry no machine paths", () => {
  for (const path of ["scripts/render-og-card.mjs", "scripts/og/nobrainer-tech-flow-icon32.svg", "scripts/og/tagline.svg"]) {
    assert.ok(existsSync(new URL(path, root)), `${path} is missing`);
    assert.doesNotMatch(read(path), /\/Users\/|\/Volumes\/|\/private\/tmp\//, `${path} contains a local path`);
  }
});
