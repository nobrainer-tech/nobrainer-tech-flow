# Astra review criteria

Primary source: [OpenAI, Eric Provencher, 2026-09-11](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra).
Refresh this reference when a material revision changes the guidance.

The source recommends short, discriminating skill descriptions; conditional
loading of supporting material; less rigid recipes; considering different models
used by contributors; relevant rather than universal `AGENTS.md` reading;
proportionate testing; explicit permission for known-safe work; careful decision
boundaries; and a defined completion point.

Apply those recommendations without turning them into numeric standards:

- flag broad triggers only with a plausible unrelated request;
- locate duplicated or contradictory obligations across active files;
- move specialized procedures behind relevant triggers;
- preserve non-obvious invariants, security requirements and owner choices;
- replace premature stopping with a concrete in-scope completion condition;
- separate confirmed findings from candidates and unexecuted behavior tests.
