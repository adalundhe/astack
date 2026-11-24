---
name: comment-cop
description: "Keep only the comments code can't replace, and make the code explain the rest. Use when writing or reviewing code, before handing work to review, or when asked to clean up comments."
---

# Comment cop

Remove comments the code already explains, and keep the few it can't.

## Start with

1. **Make the code say it:** a clear name, a smaller function, a type.
2. **Remove a workaround rather than excusing it** in a comment (**yagni**), or fix what it worked around.
3. **When code surprises, change the code** until it doesn't, rather than explaining it.

## Watch for

- narration of what the next lines do;
- banners, section dividers and commented-out code;
- history ("changed for X", "used to be Y"), which version control already keeps;
- a comment excusing a workaround;
- a comment that contradicts the code: that's a bug, so find out which one is right.

**The test:** could a rename, a smaller function or a type say this instead?

## When it doesn't fit

- license and legal headers;
- the contract of a public API;
- a constraint from outside the code, such as a vendor's bug, a protocol's rule or a platform's quirk, with a link to its source;
- a link to the issue or specification behind a choice the code can't explain;
- a lint suppression that says why the rule is wrong for that line.

<!-- Adapts pstack's comment-sicko agent and no-comments skill (MIT, Copyright (c) 2026 Lauren Tan). See NOTICE.md. -->
