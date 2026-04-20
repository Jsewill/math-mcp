"""Math MCP server.

Exposes exact, arbitrary-precision, and symbolic math tools backed by SymPy.
Every tool returns deterministic results with explicit parse echoes so the
caller can audit what was computed.
"""

from __future__ import annotations

import json
from typing import Any

import sympy as sp
from mcp.server.fastmcp import FastMCP
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

mcp = FastMCP("math-mcp")

TRANSFORMS = standard_transformations + (implicit_multiplication_application,)

BUILTIN_NAMES: dict[str, Any] = {
    "pi": sp.pi,
    "e": sp.E,
    "E": sp.E,
    "I": sp.I,
    "oo": sp.oo,
    "inf": sp.oo,
    "infinity": sp.oo,
    "nan": sp.nan,
    "gamma": sp.gamma,
    "factorial": sp.factorial,
    "binomial": sp.binomial,
    "log": sp.log,
    "ln": sp.log,
    "exp": sp.exp,
    "sqrt": sp.sqrt,
    "cbrt": sp.cbrt,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "atan2": sp.atan2,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
    "Abs": sp.Abs,
    "abs": sp.Abs,
    "floor": sp.floor,
    "ceiling": sp.ceiling,
    "ceil": sp.ceiling,
    "Min": sp.Min,
    "Max": sp.Max,
    "Rational": sp.Rational,
    "Integer": sp.Integer,
    "Float": sp.Float,
}


def _parse(expr: str, extra_locals: dict[str, Any] | None = None) -> sp.Expr:
    """Parse a string into a SymPy expression safely (no Python eval)."""
    if not isinstance(expr, str) or not expr.strip():
        raise ValueError("expression must be a non-empty string")
    local_dict = dict(BUILTIN_NAMES)
    if extra_locals:
        local_dict.update(extra_locals)
    return parse_expr(
        expr,
        local_dict=local_dict,
        transformations=TRANSFORMS,
        evaluate=True,
    )


def _parse_symbols(names: list[str] | None) -> dict[str, sp.Symbol]:
    if not names:
        return {}
    return {n: sp.Symbol(n) for n in names}


def _to_native(value: Any) -> Any:
    """Convert SymPy objects into JSON-friendly primitives where reasonable."""
    if isinstance(value, (list, tuple)):
        return [_to_native(v) for v in value]
    if isinstance(value, dict):
        return {str(_to_native(k)): _to_native(v) for k, v in value.items()}
    if isinstance(value, sp.Integer):
        return int(value)
    if isinstance(value, sp.Rational):
        return {"numer": int(value.p), "denom": int(value.q), "str": str(value)}
    if isinstance(value, sp.Float):
        return {"float": str(value), "mpf": True}
    if isinstance(value, sp.Basic):
        return str(value)
    return value


def _result(exact: Any, *, decimal: int | None = None, **extra: Any) -> str:
    """Build a standard JSON response.

    `exact` is the primary (symbolic/rational/integer) result.
    `decimal` (int>=1) adds a numeric evaluation with that many significant digits.
    """
    payload: dict[str, Any] = {
        "exact": str(exact) if isinstance(exact, sp.Basic) else _to_native(exact),
    }
    if isinstance(exact, sp.Basic):
        try:
            latex = sp.latex(exact)
            payload["latex"] = latex
        except Exception:
            pass
    if decimal is not None and isinstance(exact, sp.Basic):
        try:
            payload["decimal"] = str(sp.N(exact, decimal))
            payload["decimal_digits"] = decimal
        except Exception as err:
            payload["decimal_error"] = str(err)
    payload.update({k: _to_native(v) for k, v in extra.items()})
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Arithmetic + general evaluation
# ---------------------------------------------------------------------------


@mcp.tool()
def evaluate(expression: str, precision: int = 50) -> str:
    """Evaluate any arithmetic or symbolic expression exactly.

    Supports +, -, *, /, **, parentheses, rationals like 1/3, irrationals (pi, e,
    sqrt(2)), functions (sin, cos, log, exp, gamma, factorial, binomial), and
    arbitrarily large integers. Integer and rational math is always exact; a
    decimal approximation is also returned at the requested precision.

    Args:
        expression: e.g. "2**100 + 1", "sin(pi/6)", "1/3 + 1/7", "log(2, 10)".
        precision: significant decimal digits for the numeric approximation
            (default 50, max 10000).
    """
    precision = max(1, min(int(precision), 10000))
    expr = _parse(expression)
    simplified = sp.nsimplify(expr, rational=False) if expr.is_number else expr
    try:
        exact = sp.simplify(simplified)
    except Exception:
        exact = simplified
    return _result(exact, decimal=precision if exact.is_number else None,
                   parsed=str(expr))


