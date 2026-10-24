// Landing pages: the newsletter section sits right after the PROVE IT block on both languages, reuses
// the shared nobrainer.tech EmailOctopus form, loads it lazily and keeps a plain fallback link.
import { test } from "node:test";
import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const read = (path: string) => readFileSync(new URL(`../../public/${path}`, import.meta.url), "utf8");
const pages = { en: read("index.html"), pl: read("pl/index.html") };
const FORM_ID = "8b8c07c6-adbf-11f1-aace-2317bc0d803d";

function newsletter(html: string): string {
  const start = html.indexOf('<section class="newsletter"');
  assert.ok(start > 0, "newsletter section missing");
  return html.slice(start, html.indexOf("</section>", start) + "</section>".length);
}

for (const [lang, html] of Object.entries(pages)) {
  test(`${lang}: newsletter follows the PROVE IT block and precedes the hero`, () => {
    const tv = html.indexOf('<section class="tv"');
    const section = html.indexOf('<section class="newsletter"');
    const hero = html.indexOf('<section class="hero"');
    assert.ok(tv > 0 && tv < section && section < hero, `order tv=${tv} newsletter=${section} hero=${hero}`);
    assert.ok(html.indexOf("</section>", tv) < section, "newsletter must not sit inside the PROVE IT block");
  });

  test(`${lang}: newsletter reuses the shared form, lazily, with a fallback and the required notices`, () => {
    const s = newsletter(html);
    assert.match(s, /id="newsletter" aria-labelledby="newsletter-title" data-newsletter/);
    assert.match(s, /<h2 id="newsletter-title">/);
    assert.ok(s.includes(`data-eo-form="${FORM_ID}"`));
    assert.ok(s.includes(`data-eo-src="https://eocampaign1.com/form/${FORM_ID}.js?rev=20260926-powered-by-disabled"`));
    assert.ok(s.includes('<a href="https://nobrainer.tech/newsletter/">'), "fallback link");
    assert.ok(s.includes('<a href="https://nobrainer.tech/privacy/">'), "privacy link");
    assert.ok(s.includes("reCAPTCHA") && s.includes("https://policies.google.com/privacy") && s.includes("https://policies.google.com/terms"));
    for (const attr of ["data-email-label", "data-submit", "data-consent", "data-confirmation"]) {
      assert.match(s, new RegExp(`${attr}="[^"]+"`), attr);
    }
    // The provider script is ~540 KB: the page must not load it eagerly.
    assert.doesNotMatch(html, /<script[^>]+eocampaign1\.com/);
    assert.match(html, /<script src="\/media\/newsletter\.js\?v=\d+" defer><\/script>/);
    assert.doesNotMatch(s, /—/, "plain hyphens only");
  });
}

test("pl: newsletter copy is translated and says the newsletter is in English", () => {
  const s = newsletter(pages.pl);
  assert.match(pages.pl, /<html lang="pl">/);
  for (const text of [
    '<h2 id="newsletter-title">Śledź Flo i MC P</h2>',
    "Newsletter jest po angielsku.",
    'data-submit="Zapisz się"',
    'data-email-label="Adres e-mail"',
    'data-consent="Chcę otrzymywać od nobrainer.tech',
    "Jeśli formularz się nie wczyta,",
    "Formularz jest chroniony przez reCAPTCHA.",
  ]) assert.ok(s.includes(text), text);
  assert.doesNotMatch(s, /Follow Flo|No spam|Privacy policy|I want practical/);
});

test("newsletter script exists and waits for the section to near the viewport", () => {
  const path = new URL("../../public/media/newsletter.js", import.meta.url);
  assert.ok(existsSync(path));
  const js = readFileSync(path, "utf8");
  assert.match(js, /IntersectionObserver/);
  assert.match(js, /addEventListener\('load'/);
});
