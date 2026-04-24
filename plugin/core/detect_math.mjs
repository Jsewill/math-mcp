// Pure detection: does a bash command look like a shell calculator? No I/O.
// Shared by plugin/hooks/pretooluse.mjs. Kept in sync with plugin/opencode/math-mcp.ts
// (that file inlines a copy so opencode users can install with one file).

const MATCHERS = [
  { kind: "bash $((...))",            re: /\$\(\(/ },
  { kind: "bc",                       re: /(?:^|[\s|;&()])bc(?:\s|$|<|\|)/ },
  { kind: "dc",                       re: /(?:^|[\s|;&()])dc(?:\s|$|<|\|)/ },
  { kind: "qalc / qalculate",         re: /(?:^|[\s|;&()])(?:qalc|qalculate)\b/ },
  { kind: "python -c <arith>",        re: /\bpython3?\b[^|>\n]*\s-c\s+['"][^'"]*\b(?:print|eval)\s*\([^)]*\d[^)]*(?:\*\*|[+\-*/%])[^)]*\)/ },
  { kind: "node -e <arith>",          re: /\bnode\b[^|>\n]*\s-e\s+['"][^'"]*(?:Math\.|\d[^'"]*(?:\*\*|[+\-*/%]))/ },
  { kind: "perl -e <arith>",          re: /\bperl\b[^|>\n]*\s-e\s+['"][^'"]*\bprint\b[^'"]*\d[^'"]*(?:\*\*|[+\-*/%])/ },
  { kind: "awk 'BEGIN{print ...}'",   re: /\bawk\b[^'"]*'\s*BEGIN\s*\{[^}]*print[^}]*\d[^}]*(?:\*\*|[+\-*/%])[^}]*\}/ },
  { kind: "expr",                     re: /(?:^|[\s|;&()])expr\s+['"]?-?\d[^\n|;&]{0,80}['"]?\s+\\?[+\-*/%]/ },
];

export function detectBashMath(command) {
  if (typeof command !== "string" || !command) return null;
  for (const m of MATCHERS) {
    if (m.re.test(command)) return { kind: m.kind };
  }
  return null;
}
