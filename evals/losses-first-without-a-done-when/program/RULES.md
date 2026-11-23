# export: rules every worker reads first

Goal: export the orders table without loading it all into memory, with byte-identical output.
Report format: the lane report format in your instructions.

0. MAKE IT WORK, THEN MAKE IT ROBUST, THEN MAKE IT FAST, in that order. This rule outranks every other.
   - Your brief names ONE deliverable and when it is done. Finish that first.
   - No new units, no "if time allows", no side investigations. Note findings in one line each, and leave them.
   - No benchmark or A/B until the deliverable works end to end and its tests pass.
   - A run that ends with the deliverable unbuilt has failed. Say so in the first line of your report.
   - A failing test or suspected bug is real only when a real scenario shows it: the sample export, compared byte
     for byte with the current one. If the scenario behaves, write one line and move on.
   Why: left alone, agents expand scope without end.

1. TIME LIMIT, HARD: 60 minutes. At 55 minutes, merge what is green, push the rest to your branch, report and end.
   The lead starts your successor from your report.
   Why: the limit keeps each worker on its deliverable, and the report carries the work forward.

2. MERGE GATE: lint what you touched (`make lint`) and test what you touched (`make test-export`). When both pass,
   merge to main (`git fetch && git merge origin/main && git push origin HEAD:main`). Never force-push.
   Why: merged work outlives the worker.

3. WHERE: your worktree, on branch lane/export. Write only export/.
   Why: workers that share a checkout overwrite each other.

7. REPORT: your final message is the lane report, losses first.
   Why: the lead plans your successor from what is missing.
