// Writes public/pl/index.html from the English landing page and content/landing.pl.json,
// a list of [english, polish] pairs. Every English string must still be on the page, so an
// edit to the English copy fails here until its translation is updated.
// Flags: --check compares instead of writing.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';

const source = new URL('../public/index.html', import.meta.url);
const target = new URL('../public/pl/index.html', import.meta.url);
const pairs = JSON.parse(readFileSync(new URL('../content/landing.pl.json', import.meta.url), 'utf8'));

let html = readFileSync(source, 'utf8');
const missing = pairs.filter(([en]) => !html.includes(en)).map(([en]) => en);
if (missing.length) {
  console.error('landing: English strings no longer on the page:\n- ' + missing.join('\n- '));
  process.exit(1);
}
for (const [en, pl] of pairs) html = html.split(en).join(pl);

if (process.argv.includes('--check')) {
  let current = '';
  try { current = readFileSync(target, 'utf8'); } catch {}
  if (current !== html) {
    console.error('landing: public/pl/index.html is out of date; run npm run build:landing');
    process.exit(1);
  }
  console.log('LANDING_OK pairs=' + pairs.length);
} else {
  mkdirSync(new URL('../public/pl/', import.meta.url), { recursive: true });
  writeFileSync(target, html);
  console.log('wrote public/pl/index.html (' + pairs.length + ' pairs)');
}