@mcp.tool()
def numeric(expression: str, digits: int = 50) -> str:
    """Evaluate an expression to N significant decimal digits using mpmath.

    Use when you want a concrete decimal value (e.g. pi to 1000 places).

    Args:
        expression: any numeric SymPy expression.
        digits: number of significant digits (default 50, max 100000).
    """
    digits = max(1, min(int(digits), 100_000))
    expr = _parse(expression)
    value = sp.N(expr, digits)
    return _result(value, decimal=digits, parsed=str(expr))


# ---------------------------------------------------------------------------
# Algebra
# ---------------------------------------------------------------------------


@mcp.tool()
def simplify(expression: str, symbols: list[str] | None = None) -> str:
    """Algebraically simplify an expression.

    Args:
        expression: e.g. "(x**2 - 1)/(x - 1)".
        symbols: optional list of variable names appearing in the expression.
    """
    expr = _parse(expression, _parse_symbols(symbols))
    return _result(sp.simplify(expr), parsed=str(expr))


@mcp.tool()
def expand(expression: str, symbols: list[str] | None = None) -> str:
    """Expand products and powers. e.g. "(x+1)**5" -> polynomial form."""
    expr = _parse(expression, _parse_symbols(symbols))
    return _result(sp.expand(expr), parsed=str(expr))


@mcp.tool()
def factor(expression: str, symbols: list[str] | None = None) -> str:
    """Factor a polynomial expression over the rationals."""
    expr = _parse(expression, _parse_symbols(symbols))
    return _result(sp.factor(expr), parsed=str(expr))


@mcp.tool()
def solve_equation(
    equation: str,
    variable: str = "x",
    domain: str = "complex",
) -> str:
    """Solve an equation (or "lhs = rhs") for a variable.

    Args:
        equation: "x**2 - 2 = 0", or just "x**2 - 2" (implied = 0).
        variable: variable to solve for (default "x").
        domain: "complex" (default), "real", "integer", or "rational".
    """
    var = sp.Symbol(variable)
    if "=" in equation:
        lhs_s, rhs_s = equation.split("=", 1)
        lhs = _parse(lhs_s, {variable: var})
        rhs = _parse(rhs_s, {variable: var})
        eq = sp.Eq(lhs, rhs)
    else:
        eq = sp.Eq(_parse(equation, {variable: var}), 0)
    domain_map = {
        "complex": sp.S.Complexes,
        "real": sp.S.Reals,
        "integer": sp.S.Integers,
        "rational": sp.S.Rationals,
    }
    if domain not in domain_map:
        raise ValueError(f"domain must be one of {list(domain_map)}")
    solutions = sp.solveset(eq, var, domain=domain_map[domain])
    try:
        as_list = [str(s) for s in list(solutions)]
    except TypeError:
        as_list = None
    return _result(solutions, parsed=str(eq), solutions=as_list or str(solutions))


@mcp.tool()
def solve_system(equations: list[str], variables: list[str]) -> str:
    """Solve a system of equations.

    Args:
        equations: list like ["x + y = 3", "x - y = 1"].
        variables: list like ["x", "y"].
    """
    syms = _parse_symbols(variables)
    eqs: list[sp.Expr] = []
    for raw in equations:
        if "=" in raw:
            lhs, rhs = raw.split("=", 1)
            eqs.append(sp.Eq(_parse(lhs, syms), _parse(rhs, syms)))
        else:
            eqs.append(sp.Eq(_parse(raw, syms), 0))
    sol = sp.solve(eqs, list(syms.values()), dict=True)
    return _result(sol, equations=[str(e) for e in eqs])


# ---------------------------------------------------------------------------
# Calculus
# ---------------------------------------------------------------------------


@mcp.tool()
def differentiate(
    expression: str,
    variable: str = "x",
    order: int = 1,
    symbols: list[str] | None = None,
) -> str:
    """Take the nth derivative of an expression with respect to a variable."""
    local = _parse_symbols(symbols) | {variable: sp.Symbol(variable)}
    expr = _parse(expression, local)
    result = sp.diff(expr, local[variable], int(order))
    return _result(sp.simplify(result), parsed=str(expr))


