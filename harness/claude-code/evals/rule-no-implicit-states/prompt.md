---
description: "Refactoring boolean-flag lifecycle code follows no-implicit-states by introducing an explicit state enum/tagged union and centralized transitions."
expected_outcome: "Replaces tangled booleans with an explicit state type (enum or tagged union) and centralized transition handling so impossible combinations cannot be constructed."
allowed_tools: [Read, Glob, Grep]
---

Use `/astack:no-implicit-states` to refactor this TypeScript upload controller so impossible states (such as `isUploading && isDone` or `error != null && progress === 100`) cannot exist:

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

Reply with the refactored code and the key transition tests.
