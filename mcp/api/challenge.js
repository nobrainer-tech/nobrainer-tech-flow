// Vercel Function for /.well-known/openai-apps-challenge: returns the OpenAI domain-verification
// token from the OPENAI_APPS_CHALLENGE environment variable, or 404 when it is not set.
function challenge() {
  const token = (process.env.OPENAI_APPS_CHALLENGE ?? "").trim();
  if (!token) return new Response("Not found", { status: 404, headers: { "cache-control": "no-store" } });
  return new Response(token, { status: 200, headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" } });
}

export { challenge as GET, challenge as HEAD };

// Build for x86_64 even when `vercel build` runs on an arm64 machine (owner rule for prebuilt uploads).
export const config = { architecture: "x86_64" };
