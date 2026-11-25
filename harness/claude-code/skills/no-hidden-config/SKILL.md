---
name: no-hidden-config
description: "Parse all settings in one place, keep each option single-purpose, and test every value. Use when writing or reviewing options, flags, or env vars."
disable-model-invocation: true
---

# No hidden config

Parse every setting in one place, give each option one clear job, and document and test every value.

## Start with

1. **Centralize config parsing:** load CLI flags, files, and env vars once into a validated struct (**check-your-boundaries**). Nothing else reads the environment directly, because scattered reads hide defaults from docs and tests.
2. **One job per option, named clearly**. Use env vars for deployment settings (endpoints, secrets, paths), not user-facing behavior choices.
3. **Fail fast at startup** on invalid values, unknown keys, or conflicting options. State how to fix the error, because late config failures surface mid-request.
4. **Document every user-facing option** where users look: name, behavior, default, allowed values, and an example.
5. **Test every accepted value:** defaults, alternatives, and interaction rules.
6. **Isolate internal switches behind feature flags:** keep them off by default and off the public surface. Give each flag an owner and removal condition, because unowned flags fossilize into permanent hidden config. Delete the flag and losing path once decided.
7. **Check impact before renaming or removing user settings** (**blast-radius**).

## Watch for

- `os.environ` / `process.env` reads scattered deep in code, missing from docs, or hiding undocumented defaults;
- overloaded options (e.g. `--debug` disabling auth, `--fast` skipping validation, or one legacy switch altering multiple behaviors);
- overlapping, conflicting, or mutually dependent options;
- config values or combinations never exercised in tests;
- options missing from `--help`, README, or config docs, or lacking defaults and allowed values;
- experimental or internal code paths toggled via undocumented env vars or hidden flags;
- behavior branching on hostname, username, build path, or wall-clock time.

**The test:** can a user find this setting, predict what it does, and trust every value it accepts?

## When it doesn't fit

- deployment env vars (endpoints, secrets, paths) read centrally and documented;
- standard platform env vars (`PORT`, `TZ`, `NO_COLOR`) read in that same central parser;
- proper internal feature flags as defined above.

**Showing it:** pass an undocumented value or untested combination and show the unexpected behavior.

Referenced skills: `check-your-boundaries` (`${CLAUDE_SKILL_DIR}/../check-your-boundaries/SKILL.md`), `blast-radius` (`${CLAUDE_SKILL_DIR}/../blast-radius/SKILL.md`). Read any cited skill file before acting when its trigger applies.
