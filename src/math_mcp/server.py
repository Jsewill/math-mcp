"""math-mcp — exact, arbitrary-precision, and symbolic math over MCP.

Every tool returns a typed Pydantic model (see `models.py`) so MCP clients
see structured output with a generated JSON schema. Input sizes are capped
(see `limits.py`) to stop pathological-input DoS.

Docstrings begin with `USE THIS WHEN …` to help LLM tool routers pick the
right tool — phrase every client-facing rule in the imperative.
"""

from __future__ import annotations

from typing import Any

import sympy as sp
from mcp.server.fastmcp import FastMCP
from sympy.parsing.sympy_parser import (
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

from . import limits
from .models import (
    BaseConversionResult,
    BatchItem,
    BatchResult,
    BooleanResult,
    CombinatoricResult,
    Eigenvalues,
    ExactResult,
    Factorization,
    IntegerResult,
    IntervalResult,
    MatrixResult,
    NumericRoots,
    RationalResult,
    Roots,
    SolutionSet,
    Stats,
    SystemSolution,
    UnitConversion,
)

_ROUTING_INSTRUCTIONS = """\
<priority_instructions>
math-mcp provides exact arithmetic, arbitrary-precision numerics, and
symbolic algebra / calculus / number-theory / linear-algebra via SymPy.
You MUST route calculations through these tools. Mental arithmetic is a
silent failure mode: it produces wrong answers at surprising sizes with
no accompanying signal of doubt, so your confidence is not evidence of
correctness and cannot be used as a routing signal. Invisible failure
modes demand MORE reflexive tool use, not less — you cannot self-correct
what you cannot detect. Skipping a tool is the exception that requires
justification, not the default.
</priority_instructions>

<routing_rule>
If a number in your response is DERIVED from another number, call a tool
to compute it. There is no "mental math" exception for multiplication,
division, ratios, or percentages — even simple ones. There is no "it's
only one digit of precision" exception. The friction of one extra call
is cheaper than one wrong number.

"Derived" means: produced by any operation (`*`, `/`, `%`, `×`, ratios,
deltas, sums across rows, unit scaling, "N× more", "N% of") on at least
one other number. If you can draw an arrow from an input number to the
number you are about to write, it is derived and must come from a tool.

"I'm pretty sure it's N" is not a reason to skip — that is exactly the
state in which mental arithmetic fails silently. Hedging words (`~`,
`approximately`, `about`, `roughly`, `order of`, `~N×`, rounding to one
significant figure) are what you type when you are unsure — stop and
call a tool instead of emitting the hedge.
</routing_rule>

<never>
- Do NOT shell out for math — `python -c`, `bc`, `dc`, `qalc`, `$((...))`,
  `node -e`, `expr`, `perl -e`, `awk 'BEGIN{print ...}'` all silently lose
  precision on big integers and collapse rationals to floats.
- Do NOT paraphrase, round, or reformat returned numeric fields — quote
  `exact` / `value` / `decimal` verbatim.
- Do NOT use `evaluate` for modular exponentiation; use `mod_pow` — it is
  overflow-safe and direction-aware where `evaluate(X**Y % Z)` is not at
  cryptographic scales.
- Do NOT collapse exact rationals into floats — fractions must stay exact.
</never>

<routing_cheat_sheet>
Common user phrasings -> tool:
  "what is X * Y", "X + Y", "X^Y", any calc            -> evaluate
  "table of X/Y, A*B, ..." (many related exprs)        -> evaluate_batch
  "X^Y mod Z", modular exponentiation (NOT evaluate)   -> mod_pow
  "inverse of X mod M", "solve a*x = 1 mod m"          -> mod_inverse
  "n choose k", "ways to pick k from n"                -> binomial
   "combinations of k from n"                           -> combinations
  "P(n, k)", "arrangements of k from n"                -> permutations
  "n!", "factorial(n)"                                 -> evaluate
  "pi / e / sqrt(2) to N digits"                       -> numeric
  "is N prime?"                                        -> is_prime
  "factor N", "prime factorization of N"               -> factorint
  "nth prime", "next prime after N"                    -> nth_prime, next_prime
  "gcd / lcm of ..."                                   -> gcd, lcm
  "derivative of f", "d/dx ..."                        -> differentiate
  "integral of f dx", "area under f"                   -> integrate
  "solve f(x) = 0"                                     -> solve_equation
  "roots of polynomial", "zeros with multiplicity"     -> polynomial_roots
  "numeric roots when symbolic fails"                  -> nroots
  "solve X > 0", "where is f(x) positive"              -> solve_inequality
  "system of equations"                                -> solve_system
  "sum from k=a to b of ..."                           -> summation
  "limit as x -> a"                                    -> limit
  "Taylor / series expansion at ..."                   -> series
  "simplify / expand / factor polynomial"              -> simplify, expand, factor
  "det(M) / inv(M) / eigenvalues(M)", "A x = b"        -> matrix_*
  "X m to ft", "kg to lb", "joule to calorie"          -> convert_units
  "N in base B", "hex for N"                           -> to_base
  "parse 0xABC / 0b1010 as int"                        -> from_base
  "mean / median / variance / stdev of [...]"          -> stats
  "0.333 as a fraction", "decimal to rational"         -> to_rational
</routing_cheat_sheet>
"""

mcp = FastMCP("math-mcp", instructions=_ROUTING_INSTRUCTIONS)

_TRANSFORMS = standard_transformations + (implicit_multiplication_application,)

_BUILTIN_NAMES: dict[str, Any] = {
    "pi": sp.pi, "e": sp.E, "E": sp.E, "I": sp.I,
    "oo": sp.oo, "inf": sp.oo, "infinity": sp.oo, "nan": sp.nan,
    "gamma": sp.gamma, "factorial": sp.factorial, "binomial": sp.binomial,
    "log": sp.log, "ln": sp.log, "exp": sp.exp,
    "sqrt": sp.sqrt, "cbrt": sp.cbrt,
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan, "atan2": sp.atan2,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "Abs": sp.Abs, "abs": sp.Abs,
    "floor": sp.floor, "ceiling": sp.ceiling, "ceil": sp.ceiling,
    "Min": sp.Min, "Max": sp.Max,
    "Rational": sp.Rational, "Integer": sp.Integer, "Float": sp.Float,
}


# ---------------------------------------------------------------------------
# Parse / render helpers
# ---------------------------------------------------------------------------


def _parse(expr: str, extras: dict[str, Any] | None = None) -> sp.Expr:
    if not isinstance(expr, str) or not expr.strip():
        raise ValueError("expression must be a non-empty string")
    limits.validate_expr_len(expr)
    local = dict(_BUILTIN_NAMES)
    if extras:
        local.update(extras)
    return parse_expr(expr, local_dict=local, transformations=_TRANSFORMS, evaluate=True)


def _symbols(names: list[str] | None) -> dict[str, sp.Symbol]:
    if not names:
        return {}
    return {n: sp.Symbol(n) for n in names}


def _latex(x: sp.Basic) -> str | None:
    try:
        return sp.latex(x)
    except Exception:
        return None


def _decimal(x: sp.Basic, digits: int) -> tuple[str | None, str | None]:
    try:
        return str(sp.N(x, digits)), None
    except Exception as e:
        return None, str(e)


def _as_integer(expr: sp.Expr, *, label: str) -> int:
    """Coerce a SymPy expression to a Python int, enforcing the bit cap."""
    if not expr.is_integer:
        raise ValueError(f"{label} must reduce to an integer (got {expr})")
    n = int(expr)
    limits.validate_integer_bits(n, label=label)
    return n


def _scalar_result(expr: sp.Basic, *, digits: int | None = None,
                   parsed: str | None = None) -> ExactResult:
    """Build an ExactResult, attaching a decimal iff the value is numeric."""
    decimal, decimal_error = (None, None)
    want_digits: int | None = None
    if digits is not None and expr.is_number:
        want_digits = limits.clamp_digits(digits)
        decimal, decimal_error = _decimal(expr, want_digits)
    return ExactResult(
        exact=str(expr),
        latex=_latex(expr),
        decimal=decimal,
        decimal_digits=want_digits,
        decimal_error=decimal_error,
        parsed=parsed,
    )


def _parse_matrix(data: list[list[str | int | float]]) -> sp.Matrix:
    if not data:
        raise ValueError("matrix must be non-empty")
    rows = len(data)
    cols = len(data[0]) if data[0] else 0
    limits.validate_matrix_dims(rows, cols)
    for r in data:
        if len(r) != cols:
            raise ValueError("matrix rows must have uniform length")
    return sp.Matrix([[_parse(str(c)) for c in row] for row in data])


def _matrix_strings(M: sp.Matrix) -> list[list[str]]:
    return [[str(M[i, j]) for j in range(M.cols)] for i in range(M.rows)]


def _matrix_result(M: sp.Matrix) -> MatrixResult:
    return MatrixResult(
        rows=M.rows, cols=M.cols,
        data=_matrix_strings(M),
        latex=_latex(M),
    )


# ===========================================================================
# Arithmetic / numeric
# ===========================================================================


def _evaluate_one(expression: str, *, digits: int) -> ExactResult:
    """Shared core for `evaluate` and `evaluate_batch` — parse, simplify,
    and package an ExactResult. Raises on parse/validation failure."""
    expr = _parse(expression)
    simplified = sp.nsimplify(expr, rational=False) if expr.is_number else expr
    try:
        exact = sp.simplify(simplified)
    except Exception:
        exact = simplified
    return _scalar_result(exact, digits=digits, parsed=str(expr))


@mcp.tool()
def evaluate(expression: str, precision: int = 50) -> ExactResult:
    """USE THIS WHEN the user asks you to compute, add, multiply, divide, or
    simplify a numeric or symbolic expression — especially with large integers,
    rationals, or irrationals. Returns an exact result (no float drift) plus
    an arbitrary-precision decimal approximation.

    Supports +, -, *, /, **, parentheses, implicit multiplication (`2x` means
    `2*x`), arbitrary-size integers, rationals, functions (sin/cos/tan/log/
    exp/sqrt/cbrt/gamma/factorial/binomial), constants (pi, e, I, oo).

    For a list of related expressions (e.g. every derived cell of a
    comparison table), prefer `evaluate_batch` — one call, N answers.

    Args:
        expression: e.g. "2**100 + 1", "sin(pi/6)", "1/3 + 1/7", "log(2, 10)".
        precision: significant decimal digits for the approximation
            (clamped to [1, 10000]).
    """
    return _evaluate_one(expression, digits=limits.clamp_digits(precision))


@mcp.tool()
def evaluate_batch(
    expressions: list[str], precision: int = 50
) -> BatchResult:
    """USE THIS WHEN you need to compute MANY related values at once — every
    derived cell of a comparison table, a row of ratios/percentages, or a
    list of "X vs Y" deltas. One call replaces N round-trips, which removes
    the friction excuse for skipping the tool on tabular or multi-row work.

    Each expression is evaluated independently with `evaluate` semantics
    (exact symbolic simplification plus a decimal approximation when the
    result is numeric). A bad expression in one slot does NOT abort the
    batch; that slot's `error` field is populated and the other results
    still return — read `items[i].error` before reading `items[i].exact`.

    Args:
        expressions: list of strings like ["2**100 + 1", "1/3 + 1/7",
            "pi * 2"]. Ordering is preserved in `items`.
        precision: significant decimal digits for each approximation
            (clamped to [1, 10000]); applied uniformly to every item.
    """
    limits.validate_batch_size(len(expressions))
    digits = limits.clamp_digits(precision)
    items: list[BatchItem] = []
    for raw in expressions:
        if not isinstance(raw, str):
            items.append(BatchItem(
                expression=str(raw),
                error="expression must be a string",
            ))
            continue
        try:
            scalar = _evaluate_one(raw, digits=digits)
            items.append(BatchItem(
                expression=raw,
                exact=scalar.exact,
                latex=scalar.latex,
                decimal=scalar.decimal,
                decimal_digits=scalar.decimal_digits,
                decimal_error=scalar.decimal_error,
                parsed=scalar.parsed,
            ))
        except Exception as e:
            items.append(BatchItem(expression=raw, error=str(e)))
    return BatchResult(count=len(items), items=items)


@mcp.tool()
def numeric(expression: str, digits: int = 50) -> ExactResult:
    """USE THIS WHEN the user wants a specific decimal value — e.g. "pi to
    1000 places" — rather than the exact symbolic form. Backed by mpmath
    for arbitrary precision.

    Args:
        expression: any numeric SymPy expression (e.g. "pi", "sqrt(2)").
        digits: significant digits (clamped to [1, 10000]).
    """
    digits = limits.clamp_digits(digits)
    expr = _parse(expression)
    value = sp.N(expr, digits)
    return ExactResult(
        exact=str(value),
        latex=_latex(value),
        decimal=str(value),
        decimal_digits=digits,
        parsed=str(expr),
    )


# ===========================================================================
# Algebra
# ===========================================================================


@mcp.tool()
def simplify(expression: str, symbols: list[str] | None = None) -> ExactResult:
    """USE THIS WHEN the user asks to simplify, reduce, or clean up an
    algebraic expression.

    Args:
        expression: e.g. "(x**2 - 1)/(x - 1)".
        symbols: optional list of variable names appearing in the expression.
    """
    expr = _parse(expression, _symbols(symbols))
    return _scalar_result(sp.simplify(expr), parsed=str(expr))


@mcp.tool()
def expand(expression: str, symbols: list[str] | None = None) -> ExactResult:
    """USE THIS WHEN the user asks to expand, multiply out, or distribute
    products and powers (e.g. "(x+1)**5")."""
    expr = _parse(expression, _symbols(symbols))
    return _scalar_result(sp.expand(expr), parsed=str(expr))


@mcp.tool()
def factor(expression: str, symbols: list[str] | None = None) -> ExactResult:
    """USE THIS WHEN the user asks to factor a polynomial expression over
    the rationals."""
    expr = _parse(expression, _symbols(symbols))
    return _scalar_result(sp.factor(expr), parsed=str(expr))


@mcp.tool()
def solve_equation(
    equation: str,
    variable: str = "x",
    domain: str = "complex",
) -> SolutionSet:
    """USE THIS WHEN the user asks to solve an equation for a variable
    (including "find x such that …").

    Args:
        equation: "x**2 - 2 = 0", or just "x**2 - 2" (implied = 0).
        variable: variable to solve for (default "x").
        domain: "complex" (default), "real", "integer", or "rational".
    """
    var = sp.Symbol(variable)
    if "==" in equation:
        equation = equation.replace("==", "=")
    if "=" in equation:
        lhs_s, rhs_s = equation.split("=", 1)
        eq = sp.Eq(_parse(lhs_s, {variable: var}), _parse(rhs_s, {variable: var}))
    else:
        eq = sp.Eq(_parse(equation, {variable: var}), 0)
    domain_map = {
        "complex": sp.S.Complexes,
        "real": sp.S.Reals,
        "integer": sp.S.Integers,
        "rational": sp.S.Rationals,
    }
    if domain not in domain_map:
        raise ValueError(f"domain must be one of {sorted(domain_map)}")
    solutions = sp.solveset(eq, var, domain=domain_map[domain])
    try:
        listed: list[str] | None = [str(s) for s in list(solutions)]
    except TypeError:
        listed = None
    return SolutionSet(
        equation=str(eq),
        domain=domain,
        solutions=listed,
        set_repr=str(solutions),
        latex=_latex(solutions),
    )


@mcp.tool()
def solve_inequality(
    inequality: str,
    variable: str = "x",
) -> IntervalResult:
    """USE THIS WHEN the user asks for the values of x satisfying an
    inequality like "x**2 - 4 > 0" or "sin(x) >= 1/2". Returns the solution
    set as an Interval / Union of intervals.

    Args:
        inequality: expression using >, <, >=, <= (e.g. "x**2 - 4 > 0").
        variable: variable to solve for (default "x").
    """
    import re

    var = sp.Symbol(variable)
    normalized = inequality.replace("> =", ">=").replace("< =", "<=")
    match = re.search(r"\s*(>=|<=|>|<)\s*", normalized)
    if match is None:
        raise ValueError(
            "inequality must contain one of: >, <, >=, <="
        )
    op_str = match.group(1)
    lhs_s = normalized[: match.start()].strip()
    rhs_s = normalized[match.end():].strip()
    op_cls_map = {
        ">=": sp.GreaterThan,
        "<=": sp.LessThan,
        ">": sp.StrictGreaterThan,
        "<": sp.StrictLessThan,
    }
    if not lhs_s:
        raise ValueError("left-hand side of inequality is empty")
    if not rhs_s:
        raise ValueError("right-hand side of inequality is empty")
    rel = op_cls_map[op_str](
        _parse(lhs_s, {variable: var}),
        _parse(rhs_s, {variable: var}),
    )
    solution = sp.solveset(rel, var, domain=sp.S.Reals)
    return IntervalResult(
        inequality=str(rel),
        variable=variable,
        solution_set=str(solution),
        latex=_latex(solution),
    )


@mcp.tool()
def solve_system(equations: list[str], variables: list[str]) -> SystemSolution:
    """USE THIS WHEN the user asks to solve a system of equations for
    multiple variables simultaneously.

    Args:
        equations: list like ["x + y = 3", "x - y = 1"].
        variables: list like ["x", "y"].
    """
    syms = _symbols(variables)
    eqs: list[sp.Expr] = []
    for raw in equations:
        if "=" in raw:
            lhs, rhs = raw.split("=", 1)
            eqs.append(sp.Eq(_parse(lhs, syms), _parse(rhs, syms)))
        else:
            eqs.append(sp.Eq(_parse(raw, syms), 0))
    sols = sp.solve(eqs, list(syms.values()), dict=True)
    rendered = [{str(k): str(v) for k, v in s.items()} for s in sols]
    return SystemSolution(
        equations=[str(e) for e in eqs],
        solutions=rendered,
    )


@mcp.tool()
def polynomial_roots(polynomial: str, variable: str = "x") -> Roots:
    """USE THIS WHEN the user asks for the roots (with multiplicities) of a
    polynomial. Prefer this over solve_equation when the user says "roots"
    or "zeros" or wants repeated roots called out."""
    var = sp.Symbol(variable)
    expr = _parse(polynomial, {variable: var})
    try:
        poly = sp.Poly(expr, var)
    except sp.PolynomialError as e:
        raise ValueError(f"not a polynomial: {e}")
    roots = sp.roots(poly)  # {root: multiplicity}
    if not roots and poly.degree() > 0:
        numeric = poly.nroots()
        return Roots(
            polynomial=str(poly.as_expr()),
            variable=variable,
            roots=[str(r) for r in numeric],
            multiplicities={str(r): 1 for r in numeric},
        )
    return Roots(
        polynomial=str(poly.as_expr()),
        variable=variable,
        roots=[str(r) for r in roots],
        multiplicities={str(r): int(m) for r, m in roots.items()},
    )


@mcp.tool()
def nroots(polynomial: str, variable: str = "x",
           digits: int = 15) -> NumericRoots:
    """USE THIS WHEN solve_equation returns a ConditionSet (SymPy can't solve
    symbolically) and the user just needs numerical roots. Returns all
    complex roots at the requested precision. Parameter name matches the
    sibling `polynomial_roots` tool."""
    digits = limits.clamp_digits(digits)
    var = sp.Symbol(variable)
    expr = _parse(polynomial, {variable: var})
    try:
        poly = sp.Poly(expr, var)
    except sp.PolynomialError as e:
        raise ValueError(f"not a polynomial: {e}")
    numeric_roots = poly.nroots(n=digits)
    return NumericRoots(
        polynomial=str(expr),
        variable=variable,
        roots=[str(r) for r in numeric_roots],
        digits=digits,
    )


# ===========================================================================
# Calculus
# ===========================================================================


@mcp.tool()
def differentiate(
    expression: str,
    variable: str = "x",
    order: int = 1,
    symbols: list[str] | None = None,
) -> ExactResult:
    """USE THIS WHEN the user asks for a derivative or rate of change."""
    order = limits.validate_order(order, label="order", cap=limits.MAX_DIFF_ORDER)
    local = _symbols(symbols) | {variable: sp.Symbol(variable)}
    expr = _parse(expression, local)
    result = sp.diff(expr, local[variable], order)
    return _scalar_result(sp.simplify(result), parsed=str(expr))


@mcp.tool()
def integrate(
    expression: str,
    variable: str = "x",
    lower: str | None = None,
    upper: str | None = None,
    symbols: list[str] | None = None,
) -> ExactResult:
    """USE THIS WHEN the user asks for an integral (definite or indefinite)
    or an area under a curve. Omit lower/upper for an indefinite integral."""
    local = _symbols(symbols) | {variable: sp.Symbol(variable)}
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
    return _scalar_result(sp.simplify(result), digits=50, parsed=str(expr))


@mcp.tool()
def limit(
    expression: str,
    variable: str = "x",
    point: str = "0",
    direction: str = "+-",
    symbols: list[str] | None = None,
) -> ExactResult:
    """USE THIS WHEN the user asks for a limit of an expression as a variable
    approaches a value. direction may be '+' (right), '-' (left), or '+-'
    (two-sided)."""
    if direction not in {"+", "-", "+-"}:
        raise ValueError("direction must be '+', '-', or '+-'")
    local = _symbols(symbols) | {variable: sp.Symbol(variable)}
    expr = _parse(expression, local)
    pt = _parse(point, local)
    result = sp.limit(expr, local[variable], pt, direction)
    return _scalar_result(result, digits=50, parsed=str(expr))


@mcp.tool()
def series(
    expression: str,
    variable: str = "x",
    point: str = "0",
    order: int = 6,
    symbols: list[str] | None = None,
) -> ExactResult:
    """USE THIS WHEN the user asks for a Taylor or Laurent series expansion
    around a point."""
    order = limits.validate_order(order, label="order", cap=limits.MAX_SERIES_ORDER)
    local = _symbols(symbols) | {variable: sp.Symbol(variable)}
    expr = _parse(expression, local)
    pt = _parse(point, local)
    result = sp.series(expr, local[variable], pt, order).removeO()
    return _scalar_result(result, parsed=str(expr))


@mcp.tool()
def summation(
    expression: str,
    index: str = "n",
    lower: str = "1",
    upper: str = "oo",
    symbols: list[str] | None = None,
) -> ExactResult:
    """USE THIS WHEN the user asks for a sum (finite or infinite) of a term
    over an integer index. For example, Σ 1/n² from 1 to ∞."""
    local = _symbols(symbols) | {index: sp.Symbol(index)}
    expr = _parse(expression, local)
    lo = _parse(lower, local)
    hi = _parse(upper, local)
    result = sp.summation(expr, (local[index], lo, hi))
    return _scalar_result(sp.simplify(result), digits=50, parsed=str(expr))


# ===========================================================================
# Number theory
# ===========================================================================


@mcp.tool()
def gcd(numbers: list[str]) -> IntegerResult:
    """USE THIS WHEN the user asks for the greatest common divisor / highest
    common factor of two or more integers (any size)."""
    values = [_as_integer(_parse(n), label="input") for n in numbers]
    if len(values) < 2:
        raise ValueError("need at least two numbers")
    result = values[0]
    for v in values[1:]:
        result = int(sp.gcd(result, v))
    return IntegerResult(
        value=str(result),
        context={"inputs": ", ".join(str(v) for v in values)},
    )


@mcp.tool()
def lcm(numbers: list[str]) -> IntegerResult:
    """USE THIS WHEN the user asks for the least common multiple of two or
    more integers."""
    values = [_as_integer(_parse(n), label="input") for n in numbers]
    if len(values) < 2:
        raise ValueError("need at least two numbers")
    result = values[0]
    for v in values[1:]:
        result = int(sp.lcm(result, v))
    return IntegerResult(
        value=str(result),
        context={"inputs": ", ".join(str(v) for v in values)},
    )


@mcp.tool()
def factorint(number: str) -> Factorization:
    """USE THIS WHEN the user asks for the prime factorization of an integer."""
    n = _as_integer(_parse(number), label="number")
    if n < 1:
        raise ValueError("number must be positive")
    fac = sp.factorint(n)
    pretty = " * ".join(f"{p}^{e}" if e > 1 else str(p) for p, e in fac.items())
    return Factorization(
        number=str(n),
        factors={str(p): int(e) for p, e in fac.items()},
        pretty=pretty,
        distinct_primes=len(fac),
    )


@mcp.tool()
def is_prime(number: str) -> BooleanResult:
    """USE THIS WHEN the user asks whether a (possibly large) integer is
    prime. Deterministic below ~25 digits, BPSW above — never a false claim."""
    n = _as_integer(_parse(number), label="number")
    limits.validate_integer_bits(n, label="number", cap=limits.MAX_PRIMALITY_BITS)
    return BooleanResult(value=bool(sp.isprime(n)), subject=str(n))


@mcp.tool()
def nth_prime(n: int) -> IntegerResult:
    """USE THIS WHEN the user asks "what is the Nth prime?" (1-indexed:
    prime(1) = 2)."""
    n = int(n)
    if n < 1:
        raise ValueError("n must be a positive integer (1-indexed)")
    if n > limits.MAX_NTH_PRIME_INDEX:
        raise ValueError(
            f"n too large ({n}; max {limits.MAX_NTH_PRIME_INDEX})"
        )
    return IntegerResult(
        value=str(int(sp.prime(n))),
        context={"index": str(n)},
    )


@mcp.tool()
def next_prime(number: str) -> IntegerResult:
    """USE THIS WHEN the user asks for the smallest prime strictly greater
    than a given integer."""
    n = _as_integer(_parse(number), label="number")
    return IntegerResult(
        value=str(int(sp.nextprime(n))),
        context={"of": str(n)},
    )


@mcp.tool()
def mod_pow(base: str, exponent: str, modulus: str) -> IntegerResult:
    """USE THIS WHEN the user asks for (base**exponent) mod modulus —
    common in cryptography. Exact for integers of any size."""
    b = _as_integer(_parse(base), label="base")
    e = _as_integer(_parse(exponent), label="exponent")
    m = _as_integer(_parse(modulus), label="modulus")
    if m <= 0:
        raise ValueError("modulus must be positive")
    if e < 0:
        if pow(b, -e, m) == 0:
            raise ValueError(
                "base is not invertible modulo modulus "
                f"(gcd({b}, {m}) != 1)"
            )
        try:
            result = pow(b, e, m)
        except ValueError:
            raise ValueError(
                "base is not invertible modulo modulus "
                f"(gcd({b}, {m}) != 1)"
            )
    else:
        result = pow(b, e, m)
    return IntegerResult(
        value=str(result),
        context={"base": str(b), "exponent": str(e), "modulus": str(m)},
    )


@mcp.tool()
def mod_inverse(a: str, modulus: str) -> IntegerResult:
    """USE THIS WHEN the user asks for the modular multiplicative inverse —
    the integer x such that a*x ≡ 1 (mod m). Errors if gcd(a, m) ≠ 1."""
    a_i = _as_integer(_parse(a), label="a")
    m_i = _as_integer(_parse(modulus), label="modulus")
    return IntegerResult(
        value=str(int(sp.mod_inverse(a_i, m_i))),
        context={"a": str(a_i), "modulus": str(m_i)},
    )


# ===========================================================================
# Combinatorics
# ===========================================================================


@mcp.tool()
def binomial(n: int, k: int) -> CombinatoricResult:
    """USE THIS WHEN the user asks for "n choose k" or a binomial coefficient."""
    n, k = limits.validate_combinatoric(n, k)
    return CombinatoricResult(
        operation="binomial", n=n, k=k, value=str(int(sp.binomial(n, k))),
    )


@mcp.tool()
def permutations(n: int, k: int) -> CombinatoricResult:
    """USE THIS WHEN the user asks for the number of k-permutations of n
    distinct items (P(n, k) = n! / (n-k)!)."""
    n, k = limits.validate_combinatoric(n, k)
    if k > n:
        raise ValueError("k must be <= n for permutations")
    return CombinatoricResult(
        operation="permutations", n=n, k=k,
        value=str(int(sp.factorial(n) // sp.factorial(n - k))),
    )


@mcp.tool()
def combinations(n: int, k: int) -> CombinatoricResult:
    """USE THIS WHEN the user asks for the number of k-combinations of n
    distinct items (alias for binomial, returned with operation tag)."""
    n, k = limits.validate_combinatoric(n, k)
    return CombinatoricResult(
        operation="combinations", n=n, k=k,
        value=str(int(sp.binomial(n, k))),
    )


# ===========================================================================
# Linear algebra
# ===========================================================================


@mcp.tool()
def matrix_determinant(matrix: list[list[str | int | float]]) -> ExactResult:
    """USE THIS WHEN the user asks for the determinant of a square matrix."""
    M = _parse_matrix(matrix)
    if M.rows != M.cols:
        raise ValueError("determinant requires a square matrix")
    return _scalar_result(M.det(), parsed=f"{M.rows}x{M.cols} matrix")


@mcp.tool()
def matrix_inverse(matrix: list[list[str | int | float]]) -> MatrixResult:
    """USE THIS WHEN the user asks for the inverse of a square matrix.
    Raises if the matrix is singular."""
    M = _parse_matrix(matrix)
    if M.rows != M.cols:
        raise ValueError("inverse requires a square matrix")
    return _matrix_result(M.inv())


@mcp.tool()
def matrix_multiply(
    a: list[list[str | int | float]], b: list[list[str | int | float]]
) -> MatrixResult:
    """USE THIS WHEN the user asks for the product A*B of two matrices."""
    A = _parse_matrix(a)
    B = _parse_matrix(b)
    if A.cols != B.rows:
        raise ValueError(
            f"matrix dim mismatch for multiply: "
            f"{A.rows}x{A.cols} * {B.rows}x{B.cols}"
        )
    return _matrix_result(A * B)


@mcp.tool()
def matrix_eigenvalues(
    matrix: list[list[str | int | float]], digits: int = 15
) -> Eigenvalues:
    """USE THIS WHEN the user asks for the eigenvalues (with algebraic
    multiplicities) of a square matrix. Returns both the exact symbolic
    form and a decimal approximation at `digits` precision — prefer the
    `numeric` field for readable values when the symbolic form is an
    unwieldy nested radical."""
    M = _parse_matrix(matrix)
    if M.rows != M.cols:
        raise ValueError("eigenvalues require a square matrix")
    digits = limits.clamp_digits(digits)
    eigs = M.eigenvals()
    numeric: dict[str, str] | None = {}
    for k in eigs:
        # chop=True strips tiny imaginary artefacts left by evalf when the
        # symbolic form goes through complex intermediates (e.g. the
        # trig/cube-root form for real eigenvalues of a 3x3 symmetric matrix).
        approx = sp.sympify(k).evalf(digits, chop=True)
        if approx.free_symbols:
            numeric = None
            break
        numeric[str(k)] = str(approx)
    return Eigenvalues(
        dim=M.rows,
        eigenvalues={str(k): int(v) for k, v in eigs.items()},
        numeric=numeric,
        digits=digits if numeric is not None else None,
        latex=_latex(eigs),
    )


@mcp.tool()
def matrix_solve(
    a: list[list[str | int | float]], b: list[list[str | int | float]]
) -> MatrixResult:
    """USE THIS WHEN the user asks to solve a linear system A x = b
    exactly. `a` and `b` are nested-list matrices."""
    A = _parse_matrix(a)
    B = _parse_matrix(b)
    if A.rows != B.rows:
        raise ValueError(
            f"A and b row-dim mismatch: {A.rows} vs {B.rows}"
        )
    return _matrix_result(A.solve(B))


# ===========================================================================
# Statistics
# ===========================================================================


@mcp.tool()
def stats(numbers: list[str]) -> Stats:
    """USE THIS WHEN the user asks for summary statistics (mean, median,
    variance, standard deviation, min, max) of a list of numbers. Results
    are exact where possible."""
    if not numbers:
        raise ValueError("need at least one number")
    limits.validate_stats_n(len(numbers))
    vals = [_parse(str(n)) for n in numbers]
    for v in vals:
        if not v.is_number or not v.is_real:
            raise ValueError(
                f"stats requires real numeric inputs (got non-numeric: {v})"
            )
    n = len(vals)
    mean = sum(vals, sp.Rational(0)) / n
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
    mean_s = sp.simplify(mean)
    variance_s = sp.simplify(variance)
    stdev_s = sp.simplify(stdev)
    decimal_block: dict[str, str] = {}
    for label, expr in (
        ("mean", mean_s),
        ("variance_sample", variance_s),
        ("stdev_sample", stdev_s),
    ):
        if expr.is_number:
            decimal_block[label] = str(sp.N(expr, 30))
    return Stats(
        count=n,
        mean=str(mean_s),
        median=str(sp.simplify(median)),
        variance_sample=str(variance_s),
        stdev_sample=str(stdev_s),
        min=str(sorted_vals[0]),
        max=str(sorted_vals[-1]),
        decimal=decimal_block or None,
    )


# ===========================================================================
# Conversions
# ===========================================================================


@mcp.tool()
def to_rational(value: str, max_denominator: int = 10**9) -> RationalResult:
    """USE THIS WHEN the user has a decimal string (e.g. "0.142857142857")
    and wants the best rational approximation, bounded by max_denominator."""
    expr = _parse(value)
    num = sp.nsimplify(expr, rational=True, rational_conversion="exact")
    approx = sp.Rational(num).limit_denominator(int(max_denominator))
    return RationalResult(
        rational=str(approx),
        numer=str(int(approx.p)),
        denom=str(int(approx.q)),
        decimal=str(sp.N(approx, 50)),
        exact_rational=str(num),
    )


@mcp.tool()
def to_base(number: str, base: int) -> BaseConversionResult:
    """USE THIS WHEN the user asks to convert an integer to binary, hex,
    octal, or any base from 2 to 36."""
    base = limits.validate_base(base)
    n = _as_integer(_parse(number), label="number")

    def _digits(x: int, b: int) -> str:
        if x == 0:
            return "0"
        sign = "-" if x < 0 else ""
        x = abs(x)
        alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
        out: list[str] = []
        while x:
            x, r = divmod(x, b)
            out.append(alphabet[r])
        return sign + "".join(reversed(out))

    return BaseConversionResult(
        input=number,
        decimal_value=str(n),
        base_from=10,
        base_to=base,
        digits=_digits(n, base),
    )


@mcp.tool()
def from_base(digits: str, base: int) -> IntegerResult:
    """USE THIS WHEN the user provides a string of digits in a given base
    (2-36) and wants the decimal integer."""
    base = limits.validate_base(base)
    if not isinstance(digits, str) or not digits.strip():
        raise ValueError("digits must be a non-empty string")
    limits.validate_expr_len(digits, label="digits")
    try:
        value = int(digits, base)
    except ValueError as e:
        raise ValueError(f"invalid digit string for base {base}: {e}") from None
    limits.validate_integer_bits(value, label="parsed integer")
    return IntegerResult(
        value=str(value),
        context={"digits": digits, "base": str(base)},
    )


@mcp.tool()
def convert_units(
    value: str, source_unit: str, target_unit: str
) -> UnitConversion:
    """USE THIS WHEN the user asks to convert a physical quantity between
    units (e.g. meters to feet, kilograms to pounds, seconds to hours,
    joules to calories). Unit names follow SymPy's `physics.units` module
    (meter, foot, inch, kilogram, pound, second, hour, kelvin, joule, etc.)."""
    from sympy.physics import units as u

    def _resolve(name: str):
        obj = getattr(u, name, None)
        if obj is None or not isinstance(obj, u.Quantity):
            raise ValueError(
                f"unknown unit: '{name}'. Try meter, foot, inch, yard, "
                f"mile, kilometer, centimeter, kilogram, gram, pound, "
                f"ounce, second, minute, hour, day, year, kelvin, joule, "
                f"calorie, watt, newton, pascal, hertz."
            )
        return obj

    v = _parse(value)
    src = _resolve(source_unit)
    tgt = _resolve(target_unit)
    converted_expr = u.convert_to(v * src, tgt)
    scalar = sp.simplify(converted_expr / tgt)
    decimal_str = None
    if scalar.is_number:
        decimal_str = str(sp.N(scalar, 15))
    return UnitConversion(
        value=str(v),
        source_unit=source_unit,
        target_unit=target_unit,
        converted=f"{scalar} {target_unit}",
        decimal=decimal_str,
    )


# ===========================================================================
# Entry point
# ===========================================================================


def main() -> None:
    """Console entry point — runs the MCP server over stdio."""
    mcp.run()
