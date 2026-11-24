---
description: "In Go mode, refactoring boolean-flag lifecycle code routes to no-implicit-states and replaces scattered booleans with an explicit state machine."
expected_outcome: "Reads no-implicit-states/SKILL.md and refactors UploadController into an explicit state enum/tagged union with centralized transitions and transition tests."
allowed_tools: [Read, Glob, Grep]
---

`/astack:go` Refactor this TypeScript upload controller—users keep hitting stuck UI states after retries and failed uploads. Reply with the updated code and tests.

```ts
export class UploadController {
  isIdle = true;
  isUploading = false;
  isDone = false;
  progress = 0;
  url: string | null = null;
  error: string | null = null;

  start() { this.isIdle = false; this.isUploading = true; this.error = null; }
  tick(pct: number) { this.progress = pct; }
  finish(url: string) { this.isUploading = false; this.isDone = true; this.url = url; }
  fail(err: string) { this.isUploading = false; this.error = err; }
}
```
