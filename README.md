# math-mcp

An [MCP](https://modelcontextprotocol.io) server that gives LLM agents **exact, arbitrary-precision, and symbolic math**. Backed by [SymPy](https://www.sympy.org/) and [mpmath](https://mpmath.org/), so `1/3 + 1/7` returns `10/21` — not `0.47619047619047616`.

Every response includes the parsed input, the exact (symbolic or rational) result, a LaTeX rendering, and an optional decimal approximation at a requested precision — so callers can audit what was actually computed.

## Features

27 tools across six domains:

| Domain | Tools |
| --- | --- |
| **Arithmetic / numeric** | `evaluate`, `numeric` (up to 100,000 digits) |
| **Algebra** | `simplify`, `expand`, `factor`, `solve_equation`, `solve_system` |
| **Calculus** | `differentiate`, `integrate` (definite & indefinite), `limit`, `series`, `summation` |
| **Number theory** | `gcd`, `lcm`, `factorint`, `is_prime`, `nth_prime`, `next_prime`, `mod_pow`, `mod_inverse` |
| **Linear algebra** | `matrix_determinant`, `matrix_inverse`, `matrix_multiply`, `matrix_eigenvalues`, `matrix_solve` |
| **Other** | `stats`, `to_rational` |

All inputs are parsed through SymPy's safe expression parser — **no `eval`**. Implicit multiplication is supported (`2x` parses as `2*x`).

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
  → 1267650600228229401496703205377

evaluate(expression="1/3 + 1/7 + 1/11")
  → 131/231

numeric(expression="pi", digits=60)
  → 3.14159265358979323846264338327950288419716939937510582097494

solve_equation(equation="x**2 - 2 = 0", domain="real")
  → {-sqrt(2), sqrt(2)}

integrate(expression="1/(1+x**2)", variable="x", lower="0", upper="1")
  → pi/4   (decimal: 0.7853981633974483…)

summation(expression="1/n**2", index="n", lower="1", upper="oo")
  → pi**2/6

is_prime(number="2**521 - 1")
  → true    (Mersenne M_521)

mod_pow(base="7", exponent="2**100", modulus="10**9+7")
  → 641087921
```

## Development

```bash
git clone https://github.com/Jsewill/math-mcp
cd math-mcp
uv sync --all-groups
uv run pytest
```

Run the server directly (stdio transport):

```bash
uv run math-mcp
```

## License

MIT — see [LICENSE](LICENSE).
