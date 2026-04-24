---
description: Re-verify every derived number in the previous assistant turn by calling math-mcp.
---

Review your most recent assistant message. For every number in that message that was DERIVED (produced by `*`, `/`, `%`, ratio, sum, delta, unit scaling, "N× more", "N% of") rather than quoted verbatim from a tool result or user input:

1. Extract the claim and the number.
2. Call `mcp__math-mcp__evaluate` — or `mcp__math-mcp__evaluate_batch` when there are several — to recompute from the original inputs.
3. Compare: does the recomputed value exactly match what you originally wrote?

Report a table with columns: `claim | original | recomputed | match?`. If any row is "no", correct the prior answer inline and explain what went wrong (usually: mental arithmetic, rounding, or stacked multipliers).
