---
name: how-it-works
description: "Explain how part of a system works, or where a change belongs: the mental model first, then the parts and flow, every claim cited to a file and line and marked run or read. Use before changing unfamiliar code, and for \"how does X work\" or \"where should this live\"."
---

# How it works

Explain how part of a system works, with every claim cited to the code.

If the question could mean more than one thing, say which you're answering and go on.

1. **Read what's written first** (**rtfm**): docs, architecture decisions, READMEs.
2. **Explore read-only,** in a subagent when the area is large, so the answer comes back and the file dumps don't.
3. **Run the claims that matter:** a test, a trace, a log line, a call in a scratch copy. Mark each claim run or read (**prove-it**).
4. **Write for a capable engineer new to the area:** what it does for its users; its main parts and what each owns; how a request, event or call flows through them; where state lives and what changes it; what surprises people, and why. Cite a file and line for each claim, explain terms where they first appear, and show as well as tell (**talk-to-me**): a diagram, the states (**show-the-states**), one example end to end.
5. **For "where should this live",** show where things of that kind already live and which way the dependencies point, then answer.

<!-- Adapts pstack's how skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
