// Vercel Function: Spend Management webhook that pauses only this project.
import { createSpendHook } from "../dist/spend.js";

const hook = createSpendHook(process.env);

export { hook as POST, hook as GET };

// Build for x86_64 even when `vercel build` runs on an arm64 machine (owner rule for prebuilt uploads).
export const config = { architecture: "x86_64" };
