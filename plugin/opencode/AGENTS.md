# math-mcp — routing rules

math-mcp provides exact, arbitrary-precision, and symbolic math via SymPy. Any number in your response that is DERIVED from another number — by `*`, `/`, `%`, ratio, sum, delta, unit scaling, "N× more", or "N% of" — must come from a `mcp__math-mcp__*` tool call. Mental arithmetic is a silent failure mode at scale.

## BLOCKED — the math-mcp plugin rejects these

The `tool.execute.before` hook in `~/.config/opencode/plugins/math-mcp.ts` throws on:

- `python -c "print(2**100)"` / `python3 -c "..."` with arithmetic
- `$((...))` bash arithmetic expansion
- `bc`, `dc`, `qalc` / `qalculate`
- `node -e "..."` with numeric arithmetic
- `expr N op N`
- `awk 'BEGIN{print 2*3}'`
- `perl -e "print ..."` with arithmetic

If a call is rejected, do NOT retry with a different shell calculator — call the math-mcp tool below.

## Tool picker

| You want | Tool |
| --- | --- |
| Arithmetic / ratios / % / deltas | `mcp__math-mcp__evaluate` |
| Many expressions at once | `mcp__math-mcp__evaluate_batch` |
| High-precision decimal | `mcp__math-mcp__numeric` |
| Simplify / expand / factor | `simplify` / `expand` / `factor` |
| Solve equation / system / inequality | `solve_equation` / `solve_system` / `solve_inequality` |
| Polynomial roots | `polynomial_roots` / `nroots` |
| Differentiate / integrate / limit / series / sum | `differentiate` / `integrate` / `limit` / `series` / `summation` |
| GCD / LCM / factorint / primality | `gcd` / `lcm` / `factorint` / `is_prime` / `next_prime` / `nth_prime` |
| Modular | `mod_pow` / `mod_inverse` |
| Combinatorics | `binomial` / `permutations` / `combinations` |
| Linear algebra | `matrix_determinant` / `matrix_inverse` / `matrix_multiply` / `matrix_eigenvalues` / `matrix_solve` |
| Summary statistics | `stats` |
| Base / rational / unit conversion | `to_base` / `from_base` / `to_rational` / `convert_units` |

## Self-check before emitting a number

If you typed `~`, `approximately`, `about`, `roughly`, `order of`, `~N×`, or rounded to one significant figure, you hedged because you weren't sure. Stop, call the tool, replace the hedge.

If a number is followed by a unit (`TiB`, `W`, `ms`, `%`, `req/s`) you cannot trace to a specific `exact` / `value` / `decimal` field from a tool result, you are guessing. Compute it.
