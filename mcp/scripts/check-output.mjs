// Pre-deploy gate for a prebuilt upload: run after `vercel build --prod`, before `vercel deploy --prebuilt`.
// Fails on native modules, darwin paths, a non-x86_64 architecture or a runtime other than Node.js 22.
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative, resolve } from "node:path";

const root = process.argv[2] ?? ".vercel/output";
const problems = [];
let functions = 0;

function walk(dir) {
  for (const name of readdirSync(dir)) {
    const path = join(dir, name);
    const rel = relative(root, path);
    if (/darwin/i.test(rel)) problems.push(`darwin path: ${rel}`);
    if (statSync(path).isDirectory()) walk(path);
    else if (name.endsWith(".node")) problems.push(`native module: ${rel}`);
    else if (name === ".vc-config.json") {
      functions++;
      const cfg = JSON.parse(readFileSync(path, "utf8"));
      if (cfg.runtime !== "nodejs22.x") problems.push(`runtime ${cfg.runtime} in ${rel}`);
      if (cfg.architecture !== "x86_64") problems.push(`architecture ${cfg.architecture ?? "unset"} in ${rel}`);
      // Mapped files are uploaded with the function too: check both the destination and the source.
      for (const [to, from] of Object.entries(cfg.filePathMap ?? {})) {
        for (const p of [to, String(from)]) {
          if (p.endsWith(".node")) problems.push(`native module (mapped): ${p} in ${rel}`);
          if (/darwin/i.test(p)) problems.push(`darwin path (mapped): ${p} in ${rel}`);
        }
        if (!existsSync(resolve(root, "../..", String(from)))) problems.push(`mapped source missing: ${from} in ${rel}`);
      }
    }
  }
}

try {
  walk(root);
  JSON.parse(readFileSync(join(root, "config.json"), "utf8"));
} catch (err) {
  problems.push(`cannot read ${root}: ${err.message}`);
}
if (functions < 3) problems.push(`expected 3 functions, found ${functions}`);
if (problems.length) {
  console.error(`CHECK_OUTPUT_FAILED\n${problems.join("\n")}`);
  process.exit(1);
}
console.log(`CHECK_OUTPUT_OK functions=${functions} runtime=nodejs22.x native=0 darwin=0`);
