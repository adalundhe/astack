---
name: no-hidden-config
description: "Every setting is read in one place, does only what its name says, is documented and tested at every value; internal switches are real feature flags. Use when writing or reviewing any option, flag, setting or environment variable."
---

# No hidden config

Keep every setting in one place, doing only what its name says, documented and tested.

## Start with

1. **Read configuration in one place:** flags, files and environment, parsed at startup into one typed configuration with defaults and allowed values (**check-your-boundaries**), so nothing else needs to read the environment.
2. **Give each option one job, and name it for that job.** Environment variables suit deployment (endpoints, secrets, paths) better than users' choices.
3. **Fail at startup** on an invalid value, an unknown key or a conflicting combination, saying what to fix.
4. **Document every user-facing option** where users look: name, effect, default, allowed values, an example.
5. **Test every accepted value:** the default, each alternative, each combination rule.
6. **Put internal and experimental behaviour behind a proper feature flag:** the project's feature-flag system if it has one, otherwise one typed flag in the configuration; off by default, with an owner and a removal condition, and absent from the user-facing surface. Once its decision is made, remove the flag and the losing path.
7. **Before renaming or removing an option users set,** find who sets it (**blast-radius**).

## Watch for

- environment variables read deep in the code, missing from the docs, or with a default only the code knows;
- options that do more than they say: a debug flag that also disables authentication, a fast mode that skips validation, a legacy switch that changes several behaviours;
- options that overlap, conflict, or only work in combination;
- values or combinations no test sets;
- options missing from `--help`, the README or the config reference, or listed without default and allowed values;
- experimental or internal paths reachable through an environment variable or a hidden option;
- branches on hostname, user name, build path or time.

**The test:** could a user find this setting, know exactly what it does, and trust every value it accepts?

## When it doesn't fit

- deployment variables (endpoints, secrets, paths) read in the one configuration place and documented;
- variables the platform itself defines and documents, such as `PORT`, `TZ` or `NO_COLOR`, read in that same place;
- an internal flag that is a proper feature flag, as above;
- an approach the evidence here favours: when unsure, try both and measure (**ab-test**), and say why you chose it.

**Showing it:** set the undocumented value, or the combination no test covers, and show what changes.
