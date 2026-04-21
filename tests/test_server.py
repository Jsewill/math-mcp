"""Correctness, input-validation, and defensive-branch tests for math-mcp.

Every tool has at least one happy-path test; every error branch has a matching
test. Defensive `except` branches unreachable through user input (SymPy
internals failing) are forced via monkeypatch.
"""

from __future__ import annotations

import runpy

import pytest
import sympy as sp

from math_mcp import limits as lim
from math_mcp import server as srv
from math_mcp.models import (
    BaseConversionResult,
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
from math_mcp.server import _parse, mcp


@pytest.fixture(scope="module")
def tools() -> dict:
    return {t.name: t.fn for t in mcp._tool_manager._tools.values()}


# ---------------------------------------------------------------------------
# Fixture / registration
# ---------------------------------------------------------------------------


def test_registered_tool_count(tools: dict) -> None:
    assert len(tools) == 36


def test_server_ships_routing_instructions() -> None:
    """Server-level `instructions` is what MCP clients inject into the
    model's context. If this gets dropped, automatic tool routing
    regresses for every downstream user.
    """
    instructions = mcp.instructions or ""
    assert "math-mcp" in instructions
    # Key routing triggers that must stay intact
    for phrase in (
        "Mental arithmetic",
        "symbolic",
        "mod_pow",
        "decimal-digit strings",
    ):
        assert phrase in instructions, f"missing routing hint: {phrase!r}"


# ---------------------------------------------------------------------------
# limits.py
# ---------------------------------------------------------------------------


def test_validate_expr_len_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        lim.validate_expr_len(42)  # type: ignore[arg-type]


def test_validate_expr_len_rejects_overlong() -> None:
    with pytest.raises(ValueError):
        lim.validate_expr_len("x" * (lim.MAX_EXPR_LEN + 1))


def test_validate_integer_bits_caps() -> None:
    with pytest.raises(ValueError):
        lim.validate_integer_bits(2 ** (lim.MAX_INTEGER_BITS + 1))


def test_validate_matrix_dims_non_positive() -> None:
    with pytest.raises(ValueError):
        lim.validate_matrix_dims(0, 4)


def test_validate_matrix_dims_too_big() -> None:
    with pytest.raises(ValueError):
        lim.validate_matrix_dims(lim.MAX_MATRIX_DIM + 1, 2)


def test_clamp_digits_floor_and_ceiling() -> None:
    assert lim.clamp_digits(-5) == 1
    assert lim.clamp_digits(0) == 1
    assert lim.clamp_digits(10) == 10
    assert lim.clamp_digits(lim.MAX_NUMERIC_DIGITS + 99) == lim.MAX_NUMERIC_DIGITS


def test_validate_order_negative() -> None:
    with pytest.raises(ValueError):
        lim.validate_order(-1, label="order", cap=10)


def test_validate_order_too_big() -> None:
    with pytest.raises(ValueError):
        lim.validate_order(50, label="order", cap=10)


def test_validate_combinatoric_caps() -> None:
    with pytest.raises(ValueError):
        lim.validate_combinatoric(-1, 2)
    with pytest.raises(ValueError):
        lim.validate_combinatoric(lim.MAX_COMBINATORIC_N + 1, 1)


def test_validate_base_bounds() -> None:
    with pytest.raises(ValueError):
        lim.validate_base(1)
    with pytest.raises(ValueError):
        lim.validate_base(37)
    assert lim.validate_base(16) == 16


def test_validate_stats_n() -> None:
    with pytest.raises(ValueError):
        lim.validate_stats_n(lim.MAX_STATS_N + 1)


# ---------------------------------------------------------------------------
# Parse helper
# ---------------------------------------------------------------------------


def test_parse_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        _parse(123)  # type: ignore[arg-type]


def test_parse_rejects_whitespace() -> None:
    with pytest.raises(ValueError):
        _parse("   ")


def test_parse_rejects_overlong() -> None:
    with pytest.raises(ValueError):
        _parse("x" * (lim.MAX_EXPR_LEN + 1))


# ---------------------------------------------------------------------------
# Arithmetic / numeric
# ---------------------------------------------------------------------------


def test_bigint_arithmetic(tools: dict) -> None:
    r: ExactResult = tools["evaluate"](expression="2**100 + 1")
    assert r.exact == "1267650600228229401496703205377"
    assert r.decimal_digits == 50


def test_rational_no_float_drift(tools: dict) -> None:
    r: ExactResult = tools["evaluate"](expression="1/3 + 1/7 + 1/11")
    assert r.exact == "131/231"


def test_evaluate_clamp_low(tools: dict) -> None:
    r = tools["evaluate"](expression="pi", precision=0)
    assert r.decimal_digits == 1


def test_evaluate_clamp_high(tools: dict) -> None:
    r = tools["evaluate"](expression="pi", precision=99_999)
    assert r.decimal_digits == lim.MAX_NUMERIC_DIGITS


def test_evaluate_symbolic_has_no_decimal(tools: dict) -> None:
    r = tools["evaluate"](expression="x + x")
    assert r.exact == "2*x"
    assert r.decimal is None
    assert r.decimal_digits is None


def test_rejects_empty_expression(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["evaluate"](expression="")


def test_numeric_pi_60(tools: dict) -> None:
    r: ExactResult = tools["numeric"](expression="pi", digits=60)
    assert r.exact.startswith("3.14159265358979323846264338327950288419716939937510582097494")
    assert r.decimal_digits == 60


def test_numeric_clamp_high(tools: dict) -> None:
    r = tools["numeric"](expression="1", digits=1_000_000)
    assert r.decimal_digits == lim.MAX_NUMERIC_DIGITS


# ---------------------------------------------------------------------------
# Algebra
# ---------------------------------------------------------------------------


def test_simplify(tools: dict) -> None:
    r = tools["simplify"](expression="(x**2 - 1)/(x - 1)", symbols=["x"])
    assert r.exact == "x + 1"


def test_expand_cube(tools: dict) -> None:
    r = tools["expand"](expression="(x+1)**3", symbols=["x"])
    assert r.exact == "x**3 + 3*x**2 + 3*x + 1"


def test_factor(tools: dict) -> None:
    r = tools["factor"](expression="x**4 - 1", symbols=["x"])
    assert r.exact == "(x - 1)*(x + 1)*(x**2 + 1)"


def test_solve_real(tools: dict) -> None:
    r: SolutionSet = tools["solve_equation"](
        equation="x**2 - 2 = 0", variable="x", domain="real")
    assert set(r.solutions) == {"-sqrt(2)", "sqrt(2)"}
    assert r.domain == "real"


def test_solve_complex(tools: dict) -> None:
    r = tools["solve_equation"](equation="x**2 + 1 = 0", domain="complex")
    assert set(r.solutions) == {"-I", "I"}


def test_solve_integer(tools: dict) -> None:
    r = tools["solve_equation"](equation="x**2 - 4 = 0", domain="integer")
    assert set(r.solutions) == {"-2", "2"}


def test_solve_rational(tools: dict) -> None:
    r = tools["solve_equation"](equation="2*x - 1 = 0", domain="rational")
    assert r.solutions == ["1/2"]


def test_solve_implicit_zero(tools: dict) -> None:
    r = tools["solve_equation"](equation="x**2 - 9", domain="real")
    assert set(r.solutions) == {"-3", "3"}


def test_solve_non_iterable_falls_back(tools: dict) -> None:
    r = tools["solve_equation"](
        equation="x**x - 2 = 0", variable="x", domain="real")
    assert r.solutions is None
    assert "ConditionSet" in r.set_repr or "x**x" in r.set_repr


def test_solve_bad_domain_raises(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["solve_equation"](equation="x=0", domain="quaternion")


def test_solve_inequality_gt(tools: dict) -> None:
    r: IntervalResult = tools["solve_inequality"](
        inequality="x**2 - 4 > 0", variable="x")
    assert "Interval.open(-oo, -2)" in r.solution_set
    assert "Interval.open(2, oo)" in r.solution_set


def test_solve_inequality_lt(tools: dict) -> None:
    r = tools["solve_inequality"](inequality="x - 3 < 0", variable="x")
    assert "(-oo, 3)" in r.solution_set


def test_solve_inequality_ge(tools: dict) -> None:
    r = tools["solve_inequality"](inequality="x >= 2", variable="x")
    assert r.solution_set == "Interval(2, oo)"


def test_solve_inequality_le(tools: dict) -> None:
    r = tools["solve_inequality"](inequality="x <= 5", variable="x")
    assert r.solution_set == "Interval(-oo, 5)"


def test_solve_inequality_requires_operator(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["solve_inequality"](inequality="x + 3", variable="x")


def test_solve_system(tools: dict) -> None:
    r: SystemSolution = tools["solve_system"](
        equations=["x + y = 3", "x - y = 1"], variables=["x", "y"])
    assert r.solutions == [{"x": "2", "y": "1"}]


def test_solve_system_implicit_zero(tools: dict) -> None:
    r = tools["solve_system"](equations=["x - 5"], variables=["x"])
    assert r.solutions == [{"x": "5"}]


def test_polynomial_roots(tools: dict) -> None:
    r: Roots = tools["polynomial_roots"](
        polynomial="(x - 1)**2 * (x - 2)", variable="x")
    assert r.multiplicities == {"1": 2, "2": 1}


def test_nroots_quintic(tools: dict) -> None:
    r: NumericRoots = tools["nroots"](
        expression="x**5 - x - 1", variable="x", digits=15)
    assert len(r.roots) == 5
    assert r.digits == 15


# ---------------------------------------------------------------------------
# Calculus
# ---------------------------------------------------------------------------


def test_derivative(tools: dict) -> None:
    r = tools["differentiate"](
        expression="sin(x)*exp(x)", variable="x", order=2)
    assert r.exact == "2*exp(x)*cos(x)"


def test_derivative_order_too_large(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["differentiate"](
            expression="x", variable="x", order=lim.MAX_DIFF_ORDER + 1)


def test_derivative_negative_order(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["differentiate"](expression="x", variable="x", order=-1)


def test_integrate_definite(tools: dict) -> None:
    r = tools["integrate"](
        expression="1/(1+x**2)", variable="x", lower="0", upper="1")
    assert r.exact == "pi/4"


def test_integrate_indefinite(tools: dict) -> None:
    r = tools["integrate"](expression="x**2", variable="x")
    assert r.exact == "x**3/3"


def test_integrate_partial_bounds_raises(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["integrate"](expression="x", variable="x", lower="0")


def test_limit_sinc(tools: dict) -> None:
    r = tools["limit"](expression="sin(x)/x", variable="x", point="0")
    assert r.exact == "1"


def test_limit_right(tools: dict) -> None:
    r = tools["limit"](
        expression="1/x", variable="x", point="0", direction="+")
    assert r.exact == "oo"


def test_limit_left(tools: dict) -> None:
    r = tools["limit"](
        expression="1/x", variable="x", point="0", direction="-")
    assert r.exact == "-oo"


def test_limit_bad_direction(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["limit"](
            expression="x", variable="x", point="0", direction="?")


def test_series_exp(tools: dict) -> None:
    r = tools["series"](
        expression="exp(x)", variable="x", point="0", order=5)
    assert r.exact == "x**4/24 + x**3/6 + x**2/2 + x + 1"


def test_series_order_cap(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["series"](
            expression="exp(x)", variable="x", point="0",
            order=lim.MAX_SERIES_ORDER + 1)


def test_basel_problem(tools: dict) -> None:
    r = tools["summation"](
        expression="1/n**2", index="n", lower="1", upper="oo")
    assert r.exact == "pi**2/6"


# ---------------------------------------------------------------------------
# Number theory
# ---------------------------------------------------------------------------


def test_gcd(tools: dict) -> None:
    r: IntegerResult = tools["gcd"](numbers=["462", "1071"])
    assert r.value == "21"


def test_gcd_needs_two(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["gcd"](numbers=["5"])


def test_lcm(tools: dict) -> None:
    r = tools["lcm"](numbers=["6", "8", "10"])
    assert r.value == "120"


def test_lcm_needs_two(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["lcm"](numbers=["5"])


def test_factorint(tools: dict) -> None:
    r: Factorization = tools["factorint"](number="360")
    assert r.factors == {"2": 3, "3": 2, "5": 1}
    assert r.pretty == "2^3 * 3^2 * 5"
    assert r.distinct_primes == 3


def test_factorint_rejects_non_positive(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["factorint"](number="0")


def test_mersenne_prime(tools: dict) -> None:
    r: BooleanResult = tools["is_prime"](number="2**521 - 1")
    assert r.value is True


def test_nth_prime(tools: dict) -> None:
    r = tools["nth_prime"](n=10)
    assert r.value == "29"


def test_nth_prime_non_positive(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["nth_prime"](n=0)


def test_nth_prime_too_large(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["nth_prime"](n=lim.MAX_NTH_PRIME_INDEX + 1)


def test_next_prime(tools: dict) -> None:
    r = tools["next_prime"](number="100")
    assert r.value == "101"


def test_mod_pow(tools: dict) -> None:
    r = tools["mod_pow"](base="7", exponent="2**100", modulus="10**9+7")
    assert r.value == "641087921"


def test_mod_pow_zero_modulus(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["mod_pow"](base="2", exponent="3", modulus="0")


def test_mod_pow_big_precision(tools: dict) -> None:
    """Modular exponentiation result must survive as a full-precision string.

    7^(2**100) mod (2**127 - 1) lands in the 38-digit range — well above
    the 2**53 float64 safe-integer ceiling.
    """
    r = tools["mod_pow"](base="7", exponent="2**100", modulus="2**127 - 1")
    # Cross-check with Python's arbitrary-precision pow
    expected = str(pow(7, 2**100, 2**127 - 1))
    assert r.value == expected
    assert len(r.value) >= 35


def test_gcd_big_precision(tools: dict) -> None:
    """GCD of two large integers should survive unchanged."""
    a = 2**200 * 3**50
    b = 2**150 * 3**100
    r = tools["gcd"](numbers=[str(a), str(b)])
    assert r.value == str(2**150 * 3**50)
    assert len(r.value) >= 40


def test_mod_inverse(tools: dict) -> None:
    r = tools["mod_inverse"](a="3", modulus="11")
    assert r.value == "4"


# ---------------------------------------------------------------------------
# Combinatorics
# ---------------------------------------------------------------------------


def test_binomial(tools: dict) -> None:
    r: CombinatoricResult = tools["binomial"](n=10, k=3)
    assert r.value == "120"
    assert r.operation == "binomial"


def test_binomial_big_precision(tools: dict) -> None:
    """C(200, 100) is 59 digits — exceeds float64 safe-integer range.

    Asserts that the string-transported value preserves every digit.
    """
    r = tools["binomial"](n=200, k=100)
    assert r.value == (
        "90548514656103281165404177077484163874504589675413336841320"
    )
    assert len(r.value) == 59


def test_permutations(tools: dict) -> None:
    r = tools["permutations"](n=5, k=2)
    assert r.value == "20"


def test_permutations_k_gt_n(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["permutations"](n=3, k=5)


def test_combinations(tools: dict) -> None:
    r = tools["combinations"](n=6, k=2)
    assert r.value == "15"


def test_combinations_k_gt_n(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["combinations"](n=3, k=5)


# ---------------------------------------------------------------------------
# Linear algebra
# ---------------------------------------------------------------------------


def test_matrix_determinant(tools: dict) -> None:
    r = tools["matrix_determinant"](matrix=[["1", "2"], ["3", "4"]])
    assert r.exact == "-2"


def test_matrix_determinant_non_square(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["matrix_determinant"](matrix=[["1", "2", "3"], ["4", "5", "6"]])


def test_matrix_inverse(tools: dict) -> None:
    r: MatrixResult = tools["matrix_inverse"](
        matrix=[["1", "2"], ["3", "4"]])
    assert r.data == [["-2", "1"], ["3/2", "-1/2"]]


def test_matrix_inverse_non_square(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["matrix_inverse"](matrix=[["1", "2", "3"], ["4", "5", "6"]])


def test_matrix_multiply(tools: dict) -> None:
    r = tools["matrix_multiply"](
        a=[["1", "2"], ["3", "4"]], b=[["5", "6"], ["7", "8"]])
    assert r.data == [["19", "22"], ["43", "50"]]


def test_matrix_multiply_dim_mismatch(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["matrix_multiply"](
            a=[["1", "2"]], b=[["1", "2"], ["3", "4"], ["5", "6"]])


def test_matrix_eigenvalues(tools: dict) -> None:
    r: Eigenvalues = tools["matrix_eigenvalues"](
        matrix=[["2", "0"], ["0", "3"]])
    assert r.dim == 2
    assert r.eigenvalues == {"2": 1, "3": 1}


def test_matrix_eigenvalues_non_square(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["matrix_eigenvalues"](matrix=[["1", "2", "3"], ["4", "5", "6"]])


def test_matrix_solve(tools: dict) -> None:
    r = tools["matrix_solve"](
        a=[["1", "2"], ["3", "4"]], b=[["5"], ["11"]])
    assert r.data == [["1"], ["2"]]


def test_matrix_solve_row_mismatch(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["matrix_solve"](
            a=[["1", "2"], ["3", "4"]], b=[["5"], ["11"], ["17"]])


def test_matrix_empty_rejected(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["matrix_determinant"](matrix=[])


def test_matrix_ragged_rejected(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["matrix_determinant"](matrix=[["1", "2"], ["3"]])


def test_matrix_too_big_rejected(tools: dict) -> None:
    big = [["0"] * (lim.MAX_MATRIX_DIM + 1)
           for _ in range(lim.MAX_MATRIX_DIM + 1)]
    with pytest.raises(ValueError):
        tools["matrix_determinant"](matrix=big)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def test_stats_exact(tools: dict) -> None:
    r: Stats = tools["stats"](
        numbers=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])
    assert r.mean == "11/2"
    assert r.variance_sample == "55/6"
    assert r.decimal is not None


def test_stats_single_value(tools: dict) -> None:
    r = tools["stats"](numbers=["7"])
    assert r.mean == "7"
    assert r.median == "7"
    assert r.variance_sample == "0"
    assert r.stdev_sample == "0"


def test_stats_odd_count(tools: dict) -> None:
    r = tools["stats"](numbers=["1", "2", "3"])
    assert r.median == "2"


def test_stats_rejects_symbolic(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["stats"](numbers=["x", "x", "x"])


def test_stats_empty(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["stats"](numbers=[])


# ---------------------------------------------------------------------------
# Conversions
# ---------------------------------------------------------------------------


def test_to_rational(tools: dict) -> None:
    r: RationalResult = tools["to_rational"](
        value="0.333333333333", max_denominator=1000)
    assert r.rational == "1/3"
    assert r.numer == "1" and r.denom == "3"


def test_to_base_hex(tools: dict) -> None:
    r: BaseConversionResult = tools["to_base"](number="255", base=16)
    assert r.digits == "ff"
    assert r.base_to == 16


def test_to_base_binary(tools: dict) -> None:
    r = tools["to_base"](number="42", base=2)
    assert r.digits == "101010"


def test_to_base_zero(tools: dict) -> None:
    r = tools["to_base"](number="0", base=16)
    assert r.digits == "0"


def test_to_base_negative(tools: dict) -> None:
    r = tools["to_base"](number="-26", base=16)
    assert r.digits == "-1a"


def test_to_base_rejects_bad_base(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["to_base"](number="5", base=1)


def test_from_base_hex(tools: dict) -> None:
    r = tools["from_base"](digits="ff", base=16)
    assert r.value == "255"


def test_from_base_empty_rejected(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["from_base"](digits="", base=2)


def test_from_base_invalid_digits(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["from_base"](digits="2", base=2)


def test_convert_meter_to_foot(tools: dict) -> None:
    r: UnitConversion = tools["convert_units"](
        value="5", source_unit="meter", target_unit="foot")
    assert r.decimal is not None
    assert "foot" in r.converted
    # 5 m ≈ 16.404 ft
    assert abs(float(r.decimal) - 16.4041994750656) < 1e-9


def test_convert_unknown_unit(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["convert_units"](
            value="1", source_unit="meter", target_unit="furlong2000")


# ---------------------------------------------------------------------------
# Defensive branches (forced via monkeypatch)
# ---------------------------------------------------------------------------


def test_latex_failure_omits_latex(monkeypatch, tools: dict) -> None:
    monkeypatch.setattr(srv.sp, "latex",
                        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("x")))
    r = tools["evaluate"](expression="2+2")
    assert r.exact == "4"
    assert r.latex is None


def test_decimal_failure_captured(monkeypatch, tools: dict) -> None:
    monkeypatch.setattr(srv.sp, "N",
                        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("no N")))
    r = tools["evaluate"](expression="pi", precision=10)
    assert r.decimal_error == "no N"


def test_evaluate_simplify_exception_fallback(monkeypatch, tools: dict) -> None:
    monkeypatch.setattr(srv.sp, "simplify",
                        lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("no simplify")))
    r = tools["evaluate"](expression="2+2")
    assert r.exact == "4"


def test_as_integer_rejects_non_integer() -> None:
    with pytest.raises(ValueError):
        srv._as_integer(sp.Rational(1, 2), label="x")


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def test_main_runs_mcp(monkeypatch) -> None:
    calls = {"count": 0}
    monkeypatch.setattr(srv.mcp, "run",
                        lambda *a, **kw: calls.__setitem__("count", calls["count"] + 1))
    srv.main()
    runpy.run_module("math_mcp", run_name="__main__")
    assert calls["count"] == 2


