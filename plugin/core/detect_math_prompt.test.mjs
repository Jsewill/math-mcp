// Run with: node --test plugin/core/detect_math_prompt.test.mjs
//
// Locks the detector's precision/recall contract for the
// UserPromptSubmit hook. Positives must flag; negatives (common dev-chat
// language that mentions math-adjacent verbs like "solve" or "factor" in
// a non-math context) must not.

import { test } from "node:test";
import assert from "node:assert/strict";
import { detectMathPrompt } from "./detect_math_prompt.mjs";

test("math prompts are flagged", () => {
  const positives = [
    "what's 17 * 23?",
    "what is 2 + 2",
    "how much is 30% of 240",
    "compute 2^100",
    "calculate (x + 1)**2",
    "evaluate pi to 100 digits",
    "simplify (x**2 - 1)/(x - 1)",
    "factor 360",
    "factor (x^2 - 1)",
    "solve x^2 = 4",
    "solve for x when x + 3 = 10",
    "integrate sin(x) from 0 to pi",
    "differentiate x**2",
    "derivative of sin(x) * cos(x)",
    "integral of 1/(1+x**2)",
    "is 97 prime?",
    "prime factorization of 360",
    "next prime after 100",
    "gcd(462, 1071)",
    "mean of the list",
    "5 meters to feet",
    "convert 30 kg to pounds",
    "binomial coefficient",
    "n choose k where n=10, k=3",
    "hex for 255",
    "in base 16",
    "roots of x^3 - x - 1",
    "eigenvalues of a 3x3 matrix",
    "determinant of [[1,2],[3,4]]",
    "4 * 0.79",
    "10!",
    "2**100",
  ];
  for (const p of positives) {
    const hit = detectMathPrompt(p);
    assert.notEqual(hit, null, `should flag: ${p}`);
    assert.ok(typeof hit.kind === "string" && hit.kind.length > 0);
  }
});

test("non-math dev-chat prompts are not flagged", () => {
  const negatives = [
    "hello",
    "what's your name",
    "how do I solve this merge conflict",
    "solve the flaky test",
    "factor out this duplicated code",
    "simplify the design",
    "read this file",
    "list the dependencies",
    "create a new branch",
    "install the package",
    "run the tests",
    "fix the bug on line 42",
    "refactor this function",
    "write a README",
    "show me the diff",
    "git status please",
    "can you commit these changes",
    "integrate this feature with the auth flow",
    "differentiate between these two approaches",
    "the factor that matters most is readability",
    "evaluate the tradeoffs",
    "compute the big-O complexity",
  ];
  for (const p of negatives) {
    const hit = detectMathPrompt(p);
    assert.equal(hit, null, `should not flag: "${p}" (got kind="${hit?.kind}")`);
  }
});

test("empty / non-string returns null", () => {
  assert.equal(detectMathPrompt(""), null);
  assert.equal(detectMathPrompt(null), null);
  assert.equal(detectMathPrompt(undefined), null);
  assert.equal(detectMathPrompt(42), null);
  assert.equal(detectMathPrompt({}), null);
});
