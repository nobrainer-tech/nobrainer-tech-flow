// recommend_flow_model: ranks models from the pinned NoBrainer benchmark snapshot (no network).
import { AdvisorInputError, RECOMMEND_TOOL, recommendFlowModel, recommendInput } from "../advisor/index.ts";
import { ToolError } from "../errors.ts";
import type { ToolDef } from "./common.ts";

export const recommendTool: ToolDef<typeof recommendInput> = {
  name: RECOMMEND_TOOL.name,
  title: RECOMMEND_TOOL.title,
  description: RECOMMEND_TOOL.description,
  input: recommendInput,
  run(args, ctx) {
    try {
      return recommendFlowModel(args, new Date(ctx.now() * 1000));
    } catch (err) {
      if (err instanceof AdvisorInputError) throw new ToolError("INVALID_INPUT", err.why, err.fix);
      throw err;
    }
  },
};
