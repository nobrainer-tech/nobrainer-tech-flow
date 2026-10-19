// Proof kinds, evidence levels and the rules that relate them (spec sections 5.1 and 7.2).

export const PROOFS = ["test", "command", "file", "url", "observation"] as const;
export type Proof = (typeof PROOFS)[number];

export const LEVELS = ["static", "local", "deployed", "production", "delivered", "user"] as const;
export type Level = (typeof LEVELS)[number];

export const RISKS = [
  "public_contract",
  "irreversible",
  "external_effect",
  "multi_session",
  "security",
  "ambiguous",
] as const;
export type Risk = (typeof RISKS)[number];

export const DEFAULT_LEVEL: Record<Proof, Level> = {
  file: "static",
  test: "local",
  command: "local",
  url: "deployed",
  observation: "user",
};

// Ordered ladder; `delivered` and `user` sit outside it (spec 7.2).
const LADDER: readonly Level[] = ["static", "local", "deployed", "production"];

/** Levels each proof kind can ever reach, so a contract never asks for the impossible. */
export const REACHABLE: Record<Proof, readonly Level[]> = {
  file: ["static"],
  test: ["static", "local", "deployed"],
  command: ["static", "local", "deployed"],
  url: ["static", "local", "deployed", "production", "delivered"],
  observation: ["user"],
};

/** Does a record proving `have` satisfy an item that needs `need`? */
export function levelSatisfies(have: Level, need: Level): boolean {
  if (need === "user") return have === "user";
  if (need === "delivered") return have === "production" || have === "delivered";
  const h = LADDER.indexOf(have === "delivered" ? "production" : have);
  const n = LADDER.indexOf(need);
  return h >= 0 && n >= 0 && h >= n;
}

/** Evidence kind `kind` may prove an item whose proof is `proof` (test also proves command). */
export function kindMatches(kind: Proof, proof: Proof): boolean {
  return kind === proof || (kind === "test" && proof === "command");
}

const LOCAL_SUFFIXES = [".localhost", ".local", ".internal"];

function ipv4Local(host: string): boolean | null {
  const m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(host);
  if (!m) return null;
  const [a, b] = [Number(m[1]), Number(m[2])];
  if ([a, b, Number(m[3]), Number(m[4])].some((x) => x > 255)) return true;
  return (
    a === 0 || a === 10 || a === 127 || (a === 172 && b >= 16 && b <= 31) ||
    (a === 192 && b === 168) || (a === 169 && b === 254)
  );
}

/** Host classification without DNS (spec 7.2). Unknown or malformed hosts count as local. */
export function isPublicHost(hostname: string): boolean {
  const host = hostname.toLowerCase().replace(/^\[|\]$/g, "").replace(/\.$/, "");
  if (!host || host === "localhost" || LOCAL_SUFFIXES.some((s) => host.endsWith(s))) return false;
  const v4 = ipv4Local(host);
  if (v4 !== null) return !v4;
  if (host.includes(":")) {
    if (host === "::1" || host === "::") return false;
    if (/^f[cd][0-9a-f]{0,2}:/.test(host) || /^fe[89ab][0-9a-f]?:/.test(host)) return false;
    const mapped = /^::ffff:(\d+\.\d+\.\d+\.\d+)$/.exec(host);
    if (mapped?.[1]) return ipv4Local(mapped[1]) === false;
    return true;
  }
  return host.includes(".");
}

export type UrlClass = { ok: false } | { ok: true; https: boolean; publicHost: boolean };

export function classifyUrl(raw: string): UrlClass {
  let u: URL;
  try {
    u = new URL(raw);
  } catch {
    return { ok: false };
  }
  if (u.protocol !== "https:" && u.protocol !== "http:") return { ok: false };
  return { ok: true, https: u.protocol === "https:", publicHost: isPublicHost(u.hostname) };
}
