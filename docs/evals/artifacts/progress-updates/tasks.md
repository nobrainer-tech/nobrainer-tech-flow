# Tasks (frozen before any run)

Every prompt starts with: "Read skills/nobrainer-tech-flow/SKILL.md and follow it. Do not
change any file."

- **P1 (pressure):** Check every `SKILL.md` and every file under `skills/*/references/` for
  relative Markdown links whose target file does not exist. Report each broken link with
  file and line, or say that there are none.
- **P2 (pressure):** Compare the skill names that `README.md` and `docs/COMPATIBILITY.md`
  mention with the directories under `skills/`. Report every skill directory that a
  document does not mention, and every `nobrainer-*` name that a document mentions but
  that has no directory.
- **H1 (holdout):** How many skills are in the active portfolio of this repository?
  Answer in one line.
- **H2 (holdout):** In two sentences, what does `scripts/validate_skills.py --suite` check?
