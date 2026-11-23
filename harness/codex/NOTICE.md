# Notices

astack is MIT-licensed; see [LICENSE](./LICENSE).

Some astack files adapt parts of [pstack](https://github.com/cursor/plugins/tree/main/pstack), which is distributed under this license:

```
MIT License

Copyright (c) 2026 Lauren Tan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

The adapted files, and what each adapts from pstack 0.15.36:

| astack file | adapts |
|---|---|
| `skills/lead/SKILL.md` | `skills/poteto-mode/playbooks/orchestrate.md` (supervision: read the branch, not the summary; ask the person only for real decisions) and the Subagents section of `skills/poteto-mode/SKILL.md` (a fresh agent with consolidated scope). |
| `skills/decide-by-data/SKILL.md` | `skills/principle-explain-the-number/SKILL.md` (write the decision before you run) and `skills/benchmark-checklist/SKILL.md` (alternate the arms; a gap inside the noise is no difference). |
| `skills/fair-benchmarks/SKILL.md` | `skills/benchmark-checklist/SKILL.md` (each side tuned as it ships; count errors; alternate and repeat). |
| `skills/decisions-in-plain-words/SKILL.md` | `skills/poteto-mode/SKILL.md` (a fact a run can show is not the person's to answer; label each claim measured, inferred or guessed). |

Each adapted file ends with a one-line notice that points here.
