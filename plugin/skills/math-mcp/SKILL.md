---
name: math-mcp
description: Route numeric computation to mcp__math-mcp__* tools — arithmetic, ratios, percentages, solve/simplify/factor, calculus, number theory, linear algebra, unit/base conversion, stats. Use whenever the user says "calculate", "compute", "what's X * Y", "factor N", "solve", "integrate", "differentiate", "gcd", "lcm", "mod", "roots", "eigenvalues", "convert units", "mean/variance", or you'd otherwise produce a derived number by mental arithmetic.
---

# math-mcp routing

math-mcp provides exact arithmetic, arbitrary-precision numerics, and symbolic math via SymPy. Any number in your response that is DERIVED from another number must come from a `mcp__math-mcp__*` tool call. "Derived" = produced by `*`, `/`, `%`, ratios, deltas, sums, unit scaling, "N× more", "N% of" on at least one other number.

## Tool picker

| You want | Tool |
| --- | --- |
| Exact arithmetic / ratio / % / delta | `mcp__math-mcp__evaluate` |
| Many related expressions at once (rows, cells) | `mcp__math-mcp__evaluate_batch` |
| High-precision decimal (mpmath) | `mcp__math-mcp__numeric` |
| Simplify / expand / factor an expression | `simplify` / `expand` / `factor` |
| Solve equation / inequality / system | `solve_equation` / `solve_inequality` / `solve_system` |
| Polynomial roots (exact or numeric) | `polynomial_roots` / `nroots` |
| Derivative / integral / limit / series / sum | `differentiate` / `integrate` / `limit` / `series` / `summation` |
| GCD / LCM / prime factorization / primality | `gcd` / `lcm` / `factorint` / `is_prime` / `nth_prime` / `next_prime` |
| Modular: `a^b mod m`, modular inverse | `mod_pow` / `mod_inverse` |
| Combinatorics | `binomial` / `permutations` / `combinations` |
| Linear algebra | `matrix_determinant` / `matrix_inverse` / `matrix_multiply` / `matrix_eigenvalues` / `matrix_solve` |
| Summary statistics | `stats` |
| Base conversion / rationalize / unit conversion | `to_base` / `from_base` / `to_rational` / `convert_units` |

## Do not

- Do not do mental arithmetic, even "simple" ratios, percentages, or single-step unit conversions.
- Do not shell out for math. The PreToolUse:Bash hook blocks these patterns: `python -c`, `python3 -c`, `bc`, `dc`, `qalc`, `$((...))`, `node -e`, `expr N op N`, `perl -e`, `awk 'BEGIN{print ...}'`. If your call is nudged, do not retry in a different shell — use the tool.
- Do not paraphrase, round, or reformat returned numeric fields. Quote `exact` / `value` / `decimal` verbatim.
- Do not collapse exact rationals into floats — fractions must stay exact.

## Self-check before emitting a number

If you typed `~`, `approximately`, `about`, `roughly`, `order of`, `~N×`, or rounded to one significant figure, you hedged because you weren't sure. Stop, call the matching tool, replace the hedge with the computed value.

If a number is followed by a unit (`TiB`, `W`, `ms`, `%`, `req/s`) that you cannot trace to a specific `exact` / `value` / `decimal` field from a tool result, you are guessing. Compute it.
