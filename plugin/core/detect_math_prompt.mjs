// Pure detection: does a user prompt contain mathematical/numeric content
// that should trigger a routing nudge toward mcp__math-mcp__* tools?
// No I/O. Tested in detect_math_prompt.test.mjs.
//
// The regex set is deliberately recall-weighted — a soft false positive
// injects ~500 chars of redundant directive on that turn, which is cheap
// compared to a silent mental-arithmetic miss. Soft verbs (`solve`,
// `factor`, `simplify`, `integrate`) are narrowed to require math-looking
// context so they don't fire on "solve this merge conflict" etc.

const SIGNALS = [
  // Hard signals — unambiguous
  { kind: "digits with operator",    re: /\b\d[\d,.]*\s*[*/+\-×÷%]\s*[\d(]/ },
  { kind: "exponent",                re: /\b\d+\s*(?:\^|\*\*)\s*\d/ },
  { kind: "factorial",               re: /\b\d+!/ },
  { kind: "percent of",              re: /\b\d[\d,.]*\s*(?:percent|%)\s+of\b/i },
  { kind: "primality",               re: /\bis\s+\d[\d,.]*\s+prime\b|\bprime\s+factorization\b|\bn(?:th)?\s+prime\b|\bnext\s+prime\b/i },
  { kind: "combinatorics",           re: /\bbinomial\b|\bn\s+choose\s+k\b|\bk-?combinations?\b|\bpermutations?\s+of\b/i },
  { kind: "unit conversion",         re: /\bconvert\s+\d[\d.]*\s*\w+\s+to\s+\w+|\b\d[\d.]*\s+(?:m(?:eter)?s?|ft|feet|kg|kilograms?|lbs?|pounds?|°?[CF]|kelvin|joules?|calories?)\s+(?:to|in)\s+\w/i },
  { kind: "base conversion",         re: /\bin\s+base\s+\d+\b|\bhex(?:adecimal)?\s+(?:for|of)\s+\d|\bbinary\s+(?:for|of|representation\s+of)\s+\d|\boctal\s+(?:for|of)\s+\d/i },
  { kind: "stats",                   re: /\b(?:mean|median|variance|stdev|standard\s+deviation)\s+of\b/i },
  { kind: "matrix op",               re: /\b(?:eigenvalues?|determinant|matrix\s+(?:inverse|product|multiplication))\b/i },
  { kind: "math function",           re: /\b(?:sqrt|sin|cos|tan|log|ln|exp|gcd|lcm|mod|modulo)\s*\(/i },
  { kind: "high-precision request",  re: /\bto\s+\d+\s+(?:digits?|decimal\s+places?|dp|sig\.?\s*figs?)\b/i },

  // Soft signals — narrowed to require math-looking context
  { kind: "calc verb + math",        re: /\b(?:calculate|compute|evaluate)\s+(?:[\d(]|[a-z]+\s*[\^*+\-])/i },
  { kind: "solve equation",          re: /\bsolve\b[^.]{0,60}(?:[<>]|=|\bfor\s+[a-z]\b)/i },
  { kind: "factor N",                re: /\bfactor(?:ize|ise)?\s+(?:\d|\([^)]*[\^*+\-])/i },
  { kind: "simplify expr",           re: /\bsimplify\s+(?:\(|[a-z0-9]+\s*[\^*+\-])/i },
  { kind: "integrate/differentiate", re: /\b(?:integrate|differentiate)\s+(?:\(|\d|[a-z_]\w*\s*(?:\(|\^|\*\*))|\b(?:derivative|integral)\s+of\b/i },
  { kind: "roots/zeros of",          re: /\b(?:roots?|zeros?)\s+of\s+(?:\d|[a-z_]\w*\s*[\^*+\-(]|\()/i },
  { kind: "question about number",   re: /\b(?:what(?:'s|\s+is)|how\s+much\s+is)\s+[\d(]/i },
];

export function detectMathPrompt(text) {
  if (typeof text !== "string" || !text) return null;
  for (const s of SIGNALS) {
    if (s.re.test(text)) return { kind: s.kind };
  }
  return null;
}
