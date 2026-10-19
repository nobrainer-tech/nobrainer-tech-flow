// Tool execution errors (spec 4.4): returned as normal results with isError true.

export type ErrorCode =
  | "INVALID_INPUT"
  | "INPUT_TOO_LARGE"
  | "TOKEN_INVALID"
  | "TOKEN_EXPIRED"
  | "TOKEN_KEY_RETIRED"
  | "NOT_A_RECEIPT"
  | "UNKNOWN_ITEM"
  | "UNKNOWN_CARD"
  | "SECRET_DETECTED"
  | "RATE_LIMITED"
  | "BUDGET_EXCEEDED"
  | "INTERNAL";

export class ToolError extends Error {
  readonly code: ErrorCode;
  readonly why: string;
  readonly fix: string;
  constructor(code: ErrorCode, why: string, fix: string) {
    super(`${code}: ${why}`);
    this.code = code;
    this.why = why;
    this.fix = fix;
  }
  toJSON(): { error: { code: ErrorCode; why: string; fix: string } } {
    return { error: { code: this.code, why: this.why, fix: this.fix } };
  }
}

export const internalError = (): ToolError =>
  new ToolError("INTERNAL", "the server hit an unexpected error", "retry once; if it repeats, report it at https://github.com/nobrainer-tech/nobrainer-tech-flow/issues");
