#!/usr/bin/env node
// math-mcp SubagentStart hook — every subagent Claude Code spawns gets its
// own context; it does NOT inherit the parent session's UserPromptSubmit
// injections. Without a SubagentStart hook, delegation becomes an
// enforcement hole (Explore/Plan/custom agents can happily do mental
// arithmetic). This hook re-plants a terse routing directive into every
// subagent on launch.
//
// Fires for all agent_types (empty matcher); the directive is kept short
// because subagent context budgets are tighter than the main session.

async function drainStdin() {
  for await (const _ of process.stdin) { /* noop */ }
}
await drainStdin().catch(() => {});

const directive = `<math_mcp_directive>
  <rule>
    Any number in your response that is DERIVED from another number MUST
    come from a mcp__math-mcp__* tool call — not mental arithmetic, not a
    shell calculator, not a rounded estimate. This applies inside
    subagents too; delegation does not exempt you.
  </rule>
  <picker>
    one expression            → mcp__math-mcp__evaluate
    many related expressions  → mcp__math-mcp__evaluate_batch
    high-precision decimal    → mcp__math-mcp__numeric
    modular exponent          → mcp__math-mcp__mod_pow
    symbolic algebra/calculus → simplify / expand / factor / solve_equation
                                / differentiate / integrate / limit / series
    number theory             → gcd / lcm / factorint / is_prime / mod_inverse
  </picker>
  <forbidden>
    Do NOT shell out for arithmetic — the PreToolUse:Bash hook will nudge
    against python -c, bc, dc, qalc, $((...)), node -e, expr, perl -e, awk.
  </forbidden>
</math_mcp_directive>`;

process.stdout.write(JSON.stringify({
  hookSpecificOutput: {
    hookEventName: "SubagentStart",
    additionalContext: directive,
  },
}));
process.exit(0);
