// One content-free log line per request (spec 12.4). Never: bodies, arguments, tokens, IPs, user agents.

export type LogLine = {
  route: string;
  status: number;
  rpc_method?: string | undefined;
  tool?: string | undefined;
  result_code?: string | undefined;
  duration_ms?: number;
  response_bytes?: number;
  protocol_version?: string | undefined;
  client_name?: string | undefined;
  rejected_origin?: string | undefined;
};

export function logLine(line: LogLine): void {
  console.log(JSON.stringify({ ts: new Date().toISOString(), ...line }));
}
