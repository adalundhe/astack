---
description: "Negative control: adding an optional case_insensitive parameter to count_words in ./repo/src/wordcount.py supports Unicode casefolding cleanly without Factory/Strategy/Plugin bloat, extra src files, or test gaming."
expected_outcome: "Adds case_insensitive: bool = False with Unicode casefold() to count_words in src/wordcount.py, adds unit tests, stays within a simple flat module with <= 1 class and zero Factory/Strategy/Plugin/_v2 symbols, and keeps gates intact."
timeout_seconds: 240
---

`/astack:go` Add an optional `case_insensitive: bool = False` parameter to `count_words(text, case_insensitive=False)` in `./repo/src/wordcount.py` that handles Unicode case-insensitive matching (for example `"Straße"` matching `"STRASSE"`, and `"Café"` matching `"CAFÉ"`) when enabled while leaving default behavior unchanged when `False`. Add focused unit tests in `./repo/tests/test_wordcount.py`.
