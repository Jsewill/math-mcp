// Run with: node --test plugin/core/detect_math.test.mjs
//
// Protects the detector's precision/recall contract: if a new pattern is
// added (or an existing one drifts) and these cases fail, CI stops the
// regression before it ships. Keep in sync with plugin/opencode/math-mcp.ts
// (which inlines the same MATCHERS table for a single-file opencode install).

import { test } from "node:test";
import assert from "node:assert/strict";
import { detectBashMath } from "./detect_math.mjs";

test("positives are flagged", () => {
  const positives = [
    "echo $((17 * 23))",
    'echo "$((2**20))"',
    'python -c "print(2**100)"',
    "python3 -c 'print(17*23)'",
    'bc <<< "3+4"',
    'echo "17*23" | bc',
    'node -e "console.log(17*23)"',
    'node -e "console.log(Math.pow(2,100))"',
    'node -e "console.log(Math.PI)"',
    "expr 17 \\* 23",
    "perl -e 'print 2**10'",
    "awk 'BEGIN{print 2*3}'",
    'qalc "1 USD to EUR"',
    'dc -e "17 23 * p"',
  ];
  for (const cmd of positives) {
    const hit = detectBashMath(cmd);
    assert.notEqual(hit, null, `should flag: ${cmd}`);
    assert.ok(typeof hit.kind === "string" && hit.kind.length > 0);
  }
});

test("negatives are not flagged", () => {
  const negatives = [
    "ls",
    "git status",
    "mkdir -p foo/bar",
    "rm -rf /tmp/x",
    `node -e "console.log('hello, world')"`,
    `node -e "process.exit(0)"`,
    `echo "bc is a command-line calculator"`,
    `python -c "import sys; print(sys.version)"`,
    "cd /tmp && ls",
    "cat file.txt | grep foo",
    "curl https://example.com/",
    "npm test",
    "uv run pytest",
  ];
  for (const cmd of negatives) {
    assert.equal(detectBashMath(cmd), null, `should not flag: ${cmd}`);
  }
});

test("non-string / empty input returns null", () => {
  assert.equal(detectBashMath(null), null);
  assert.equal(detectBashMath(undefined), null);
  assert.equal(detectBashMath(""), null);
  assert.equal(detectBashMath(42), null);
  assert.equal(detectBashMath({}), null);
});