@mcp.tool()
def integrate(
    expression: str,
    variable: str = "x",
    lower: str | None = None,
    upper: str | None = None,
    symbols: list[str] | None = None,
) -> str:
    """Symbolically integrate. Omit lower/upper for an indefinite integral."""
    local = _parse_symbols(symbols) | {variable: sp.Symbol(variable)}
    expr = _parse(expression, local)
    var = local[variable]
    if lower is None and upper is None:
        result = sp.integrate(expr, var)
    elif lower is not None and upper is not None:
        lo = _parse(lower, local)
        hi = _parse(upper, local)
        result = sp.integrate(expr, (var, lo, hi))
    else:
        raise ValueError("provide both lower and upper, or neither")
    return _result(
        sp.simplify(result),
        decimal=50 if result.is_number else None,
        parsed=str(expr),
    )


@mcp.tool()
def limit(
    expression: str,
    variable: str = "x",
    point: str = "0",
    direction: str = "+-",
    symbols: list[str] | None = None,
) -> str:
    """Compute a limit. direction may be '+' (right), '-' (left), or '+-' (two-sided)."""
    local = _parse_symbols(symbols) | {variable: sp.Symbol(variable)}
    expr = _parse(expression, local)
    pt = _parse(point, local)
    if direction not in {"+", "-", "+-"}:
        raise ValueError("direction must be '+', '-', or '+-'")
    result = sp.limit(expr, local[variable], pt, direction)
    return _result(result, decimal=50 if result.is_number else None, parsed=str(expr))


@mcp.tool()
def series(
    expression: str,
    variable: str = "x",
    point: str = "0",
    order: int = 6,
    symbols: list[str] | None = None,
) -> str:
    """Taylor/Laurent series expansion around a point."""
    local = _parse_symbols(symbols) | {variable: sp.Symbol(variable)}
    expr = _parse(expression, local)
    pt = _parse(point, local)
    result = sp.series(expr, local[variable], pt, int(order)).removeO()
    return _result(result, parsed=str(expr))


@mcp.tool()
def summation(
    expression: str,
    index: str = "n",
    lower: str = "1",
    upper: str = "oo",
    symbols: list[str] | None = None,
) -> str:
    """Compute a (possibly infinite) summation Σ expression for index from lower..upper."""
    local = _parse_symbols(symbols) | {index: sp.Symbol(index)}
    expr = _parse(expression, local)
    lo = _parse(lower, local)
    hi = _parse(upper, local)
    result = sp.summation(expr, (local[index], lo, hi))
    return _result(sp.simplify(result),
                   decimal=50 if result.is_number else None,
                   parsed=str(expr))


# ---------------------------------------------------------------------------
# Number theory
# ---------------------------------------------------------------------------


@mcp.tool()
def gcd(numbers: list[str]) -> str:
    """Greatest common divisor of two or more integers (arbitrary size)."""
    values = [sp.Integer(_parse(n)) for n in numbers]
    if len(values) < 2:
        raise ValueError("need at least two numbers")
    result = values[0]
    for v in values[1:]:
        result = sp.gcd(result, v)
    return _result(result, inputs=[str(v) for v in values])


@mcp.tool()
def lcm(numbers: list[str]) -> str:
    """Least common multiple of two or more integers."""
    values = [sp.Integer(_parse(n)) for n in numbers]
    if len(values) < 2:
        raise ValueError("need at least two numbers")
    result = values[0]
    for v in values[1:]:
        result = sp.lcm(result, v)
    return _result(result, inputs=[str(v) for v in values])


@mcp.tool()
def factorint(number: str) -> str:
    """Prime factorization of an integer. Returns {prime: exponent}."""
    n = sp.Integer(_parse(number))
    factors = sp.factorint(n)
    pretty = " * ".join(f"{p}^{e}" if e > 1 else str(p) for p, e in factors.items())
    return _result(n, factors={str(p): int(e) for p, e in factors.items()},
                   pretty=pretty)


@mcp.tool()
def is_prime(number: str) -> str:
    """Deterministic primality test for integers of any size."""
    n = sp.Integer(_parse(number))
    return _result(bool(sp.isprime(n)), number=int(n))


@mcp.tool()
def nth_prime(n: int) -> str:
    """Return the nth prime (1-indexed: prime(1)=2)."""
    return _result(int(sp.prime(int(n))), index=int(n))


@mcp.tool()
def next_prime(number: str) -> str:
    """Smallest prime strictly greater than the given integer."""
    n = sp.Integer(_parse(number))
    return _result(int(sp.nextprime(n)), number=int(n))


