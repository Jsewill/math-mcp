#!/usr/bin/env node
// math-mcp UserPromptSubmit hook — fires before every assistant response.
// When the user's prompt contains math signals, injects a pre-response
// directive that any derived number MUST route through mcp__math-mcp__*.
// Silent (exit 0 with no output) on non-math prompts, so non-math turns
// pay zero additional context cost.

import { detectMathPrompt } from "../core/detect_math_prompt.mjs";

async function readStdin() {
  let data = "";
  for await (const chunk of process.stdin) data += chunk;
  return data;
}

const raw = await readStdin();
let payload;
try { payload = JSON.parse(raw || "{}"); } catch { process.exit(0); }

const prompt = payload?.prompt ?? payload?.user_prompt ?? "";
if (typeof prompt !== "string" || !prompt) process.exit(0);

const hit = detectMathPrompt(prompt);
if (!hit) process.exit(0);

const directive = `<math_mcp_directive>
  <trigger>prompt contains: ${hit.kind}</trigger>
  <pressure>
    Any number in your response that is DERIVED from another number MUST
    come from a mcp__math-mcp__* tool call — not mental arithmetic, not a
    shell calculator, not a rounded estimate. Mental arithmetic fails
    silently at scale; your confidence is not evidence of correctness.
    If you catch yourself about to emit a number without a prior tool
    call for it, stop and call the tool first.
  </pressure>
  <picker>
    one expression            → mcp__math-mcp__evaluate
    many related expressions  → mcp__math-mcp__evaluate_batch
    high-precision decimal    → mcp__math-mcp__numeric
    modular exponentiation    → mcp__math-mcp__mod_pow
    see routing_cheat_sheet (server instructions) for the full picker.
  </picker>
</math_mcp_directive>`;

process.stdout.write(JSON.stringify({
  hookSpecificOutput: {
    hookEventName: "UserPromptSubmit",
    additionalContext: directive,
  },
}));
process.exit(0);
