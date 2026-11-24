---
name: rtfm
description: "Check the user's message, repo docs/code/history, local environment, and official tool docs before asking questions or claiming to be blocked. Use before asking the person anything."
---

# RTFM

Read what's already available before asking the person anything.

Before asking a question, declaring yourself blocked, calling a requirement unclear, or claiming you lack context, check in order:

1. **What you were already given:** the prompt and thread, your brief, `RULES.md`, earlier decisions in the lane log, and any attached docs or examples.
2. **The repository:** README, docs, architecture decisions, contributor/agent guides, relevant source and tests, and git/PR/issue history for the area.
3. **The local environment:** configs, scripts, CI workflows, installed/running services, and existing logs or outputs.
4. **Official references:** documentation and examples for the tools and libraries involved.

Then actually test what you read—run the command, inspect the source, call the API.

Only ask if nothing above resolves it, and include what you already checked and tried (**decisions-in-plain-words**). Don't ask anything the existing material already answers.
