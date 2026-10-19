import { test } from "node:test";
import assert from "node:assert/strict";
import { randomBytes } from "node:crypto";
import {
  CONTRACT_PREFIX, LIFETIME_S, MAX_AGE_S, RECEIPT_PREFIX, decodeToken, encodeToken, parseKeyRing, renew, type TokenState,
} from "../../src/token.ts";
import { ToolError } from "../../src/errors.ts";

const k1 = randomBytes(32).toString("base64");
const k2 = randomBytes(32).toString("base64");
const ring = parseKeyRing(`1:${k1}`);
const NOW = 1_800_000_000;

export function sampleState(n = 3, files = 0): TokenState {
  return {
    kid: 1, full: true, verdict: "NONE", risks: ["security", "ambiguous"], contract: randomBytes(8),
    created: NOW, expires: NOW + LIFETIME_S, flow: [2, 4, 1], epoch: 3,
    items: Array.from({ length: n }, (_, i) => ({
      proof: "test" as const, level: "deployed" as const, failures: i % 4, status: "ACCEPTED" as const,
      kind: "test" as const, unchecked: i === 1, epoch: 2, digest: randomBytes(4),
    })),
    files: Array.from({ length: files }, () => ({ path: randomBytes(4), hash: randomBytes(4) })),
  };
}

const code = (fn: () => unknown): string => {
  try {
    fn();
  } catch (e) {
    assert.ok(e instanceof ToolError);
    return e.code;
  }
  return "NO_ERROR";
};

test("round trip preserves every field", () => {
  const s = sampleState(10, 8);
  const back = decodeToken(encodeToken(s, CONTRACT_PREFIX, ring), CONTRACT_PREFIX, ring, NOW + 1);
  assert.deepEqual({ ...back, kid: 1 }, s);
});

test("maximum token is 176 bytes (240 characters)", () => {
  const t = encodeToken(sampleState(10, 8), CONTRACT_PREFIX, ring);
  assert.equal(Buffer.from(t.slice(5), "base64url").length, 176);
  assert.ok(t.length <= 240, String(t.length));
});

test("any single bit flip is rejected", () => {
  const t = encodeToken(sampleState(2, 1), CONTRACT_PREFIX, ring);
  const raw = Buffer.from(t.slice(5), "base64url");
  for (let byte = 0; byte < raw.length; byte++) {
    for (let bit = 0; bit < 8; bit++) {
      const copy = Buffer.from(raw);
      copy[byte] = (copy[byte] as number) ^ (1 << bit);
      const c = code(() => decodeToken(`nbf1.${copy.toString("base64url")}`, CONTRACT_PREFIX, ring, NOW));
      assert.ok(["TOKEN_INVALID", "TOKEN_KEY_RETIRED"].includes(c), `byte ${byte} bit ${bit}: ${c}`);
    }
  }
});

test("prefix is part of the MAC: a contract cannot pose as a receipt and vice versa", () => {
  const t = encodeToken(sampleState(), CONTRACT_PREFIX, ring);
  assert.equal(code(() => decodeToken(t.replace("nbf1.", "nbr1."), RECEIPT_PREFIX, ring, NOW)), "TOKEN_INVALID");
  assert.equal(code(() => decodeToken(t, RECEIPT_PREFIX, ring, NOW)), "NOT_A_RECEIPT");
  const r = encodeToken(sampleState(), RECEIPT_PREFIX, ring);
  assert.equal(code(() => decodeToken(r, CONTRACT_PREFIX, ring, NOW)), "TOKEN_INVALID");
});

test("garbage, wrong prefix and truncation are TOKEN_INVALID", () => {
  const t = encodeToken(sampleState(), CONTRACT_PREFIX, ring);
  for (const bad of ["", "nbf1.", "nbf1.!!!", "xyz1.AAAA", t.slice(0, -4), `${t}AA`, t.replace("nbf1.", "nbf2.")]) {
    assert.equal(code(() => decodeToken(bad, CONTRACT_PREFIX, ring, NOW)), "TOKEN_INVALID", bad.slice(0, 12));
  }
});

test("expiry, renewal cap at 90 days", () => {
  const s = sampleState();
  const t = encodeToken(s, CONTRACT_PREFIX, ring);
  assert.equal(code(() => decodeToken(t, CONTRACT_PREFIX, ring, s.expires)), "TOKEN_EXPIRED");
  assert.equal(renew(s, NOW + 10).expires, NOW + 10 + LIFETIME_S);
  assert.equal(renew(s, NOW + 80 * 86400).expires, NOW + MAX_AGE_S);
});

test("key rotation: new key signs, old key still verifies; retired key is rejected", () => {
  const old = encodeToken(sampleState(), CONTRACT_PREFIX, ring);
  const rotated = parseKeyRing(`2:${k2},1:${k1}`);
  assert.equal(rotated.signer, 2);
  assert.doesNotThrow(() => decodeToken(old, CONTRACT_PREFIX, rotated, NOW));
  const fresh = encodeToken(sampleState(), CONTRACT_PREFIX, rotated);
  assert.equal(Buffer.from(fresh.slice(5), "base64url")[1], 2);
  const retired = parseKeyRing(`2:${k2}`);
  assert.equal(code(() => decodeToken(old, CONTRACT_PREFIX, retired, NOW)), "TOKEN_KEY_RETIRED");
});

test("a token signed by another key with the same kid is TOKEN_INVALID", () => {
  const other = parseKeyRing(`1:${k2}`);
  const t = encodeToken(sampleState(), CONTRACT_PREFIX, other);
  assert.equal(code(() => decodeToken(t, CONTRACT_PREFIX, ring, NOW)), "TOKEN_INVALID");
});

test("key ring parsing rejects short keys, duplicates and empty input", () => {
  assert.throws(() => parseKeyRing(""));
  assert.throws(() => parseKeyRing(`1:${randomBytes(16).toString("base64")}`));
  assert.throws(() => parseKeyRing(`1:${k1},1:${k2}`));
  assert.throws(() => parseKeyRing("300:" + k1));
});

test("token holds no plaintext: only binary fields", () => {
  const t = encodeToken(sampleState(), CONTRACT_PREFIX, ring);
  assert.match(t, /^nbf1\.[A-Za-z0-9_-]+$/);
});
