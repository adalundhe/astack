---
name: no-hidden-config
description: "Parse all settings in one place, keep each option single-purpose, document and test every value, and isolate internal switches behind proper feature flags. Use when writing or reviewing options, flags, or env vars."
---

# No hidden config

Parse every setting in one place, make each option do only what its name says, and document and test every accepted value.

## Start with

1. **Centralize config parsing:** load CLI flags, config files, and environment variables once at startup into one typed config struct with defaults and validation (**check-your-boundaries**). Nothing else reads the environment directly.
2. **One job per option, named clearly.** Prefer environment variables for deployment settings (endpoints, secrets, paths) rather than user-facing behavior choices.
3. **Fail fast at startup** on invalid values, unknown keys, or conflicting combinations, with an error stating how to fix it.
4. **Document every user-facing option** where users look: name, behavior, default, allowed values, and an example.
5. **Test every accepted value:** defaults, alternatives, and interaction rules.
6. **Use proper feature flags for internal or experimental paths:** use the project's feature-flag system (or a typed internal config flag), off by default, with an owner and removal condition, kept off the public user surface. Delete the flag and losing path once decided.
7. **Check impact before renaming or removing user settings** (**blast-radius**).

## Watch for

- `os.environ` / `process.env` reads scattered deep in code, missing from docs, or hiding undocumented defaults;
- overloaded options (e.g. a `--debug` flag that disables auth, a `--fast` mode that skips validation, a legacy switch altering multiple behaviors);
- overlapping, conflicting, or mutually dependent options;
- config values or combinations never exercised in tests;
- options missing from `--help`, README, or config docs, or lacking defaults and allowed values;
- experimental or internal code paths toggled via undocumented env vars or hidden flags;
- behavior branching on hostname, username, build path, or wall-clock time.

**The test:** can a user find this setting, predict exactly what it does, and trust every value it accepts?

## When it doesn't fit

- deployment env vars (endpoints, secrets, paths) read centrally and documented;
- standard platform env vars (`PORT`, `TZ`, `NO_COLOR`) read in that same central parser;
- proper internal feature flags as defined above;
- an alternative backed by measurements (**ab-test**), with the trade-off documented.

**Showing it:** pass an undocumented value or untested combination and show the unexpected behavior.

Referenced skills: `check-your-boundaries` (`../check-your-boundaries/SKILL.md`), `blast-radius` (`../blast-radius/SKILL.md`), `ab-test` (`../ab-test/SKILL.md`). Read any cited skill file before acting when its trigger applies.
