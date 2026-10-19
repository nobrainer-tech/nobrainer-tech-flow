// Binary contract token and done receipt with HMAC-SHA-256 (spec section 6).
import { createHmac, timingSafeEqual } from "node:crypto";
import { LEVELS, PROOFS, RISKS, type Level, type Proof, type Risk } from "./rules/levels.ts";
import { ToolError } from "./errors.ts";

export const CONTRACT_PREFIX = "nbf1";
export const RECEIPT_PREFIX = "nbr1";
const FORMAT = 0x01;
const MAC_BYTES = 16;
export const MAX_ITEMS = 10;
export const MAX_FILES = 8;
const DAY = 86_400;
export const LIFETIME_S = 30 * DAY;
export const MAX_AGE_S = 90 * DAY;

export const STATUS = ["OPEN", "ACCEPTED", "FAILED"] as const;
export type Status = (typeof STATUS)[number];
export const VERDICTS = ["NONE", "DONE", "DONE_WITH_GAPS"] as const;
export type ReceiptVerdict = (typeof VERDICTS)[number];

export type Item = {
  proof: Proof;
  level: Level;
  failures: number; // 0-3
  status: Status;
  kind: Proof | null; // kind of the accepting (or last failing) record
  unchecked: boolean; // receipts only
  epoch: number; // change epoch at acceptance
  digest: Buffer; // 4 bytes of the record digest, zeros when none
};

export type FileEntry = { path: Buffer; hash: Buffer }; // 4 bytes each

export type TokenState = {
  kid: number;
  full: boolean;
  verdict: ReceiptVerdict;
  risks: Risk[];
  contract: Buffer; // 8 bytes
  created: number;
  expires: number;
  flow: [number, number, number];
  epoch: number;
  items: Item[];
  files: FileEntry[];
};

export type KeyRing = { signer: number; keys: Map<number, Buffer> };

/** Parse `FLOW_TOKEN_KEYS="<kid>:<base64>,<kid>:<base64>"`; the first entry signs. */
export function parseKeyRing(raw: string | undefined): KeyRing {
  const keys = new Map<number, Buffer>();
  let signer = -1;
  for (const part of (raw ?? "").split(",").map((p) => p.trim()).filter(Boolean)) {
    const m = /^(\d{1,3}):([A-Za-z0-9+/=_-]+)$/.exec(part);
    if (!m?.[1] || !m[2]) throw new Error("FLOW_TOKEN_KEYS entry is malformed");
    const kid = Number(m[1]);
    const key = Buffer.from(m[2], "base64");
    if (kid > 255 || key.length < 32) throw new Error("FLOW_TOKEN_KEYS needs kid 0-255 and 32-byte keys");
    if (keys.has(kid)) throw new Error("FLOW_TOKEN_KEYS has a duplicate kid");
    keys.set(kid, key);
    if (signer < 0) signer = kid;
  }
  if (signer < 0) throw new Error("FLOW_TOKEN_KEYS is empty");
  return { signer, keys };
}

function mac(prefix: string, key: Buffer, payload: Buffer): Buffer {
  return createHmac("sha256", key).update(prefix).update(payload).digest().subarray(0, MAC_BYTES);
}

export function encodeToken(state: TokenState, prefix: string, ring: KeyRing): string {
  const n = state.items.length;
  const f = state.files.length;
  if (n < 1 || n > MAX_ITEMS || f > MAX_FILES) throw new Error("token state out of range");
  const buf = Buffer.alloc(25 + 7 * n + 1 + 8 * f);
  let o = 0;
  buf[o++] = FORMAT;
  buf[o++] = ring.signer;
  buf[o++] = (state.full ? 1 : 0) | (VERDICTS.indexOf(state.verdict) << 1);
  buf[o++] = state.risks.reduce((m, r) => m | (1 << RISKS.indexOf(r)), 0);
  state.contract.copy(buf, o, 0, 8); o += 8;
  buf.writeUInt32BE(state.created, o); o += 4;
  buf.writeUInt32BE(state.expires, o); o += 4;
  for (const v of state.flow) buf[o++] = Math.min(255, v);
  buf[o++] = state.epoch;
  buf[o++] = n;
  for (const it of state.items) {
    buf[o++] = PROOFS.indexOf(it.proof) | (LEVELS.indexOf(it.level) << 3) | (Math.min(3, it.failures) << 6);
    const kind = it.kind === null ? 7 : PROOFS.indexOf(it.kind);
    buf[o++] = STATUS.indexOf(it.status) | (kind << 2) | (it.unchecked ? 1 << 5 : 0);
    buf[o++] = it.epoch;
    it.digest.copy(buf, o, 0, 4); o += 4;
  }
  buf[o++] = f;
  for (const fe of state.files) {
    fe.path.copy(buf, o, 0, 4); o += 4;
    fe.hash.copy(buf, o, 0, 4); o += 4;
  }
  const key = ring.keys.get(ring.signer);
  if (!key) throw new Error("signing key missing");
  return `${prefix}.${Buffer.concat([buf, mac(prefix, key, buf)]).toString("base64url")}`;
}

