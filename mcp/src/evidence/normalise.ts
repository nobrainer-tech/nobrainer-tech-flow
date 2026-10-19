// Output normalisation shared by the digest, the parsers and the secret screen.

const ANSI_OSC = /\u001b\][^\u0007\u001b]{0,2000}(?:\u0007|\u001b\\)/g;
const ANSI_CSI = /\u001b\[[0-?]{0,32}[ -/]{0,8}[@-~]/g;
const ANSI_OTHER = /\u001b[@-_]/g;
// Control characters except tab (09) and newline (0A).
const CONTROL = /[\u0000-\u0008\u000B-\u001F\u007F]/g;
// Control characters that are not whitespace.
const CONTROL_NON_SPACE = /[\u0000-\u0008\u000E-\u001F\u007F]/g;

export const OUT_MAX_CHARS = 4000;

/** Strip ANSI, CRLF/CR -> LF, drop control chars, trim, keep the last 4,000 characters. */
export function normaliseOut(s: string): string {
  return s
    .replace(ANSI_OSC, '')
    .replace(ANSI_CSI, '')
    .replace(ANSI_OTHER, '')
    .replace(/\r\n?/g, '\n')
    .replace(CONTROL, '')
    .trim()
    .slice(-OUT_MAX_CHARS);
}

/** For short fields: drop control chars, collapse whitespace, trim. */
export function normaliseText(s: string): string {
  return s.replace(CONTROL_NON_SPACE, '').replace(/\s+/g, ' ').trim();
}
