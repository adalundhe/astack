---
name: idk
description: "Dispatch researchers, synthesize concise explanations, diagrams, and interactive demos. Use when a user indicates unfamiliarity with a concept, problem, discipline, technology, or reference."
disable-model-invocation: true
---

# IDK

Help a user get grounded quickly when their prompt signals unfamiliarity with a domain, problem, technology, concept, reference, or tool choice. **Owned exclusively by the Lead.**

## 1. Anchor to the user's real work first

Inspect what the user is actually building before researching in a vacuum (**rtfm**, **lookup**, **analyze-environment**):

- Check the current repo, stack, configs, and local dev setup.
- Check saved records under `$HOME/.astack/<project_name>/` (`astack-tools research list`, `docs list`, `lessons list`, `arch list`).
- Name the user's actual goal. Every explanation and demo should tie back to it.

## 2. Dispatch researchers for verified primary sources

Dispatch read-only `astack:researcher` subagents (`roles.researcher`, per **lead**) using **research-this**:

- Gather primary sources—official docs, specs, standards, tools, trade-offs, and pitfalls. Verify quotes in place and grade findings A–F.
- Cover both core concepts and practical tool picks. Show when each tool fits and when it does not.
- Save external research under `$HOME/.astack/<project_name>/research/<topic>` (`%USERPROFILE%\.astack\...` on Windows; `ASTACK_HOME` overrides). Resolve paths via `astack-tools research path <project_name> <topic> --ensure`.

## 3. Synthesize for first-read understanding

Turn the research into a direct guide (**talk-to-me**, **show-the-states**, **wat**):

- **Bottom line & tool picks:** state what matters first, which tools fit, and why.
- **Visuals & diagrams:** add Mermaid state charts, architecture flows, or sequence diagrams (**show-the-states**) showing components, states, and data flow.
- **Grounded analogies:** give short analogies tied to their codebase. State where each analogy breaks down (**talk-to-me**).
- **Verified references:** link authoritative primary sources and cite the saved `$HOME/.astack/<project_name>/research/` path.

## 4. Build an interactive demo with a walkthrough

Let the user try the concept hands-on using **play-with-me** whenever practical:

- Build a runnable interactive demo the user can run and modify. Dispatch an isolated `astack:worker` for non-trivial demos, and keep throwaway files outside production code.
- **Connect to local dev when relevant:** if **analyze-environment** confirmed a relevant local dev stack, wire the **play-with-me** demo against it safely. Keep demos non-destructive and never touch prod or real user data.
- Verify the demo yourself first (**prove-it**).
- Give a concise walkthrough: one command to start, 2–4 things to try, what to observe, and how each maps to their goal.

**Done when:** research is saved under `$HOME/.astack/<project_name>/research/` and summarized with diagrams, analogies, and references. Wherever practical, include a verified **play-with-me** demo with a concise walkthrough.

Referenced skills: `rtfm` (`${CLAUDE_SKILL_DIR}/../rtfm/SKILL.md`), `lookup` (`${CLAUDE_SKILL_DIR}/../lookup/SKILL.md`), `analyze-environment` (`${CLAUDE_SKILL_DIR}/../analyze-environment/SKILL.md`), `lead` (`${CLAUDE_SKILL_DIR}/../lead/SKILL.md`), `research-this` (`${CLAUDE_SKILL_DIR}/../research-this/SKILL.md`), `talk-to-me` (`${CLAUDE_SKILL_DIR}/../talk-to-me/SKILL.md`), `show-the-states` (`${CLAUDE_SKILL_DIR}/../show-the-states/SKILL.md`), `wat` (`${CLAUDE_SKILL_DIR}/../wat/SKILL.md`), `play-with-me` (`${CLAUDE_SKILL_DIR}/../play-with-me/SKILL.md`), `prove-it` (`${CLAUDE_SKILL_DIR}/../prove-it/SKILL.md`). Read any cited skill file before acting when its trigger applies.
