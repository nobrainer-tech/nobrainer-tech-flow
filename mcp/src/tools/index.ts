// The six tools in their fixed tools/list order.
import type { ToolDef } from "./common.ts";
import { startTool } from "./start.ts";
import { stepTool } from "./step.ts";
import { evidenceTool } from "./evidence.ts";
import { doneTool } from "./done.ts";
import { handoffTool } from "./handoff.ts";
import { recommendTool } from "./recommend.ts";

export const TOOLS: readonly ToolDef[] = [startTool, stepTool, evidenceTool, doneTool, handoffTool, recommendTool] as unknown as ToolDef[];
