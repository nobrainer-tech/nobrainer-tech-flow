import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "url";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const skillsDirectory = path.resolve(currentDirectory, "../../skills");
const bootstrapPath = path.resolve(currentDirectory, "../../adapters/bootstrap.md");
const bootstrapMarker = "NOBRAINER_BOOTSTRAP_V1";
let bootstrapCache;

const getBootstrap = () => {
  if (bootstrapCache === undefined) {
    bootstrapCache = readFileSync(bootstrapPath, "utf8");
  }
  return bootstrapCache;
};

const hasBootstrap = (parts) =>
  parts.some(
    (part) =>
      part?.type === "text" &&
      typeof part.text === "string" &&
      part.text.includes(bootstrapMarker),
  );

export const NoBrainerTechSkillsPlugin = async () => ({
  config: async (config) => {
    config.skills = config.skills || {};
    config.skills.paths = config.skills.paths || [];
    if (!config.skills.paths.includes(skillsDirectory)) {
      config.skills.paths.push(skillsDirectory);
    }
  },
  "experimental.chat.messages.transform": async (_input, output) => {
    try {
      if (!Array.isArray(output.messages)) return;
      const firstUser = output.messages.find((message) => message.info?.role === "user");
      if (!firstUser || !Array.isArray(firstUser.parts) || hasBootstrap(firstUser.parts)) {
        return;
      }
      const bootstrap = getBootstrap().trimEnd();
      const textPart = firstUser.parts.find(
        (part) => part.type === "text" && typeof part.text === "string",
      );
      if (textPart) {
        textPart.text = `${bootstrap}\n\n${textPart.text}`;
        return;
      }
      // After compaction (or with an attachment-only first message) the first user
      // message has no text part to prefix, so add one for this request only.
      firstUser.parts.unshift({
        id: `${firstUser.info?.id ?? "message"}-nobrainer-bootstrap`,
        sessionID: firstUser.info?.sessionID,
        messageID: firstUser.info?.id,
        type: "text",
        text: bootstrap,
        synthetic: true,
      });
    } catch {
      // The bootstrap is advisory context: a missing or unreadable file must never
      // break the host's prompt loop.
    }
  },
});

export default NoBrainerTechSkillsPlugin;
