// start_flow_task rules: path, lint, routing, owner gates and version note (spec 5.1).
import { DEFAULT_LEVEL, REACHABLE, type Level, type Proof, type Risk } from "./levels.ts";
import { ToolError } from "../errors.ts";

export type DodInput = { text: string; proof: Proof; level?: Level | undefined };
export type ContractInput = {
  outcome: string;
  dod: DodInput[];
  non_goals?: string[] | undefined;
  risks?: Risk[] | undefined;
  local_flow?: string | undefined;
};
export type NormalisedItem = { text: string; proof: Proof; level: Level };

// Control characters except tab and newline are removed; whitespace is collapsed.
export function normaliseText(s: string): string {
  return s.replace(/[\u0000-\u0008\u000b-\u001f\u007f]/g, "").replace(/\s+/g, " ").trim();
}

export function normaliseItems(dod: DodInput[]): NormalisedItem[] {
  return dod.map((d, i) => {
    const text = normaliseText(d.text);
    if (!text) throw new ToolError("INVALID_INPUT", `dod[${i}].text is empty`, "describe the observable check for this item");
    const level = d.level ?? DEFAULT_LEVEL[d.proof];
    if (!REACHABLE[d.proof].includes(level)) {
      throw new ToolError(
        "INVALID_INPUT",
        `dod[${i}]: proof ${d.proof} cannot reach level ${level}`,
        `use level ${REACHABLE[d.proof].join(", ")} for ${d.proof}, or another proof kind`,
      );
    }
    return { text, proof: d.proof, level };
  });
}

const QUICK_LEVELS: readonly Level[] = ["static", "local"];

export function choosePath(items: NormalisedItem[], risks: Risk[]): "QUICK" | "FULL" {
  const quick = risks.length === 0 && items.length <= 3 && items.every((i) => QUICK_LEVELS.includes(i.level));
  return quick ? "QUICK" : "FULL";
}

const VAGUE = new Set([
  "works", "it works", "working", "looks good", "look good", "all good", "tests pass", "test passes",
  "tests passing", "is done", "done", "fixed", "it is fixed", "complete", "completed", "passes", "ok", "good",
]);
const PATH_LIKE = /(^|[\s(`'"])([\w.-]*\/[\w./-]+|[\w-]+\.[A-Za-z0-9]{1,8})(?=$|[\s)`'",;:])/;
const URL_LIKE = /https?:\/\/\S+|\b[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}\b/i;

export function lint(items: NormalisedItem[], path: "QUICK" | "FULL", nonGoals: string[]): string[] {
  const out: string[] = [];
  const seen = new Map<string, number>();
  items.forEach((item, i) => {
    const id = `AC${String(i + 1).padStart(2, "0")}`;
    const bare = item.text.toLowerCase().replace(/[.!?]+$/, "").trim();
    if (VAGUE.has(bare)) out.push(`${id}: VAGUE: name the observable check.`);
    if (item.proof === "file" && !PATH_LIKE.test(item.text)) out.push(`${id}: NO_TARGET: name the file path.`);
    if (item.proof === "url" && !URL_LIKE.test(item.text)) out.push(`${id}: NO_TARGET: name the URL or host.`);
    const prior = seen.get(bare);
    if (prior !== undefined) out.push(`${id}: DUPLICATE: same text as AC${String(prior + 1).padStart(2, "0")}.`);
    else seen.set(bare, i);
  });
  if (path === "FULL" && nonGoals.length === 0) out.push("NO_NON_GOALS: list what this task will not do.");
  return out;
}

/** Module routing derived from the Flow routing reference (spec 5.1 step 4). */
export function route(path: "QUICK" | "FULL", risks: Risk[], items: NormalisedItem[]): { modules: string[]; optional: string[] } {
  const modules: string[] = [];
  if (path === "FULL") modules.push("nobrainer-build", "nobrainer-review");
  if (risks.includes("security")) modules.push("nobrainer-security");
  if (risks.includes("ambiguous")) modules.push("nobrainer-decide");
  if (risks.includes("public_contract")) modules.push("nobrainer-spec-driven-development");
  if (risks.includes("multi_session")) modules.push("nobrainer-sessions");
  const optional: string[] = [];
  const rendered = items.some((i) => i.proof === "url" && ["deployed", "production", "delivered"].includes(i.level));
  if (rendered) optional.push("nobrainer-browser");
  return { modules, optional };
}

/** Every module name the routing table can emit; tests check them against the release. */
export const ROUTED_MODULES = [
  "nobrainer-build", "nobrainer-review", "nobrainer-security", "nobrainer-decide",
  "nobrainer-spec-driven-development", "nobrainer-sessions", "nobrainer-browser", "nobrainer-rca",
] as const;

export function needsGates(risks: Risk[]): boolean {
  return risks.includes("irreversible") || risks.includes("external_effect");
}

function parseVersion(v: string): [number, number, number] | null {
  const m = /^v?(\d{1,3})\.(\d{1,3})\.(\d{1,3})/.exec(v.trim());
  return m ? [Number(m[1]), Number(m[2]), Number(m[3])] : null;
}

export function compareVersions(a: [number, number, number], b: [number, number, number]): number {
  for (let i = 0; i < 3; i++) if (a[i] !== b[i]) return (a[i] as number) - (b[i] as number);
  return 0;
}

export function flowTriple(version: string): [number, number, number] {
  const v = parseVersion(version);
  if (!v) throw new Error(`bad Flow version ${version}`);
  return v;
}

/** A note when the client's local Flow is older than the pinned release, or unparseable. */
export function versionNote(local: string | undefined, server: string): string | undefined {
  if (!local) return undefined;
  const lv = parseVersion(local);
  if (!lv) return `local_flow is not a version; gate rules follow Flow ${server}.`;
  if (compareVersions(lv, flowTriple(server)) < 0) {
    return `Local Flow is older than ${server}; gate rules follow Flow ${server}.`;
  }
  return undefined;
}
