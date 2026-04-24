// math-mcp opencode plugin — intercepts Bash-as-calculator and routes to
// mcp__math-mcp__* tools.
//
// Install (global — applies to every opencode project):
//   cp math-mcp.ts ~/.config/opencode/plugins/math-mcp.ts
// Install (per-project):
//   cp math-mcp.ts .opencode/plugins/math-mcp.ts
//
// Also register math-mcp as a local MCP server in opencode.json — see the
// opencode.json example in this directory.
//
// Detector MUST stay in sync with ../core/detect_math.mjs (the Claude Code
// copy). It is inlined here so users can install with a single file.

const MATCHERS: { kind: string; re: RegExp }[] = [
  { kind: "bash $((...))",          re: /\$\(\(/ },
  { kind: "bc",                     re: /(?:^|[\s|;&()])bc(?:\s|$|<|\|)/ },
  { kind: "dc",                     re: /(?:^|[\s|;&()])dc(?:\s|$|<|\|)/ },
  { kind: "qalc / qalculate",       re: /(?:^|[\s|;&()])(?:qalc|qalculate)\b/ },
  { kind: "python -c <arith>",      re: /\bpython3?\b[^|>\n]*\s-c\s+['"][^'"]*\b(?:print|eval)\s*\([^)]*\d[^)]*(?:\*\*|[+\-*/%])[^)]*\)/ },
  { kind: "node -e <arith>",        re: /\bnode\b[^|>\n]*\s-e\s+['"][^'"]*(?:Math\.|\d[^'"]*(?:\*\*|[+\-*/%]))/ },
  { kind: "perl -e <arith>",        re: /\bperl\b[^|>\n]*\s-e\s+['"][^'"]*\bprint\b[^'"]*\d[^'"]*(?:\*\*|[+\-*/%])/ },
  { kind: "awk 'BEGIN{print ...}'", re: /\bawk\b[^'"]*'\s*BEGIN\s*\{[^}]*print[^}]*\d[^}]*(?:\*\*|[+\-*/%])[^}]*\}/ },
  { kind: "expr",                   re: /(?:^|[\s|;&()])expr\s+['"]?-?\d[^\n|;&]{0,80}['"]?\s+\\?[+\-*/%]/ },
];

function detectBashMath(command: string): { kind: string } | null {
  if (typeof command !== "string" || !command) return null;
  for (const m of MATCHERS) {
    if (m.re.test(command)) return { kind: m.kind };
  }
  return null;
}

export const MathMcpPlugin = async () => {
  return {
    "tool.execute.before": async (input: any, output: any) => {
      if (input?.tool !== "bash") return;
      const cmd: string = output?.args?.command ?? "";
      const hit = detectBashMath(cmd);
      if (!hit) return;
      throw new Error(
        `math-mcp: bash calculator pattern detected (${hit.kind}). ` +
        `Shell calculators silently lose precision on big integers and ` +
        `collapse rationals to floats. Route through a math-mcp tool: ` +
        `mcp__math-mcp__evaluate for arithmetic / ratios / %, ` +
        `mcp__math-mcp__evaluate_batch for multiple expressions, ` +
        `mcp__math-mcp__numeric for high-precision decimal, ` +
        `mcp__math-mcp__mod_pow for modular exponentiation.`
      );
    },
  };
};
