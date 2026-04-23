# math-mcp

[![CI](https://github.com/Jsewill/math-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/Jsewill/math-mcp/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](#)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An [MCP](https://modelcontextprotocol.io) server that gives LLM agents **exact, arbitrary-precision, and symbolic math**. Backed by [SymPy](https://www.sympy.org/) and [mpmath](https://mpmath.org/), so `1/3 + 1/7` returns `10/21` — not `0.47619047619047616`.

Every tool returns a typed [Pydantic](https://docs.pydantic.dev) model, so MCP clients see structured output with a generated JSON schema — no re-parsing. Docstrings lead with **USE THIS WHEN …** to steer LLM tool routing.

## Features

37 tools across seven domains:

| Domain | Tools |
| --- | --- |
| **Arithmetic / numeric** | `evaluate`, `evaluate_batch`, `numeric` (up to 10,000 digits) |
| **Algebra** | `simplify`, `expand`, `factor`, `solve_equation`, `solve_inequality`, `solve_system`, `polynomial_roots`, `nroots` |
| **Calculus** | `differentiate`, `integrate` (definite & indefinite), `limit`, `series`, `summation` |
| **Number theory** | `gcd`, `lcm`, `factorint`, `is_prime`, `nth_prime`, `next_prime`, `mod_pow`, `mod_inverse` |
| **Combinatorics** | `binomial`, `permutations`, `combinations` |
| **Linear algebra** | `matrix_determinant`, `matrix_inverse`, `matrix_multiply`, `matrix_eigenvalues`, `matrix_solve` |
| **Conversions / stats** | `stats`, `to_rational`, `to_base`, `from_base`, `convert_units` |

### Safety

- **No `eval`.** All inputs are parsed through SymPy's AST-based expression parser. Implicit multiplication is supported (`2x` parses as `2*x`).
- **Input caps** (see `src/math_mcp/limits.py`) reject pathological inputs before they reach SymPy: max 4096-char expressions, max 4096-bit integers, max 32×32 matrices, max 10,000 numeric digits, max 50-order series, max 20-order derivatives.
- **Typed error messages** identify which limit was exceeded so callers can adjust.

## Install

### With `uv` / `uvx` (recommended)

```bash
uvx math-mcp
```

or from a local checkout:

```bash
uv tool install .
math-mcp
```

### With `pip`

```bash
pip install math-mcp
math-mcp
```

## Register with Claude Code

```bash
claude mcp add math-mcp --scope user -- uvx math-mcp
```

Or add to `~/.claude.json` manually:

```json
{
  "mcpServers": {
    "math-mcp": {
      "command": "uvx",
      "args": ["math-mcp"]
    }
  }
}
```

## Register with Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "math-mcp": {
      "command": "uvx",
      "args": ["math-mcp"]
    }
  }
}
```

## Example tool calls

```
evaluate(expression="2**100 + 1")
  → exact: "1267650600228229401496703205377"

evaluate(expression="1/3 + 1/7 + 1/11")
  → exact: "131/231"

numeric(expression="pi", digits=60)
  → exact: "3.14159265358979323846264338327950288419716939937510582097494"

solve_equation(equation="x**2 - 2 = 0", domain="real")
  → solutions: ["-sqrt(2)", "sqrt(2)"]

solve_inequality(inequality="x**2 - 4 > 0", variable="x")
  → solution_set: "Union(Interval.open(-oo, -2), Interval.open(2, oo))"

polynomial_roots(polynomial="(x - 1)**2 * (x - 2)")
  → multiplicities: {"1": 2, "2": 1}

integrate(expression="1/(1+x**2)", variable="x", lower="0", upper="1")
  → exact: "pi/4"   (decimal: 0.7853981633974483…)

summation(expression="1/n**2", index="n", lower="1", upper="oo")
  → exact: "pi**2/6"

is_prime(number="2**521 - 1")
  → value: true    (Mersenne M_521)

mod_pow(base="7", exponent="2**100", modulus="10**9+7")
  → value: 641087921

binomial(n=52, k=5)
  → value: 2598960    (poker hands)

to_base(number="255", base=16)
  → digits: "ff"

convert_units(value="5", source_unit="meter", target_unit="foot")
  → converted: "6250/381 foot"   (decimal: 16.4041994750656)
```

## Development

```bash
git clone https://github.com/Jsewill/math-mcp
cd math-mcp
uv sync --all-groups
uv run coverage run -m pytest
uv run coverage report
```

Coverage is enforced at 100% (`fail_under = 100` in `pyproject.toml`); any regression breaks the test run.

Run the server directly (stdio transport):

```bash
uv run math-mcp
```

## License

MIT — see [LICENSE](LICENSE).
