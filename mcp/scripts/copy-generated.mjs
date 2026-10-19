// Copy generated JSON next to the compiled modules (dist/ mirrors src/).
import { cpSync, mkdirSync } from "node:fs";

const from = new URL("../src/generated/", import.meta.url);
const to = new URL("../dist/generated/", import.meta.url);
mkdirSync(to, { recursive: true });
cpSync(from, to, { recursive: true });