@mcp.tool()
def mod_pow(base: str, exponent: str, modulus: str) -> str:
    """Modular exponentiation: base**exponent mod modulus (exact, any size)."""
    b = int(_parse(base))
    e = int(_parse(exponent))
    m = int(_parse(modulus))
    if m == 0:
        raise ValueError("modulus must be non-zero")
    return _result(pow(b, e, m), base=b, exponent=e, modulus=m)


@mcp.tool()
def mod_inverse(a: str, modulus: str) -> str:
    """Modular multiplicative inverse of a mod m. Raises if gcd(a,m) != 1."""
    a_i = int(_parse(a))
    m_i = int(_parse(modulus))
    return _result(int(sp.mod_inverse(a_i, m_i)), a=a_i, modulus=m_i)


# ---------------------------------------------------------------------------
# Linear algebra
# ---------------------------------------------------------------------------


def _parse_matrix(data: list[list[str]]) -> sp.Matrix:
    rows = [[_parse(str(cell)) for cell in row] for row in data]
    return sp.Matrix(rows)


@mcp.tool()
def matrix_determinant(matrix: list[list[str]]) -> str:
    """Exact determinant of a square matrix given as nested lists."""
    M = _parse_matrix(matrix)
    return _result(M.det(), rows=M.rows, cols=M.cols)


@mcp.tool()
def matrix_inverse(matrix: list[list[str]]) -> str:
    """Exact inverse of a square matrix. Raises if singular."""
    M = _parse_matrix(matrix)
    inv = M.inv()
    return _result(str(inv), rows=inv.rows, cols=inv.cols,
                   data=[[str(inv[i, j]) for j in range(inv.cols)] for i in range(inv.rows)])


@mcp.tool()
def matrix_multiply(a: list[list[str]], b: list[list[str]]) -> str:
    """Exact matrix product A*B."""
    A = _parse_matrix(a)
    B = _parse_matrix(b)
    C = A * B
    return _result(str(C), rows=C.rows, cols=C.cols,
                   data=[[str(C[i, j]) for j in range(C.cols)] for i in range(C.rows)])


@mcp.tool()
def matrix_eigenvalues(matrix: list[list[str]]) -> str:
    """Exact eigenvalues with algebraic multiplicity."""
    M = _parse_matrix(matrix)
    eigs = M.eigenvals()
    return _result({str(k): int(v) for k, v in eigs.items()})


@mcp.tool()
def matrix_solve(a: list[list[str]], b: list[list[str]]) -> str:
    """Solve the linear system A x = b exactly."""
    A = _parse_matrix(a)
    B = _parse_matrix(b)
    x = A.solve(B)
    return _result(str(x), data=[[str(x[i, j]) for j in range(x.cols)]
                                 for i in range(x.rows)])


# ---------------------------------------------------------------------------
# Statistics (basic, exact over rationals)
# ---------------------------------------------------------------------------


@mcp.tool()
def stats(numbers: list[str]) -> str:
    """Mean, median, variance (sample), stdev, min, max — exact where possible."""
    vals = [_parse(str(n)) for n in numbers]
    if not vals:
        raise ValueError("need at least one number")
    n = len(vals)
    mean = sp.Rational(0)
    for v in vals:
        mean += v
    mean = mean / n
    sorted_vals = sorted(vals, key=lambda v: float(v))
    if n % 2 == 1:
        median = sorted_vals[n // 2]
    else:
        median = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    if n > 1:
        variance = sum((v - mean) ** 2 for v in vals) / (n - 1)
        stdev = sp.sqrt(variance)
    else:
        variance = sp.Rational(0)
        stdev = sp.Rational(0)
    return _result(
        {
            "mean": str(sp.simplify(mean)),
            "median": str(sp.simplify(median)),
            "variance_sample": str(sp.simplify(variance)),
            "stdev_sample": str(sp.simplify(stdev)),
            "min": str(min(sorted_vals, key=lambda v: float(v))),
            "max": str(max(sorted_vals, key=lambda v: float(v))),
            "count": n,
        },
        decimal=30,
    )


# ---------------------------------------------------------------------------
# Units / conversions helpers
# ---------------------------------------------------------------------------


@mcp.tool()
def to_rational(value: str, max_denominator: int = 10**9) -> str:
    """Best rational approximation to a decimal string, bounded by max_denominator."""
    expr = _parse(value)
    num = sp.nsimplify(expr, rational=True,
                       rational_conversion="exact")
    approx = sp.Rational(num).limit_denominator(int(max_denominator))
    return _result(approx, exact_rational=str(num), decimal=50)


def main() -> None:
    """Console entry point — runs the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