const invalid = () =>
  new ToolError("TOKEN_INVALID", "the token is malformed or was changed", "use the token from the last Flow tool result, unmodified");

function enumAt<T>(list: readonly T[], i: number): T {
  const v = list[i];
  if (v === undefined) throw invalid();
  return v;
}

/** Verify and decode. `expect` is the prefix the caller needs; the other prefix gets NOT_A_RECEIPT. */
export function decodeToken(token: string, expect: string, ring: KeyRing, now: number): TokenState {
  const dot = token.indexOf(".");
  const prefix = token.slice(0, dot);
  if (dot < 0 || (prefix !== CONTRACT_PREFIX && prefix !== RECEIPT_PREFIX)) throw invalid();
  const body = token.slice(dot + 1);
  if (!/^[A-Za-z0-9_-]+$/.test(body)) throw invalid();
  const raw = Buffer.from(body, "base64url");
  if (raw.length < 25 + 7 + 1 + MAC_BYTES || raw.toString("base64url") !== body) throw invalid();
  const buf = raw.subarray(0, raw.length - MAC_BYTES);
  const tag = raw.subarray(raw.length - MAC_BYTES);
  if (buf[0] !== FORMAT) throw invalid();
  const kid = buf[1] as number;
  const key = ring.keys.get(kid);
  if (!key) {
    throw new ToolError("TOKEN_KEY_RETIRED", "the token was signed with a retired key", "call start_flow_task again with the same contract");
  }
  if (!timingSafeEqual(mac(prefix, key, buf), tag)) throw invalid();
  if (prefix !== expect) {
    if (expect === RECEIPT_PREFIX) {
      throw new ToolError("NOT_A_RECEIPT", "a contract token was given where a done receipt is needed", "call check_flow_done first and pass its receipt");
    }
    throw new ToolError("TOKEN_INVALID", "a done receipt was given where a contract token is needed", "pass the contract token from the last Flow tool result");
  }
  return parsePayload(buf, kid, now);
}

function parsePayload(buf: Buffer, kid: number, now: number): TokenState {
  let o = 2;
  const flags = buf[o++] as number;
  const riskBits = buf[o++] as number;
  const contract = Buffer.from(buf.subarray(o, o + 8)); o += 8;
  const created = buf.readUInt32BE(o); o += 4;
  const expires = buf.readUInt32BE(o); o += 4;
  const flow: [number, number, number] = [buf[o] as number, buf[o + 1] as number, buf[o + 2] as number]; o += 3;
  const epoch = buf[o++] as number;
  const n = buf[o++] as number;
  if (n < 1 || n > MAX_ITEMS || buf.length < o + 7 * n + 1) throw invalid();
  const items: Item[] = [];
  for (let i = 0; i < n; i++) {
    const a = buf[o++] as number;
    const b = buf[o++] as number;
    const kindIdx = (b >> 2) & 7;
    items.push({
      proof: enumAt(PROOFS, a & 7),
      level: enumAt(LEVELS, (a >> 3) & 7),
      failures: a >> 6,
      status: enumAt(STATUS, b & 3),
      kind: kindIdx === 7 ? null : enumAt(PROOFS, kindIdx),
      unchecked: (b & (1 << 5)) !== 0,
      epoch: buf[o++] as number,
      digest: Buffer.from(buf.subarray(o, o + 4)),
    });
    o += 4;
  }
  const f = buf[o++] as number;
  if (f > MAX_FILES || buf.length !== o + 8 * f) throw invalid();
  const files: FileEntry[] = [];
  for (let i = 0; i < f; i++, o += 8) {
    files.push({ path: Buffer.from(buf.subarray(o, o + 4)), hash: Buffer.from(buf.subarray(o + 4, o + 8)) });
  }
  if (now >= expires) {
    throw new ToolError("TOKEN_EXPIRED", "the contract token has expired", "call start_flow_task again with the same contract");
  }
  return {
    kid,
    full: (flags & 1) === 1,
    verdict: enumAt(VERDICTS, (flags >> 1) & 3),
    risks: RISKS.filter((_, i) => (riskBits & (1 << i)) !== 0),
    contract, created, expires, flow, epoch, items, files,
  };
}

/** Extend the lifetime on reissue: now + 30 days, capped at created + 90 days. */
export function renew(state: TokenState, now: number): TokenState {
  return { ...state, expires: Math.min(now + LIFETIME_S, state.created + MAX_AGE_S) };
}

export const hex8 = (b: Buffer): string => b.subarray(0, 4).toString("hex");
export const itemId = (i: number): string => `AC${String(i + 1).padStart(2, "0")}`;
