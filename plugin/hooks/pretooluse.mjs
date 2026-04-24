#!/usr/bin/env node
// math-mcp PreToolUse:Bash hook — flags shell calculator patterns with a nudge
// toward the matching mcp__math-mcp__* tool. Advisory (additionalContext), not
// a hard deny — false positives are ignorable. Emits nothing when the command
// is not recognized as arithmetic.

import { detectBashMath } from "../core/detect_math.mjs";

async function readStdin() {
  let data = "";
  for await (const chunk of process.stdin) data += chunk;
  return data;
}

const raw = await readStdin();
let payload;
try { payload = JSON.parse(raw || "{}"); } catch { process.exit(0); }

const toolName = payload?.tool_name;
const command = payload?.tool_input?.command;

if (toolName !== "Bash" || typeof command !== "string") process.exit(0);

const hit = detectBashMath(command);
if (!hit) process.exit(0);

const tip = `<math_routing>
  <tip>
    This Bash command looks like arithmetic (pattern: ${hit.kind}).
    Shell calculators silently lose precision on big integers and collapse
    rationals to floats. Route through a math-mcp tool instead:
      - arithmetic / ratios / percentages / deltas → mcp__math-mcp__evaluate
      - many expressions at once (table cells)     → mcp__math-mcp__evaluate_batch
      - high-precision decimal (mpmath)            → mcp__math-mcp__numeric
      - modular exponent (a^b mod m)               → mcp__math-mcp__mod_pow
      - modular inverse                            → mcp__math-mcp__mod_inverse
      - primality / factorization                  → mcp__math-mcp__is_prime / factorint
    If this command is NOT arithmetic (e.g. a legitimate \`bc\` unrelated to
    math, or \`node -e\` with non-numeric \`+\`), you may proceed.
  </tip>
</math_routing>`;

process.stdout.write(JSON.stringify({
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    additionalContext: tip,
  },
}));
process.exit(0);
