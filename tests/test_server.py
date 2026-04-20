"""Correctness and coverage tests for math-mcp.

Each tool has at least one happy-path test; each error branch has a matching
test. Defensive `except` branches that cannot be reached through normal input
(LaTeX renderer failure, numeric evaluation failure) are forced via monkeypatch.
"""

from __future__ import annotations

import json
import runpy

import pytest
import sympy as sp

from math_mcp import server as srv
from math_mcp.server import _parse, _to_native, mcp


@pytest.fixture(scope="module")
def tools() -> dict:
    return {t.name: t.fn for t in mcp._tool_manager._tools.values()}


def _call(tools: dict, name: str, **kwargs):
    return json.loads(tools[name](**kwargs))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_registered_tool_count(tools: dict) -> None:
    assert len(tools) == 27


def test_to_native_rational_dict() -> None:
    r = _to_native(sp.Rational(3, 7))
    assert r == {"numer": 3, "denom": 7, "str": "3/7"}


def test_to_native_float_dict() -> None:
    r = _to_native(sp.Float("1.5"))
    assert r == {"float": "1.50000000000000", "mpf": True}


def test_to_native_tuple_and_dict_keys() -> None:
    r = _to_native((sp.Integer(1), sp.Integer(2)))
    assert r == [1, 2]
    r = _to_native({sp.Integer(1): sp.Integer(2)})
    assert r == {"1": 2}


def test_parse_rejects_non_string() -> None:
    with pytest.raises(ValueError):
        _parse(123)  # type: ignore[arg-type]


def test_parse_rejects_whitespace() -> None:
    with pytest.raises(ValueError):
        _parse("   ")


# ---------------------------------------------------------------------------
# Arithmetic / numeric
# ---------------------------------------------------------------------------


def test_bigint_arithmetic(tools: dict) -> None:
    r = _call(tools, "evaluate", expression="2**100 + 1")
    assert r["exact"] == "1267650600228229401496703205377"


def test_rational_no_float_drift(tools: dict) -> None:
    r = _call(tools, "evaluate", expression="1/3 + 1/7 + 1/11")
    assert r["exact"] == "131/231"


def test_evaluate_precision_floor_clamp(tools: dict) -> None:
    r = _call(tools, "evaluate", expression="pi", precision=0)
    assert r["decimal_digits"] == 1


def test_evaluate_precision_ceiling_clamp(tools: dict) -> None:
    r = _call(tools, "evaluate", expression="pi", precision=99999)
    assert r["decimal_digits"] == 10000


def test_evaluate_with_symbols_is_non_numeric(tools: dict) -> None:
    r = _call(tools, "evaluate", expression="x + x")
    assert r["exact"] == "2*x"
    assert "decimal" not in r


def test_pi_to_60_digits(tools: dict) -> None:
    r = _call(tools, "numeric", expression="pi", digits=60)
    assert r["exact"].startswith("3.14159265358979323846264338327950288419716939937510582097494")


def test_numeric_digits_upper_clamp(tools: dict) -> None:
    r = _call(tools, "numeric", expression="1", digits=1_000_000)
    assert r["decimal_digits"] == 100_000


# ---------------------------------------------------------------------------
# Algebra
# ---------------------------------------------------------------------------


def test_simplify(tools: dict) -> None:
    r = _call(tools, "simplify", expression="(x**2 - 1)/(x - 1)", symbols=["x"])
    assert r["exact"] == "x + 1"


def test_expand_cube(tools: dict) -> None:
    r = _call(tools, "expand", expression="(x+1)**3", symbols=["x"])
    assert r["exact"] == "x**3 + 3*x**2 + 3*x + 1"


def test_factor(tools: dict) -> None:
    r = _call(tools, "factor", expression="x**4 - 1", symbols=["x"])
    assert r["exact"] == "(x - 1)*(x + 1)*(x**2 + 1)"


def test_solve_real(tools: dict) -> None:
    r = _call(tools, "solve_equation", equation="x**2 - 2 = 0",
              variable="x", domain="real")
    assert set(r["solutions"]) == {"-sqrt(2)", "sqrt(2)"}


def test_solve_complex_domain(tools: dict) -> None:
    r = _call(tools, "solve_equation", equation="x**2 + 1 = 0", domain="complex")
    assert set(r["solutions"]) == {"-I", "I"}


def test_solve_integer_domain(tools: dict) -> None:
    r = _call(tools, "solve_equation", equation="x**2 - 4 = 0", domain="integer")
    assert set(r["solutions"]) == {"-2", "2"}


def test_solve_rational_domain(tools: dict) -> None:
    r = _call(tools, "solve_equation", equation="2*x - 1 = 0", domain="rational")
    assert r["solutions"] == ["1/2"]


def test_solve_equation_implicit_zero(tools: dict) -> None:
    """No '=' in the input → implied '= 0'."""
    r = _call(tools, "solve_equation", equation="x**2 - 9", domain="real")
    assert set(r["solutions"]) == {"-3", "3"}


def test_solve_equation_non_iterable_solution_set(tools: dict) -> None:
    """An unsolvable equation returns a ConditionSet whose list() raises TypeError.

    The except-branch should stringify the solution set instead.
    """
    r = _call(tools, "solve_equation", equation="x**x - 2 = 0",
              variable="x", domain="real")
    # as_list becomes None → `solutions` falls back to str(solveset output)
    assert isinstance(r["solutions"], str)
    assert "ConditionSet" in r["solutions"] or "x**x" in r["solutions"]


def test_solve_bad_domain_raises(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["solve_equation"](equation="x = 0", variable="x", domain="quaternion")


def test_solve_system(tools: dict) -> None:
    r = _call(tools, "solve_system",
              equations=["x + y = 3", "x - y = 1"], variables=["x", "y"])
    assert r["exact"] == [{"x": 2, "y": 1}]


def test_solve_system_implicit_zero(tools: dict) -> None:
    """Equation without '=' in a system."""
    r = _call(tools, "solve_system",
              equations=["x - 5"], variables=["x"])
    assert r["exact"] == [{"x": 5}]


# ---------------------------------------------------------------------------
# Calculus
# ---------------------------------------------------------------------------


def test_derivative(tools: dict) -> None:
    r = _call(tools, "differentiate", expression="sin(x)*exp(x)",
              variable="x", order=2)
    assert r["exact"] == "2*exp(x)*cos(x)"


def test_integral_definite_arctan(tools: dict) -> None:
    r = _call(tools, "integrate", expression="1/(1+x**2)",
              variable="x", lower="0", upper="1")
    assert r["exact"] == "pi/4"


def test_integral_indefinite(tools: dict) -> None:
    r = _call(tools, "integrate", expression="x**2", variable="x")
    assert r["exact"] == "x**3/3"


def test_integrate_partial_bounds_raises(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["integrate"](expression="x", variable="x", lower="0")


def test_limit_sinc(tools: dict) -> None:
    r = _call(tools, "limit", expression="sin(x)/x", variable="x", point="0")
    assert r["exact"] == "1"


def test_limit_right_direction(tools: dict) -> None:
    r = _call(tools, "limit", expression="1/x", variable="x", point="0", direction="+")
    assert r["exact"] == "oo"


def test_limit_left_direction(tools: dict) -> None:
    r = _call(tools, "limit", expression="1/x", variable="x", point="0", direction="-")
    assert r["exact"] == "-oo"


def test_limit_bad_direction_raises(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["limit"](expression="x", variable="x", point="0", direction="?")


def test_series_exp(tools: dict) -> None:
    r = _call(tools, "series", expression="exp(x)",
              variable="x", point="0", order=5)
    assert r["exact"] == "x**4/24 + x**3/6 + x**2/2 + x + 1"


def test_basel_problem(tools: dict) -> None:
    r = _call(tools, "summation", expression="1/n**2",
              index="n", lower="1", upper="oo")
    assert r["exact"] == "pi**2/6"


# ---------------------------------------------------------------------------
# Number theory
# ---------------------------------------------------------------------------


def test_gcd(tools: dict) -> None:
    r = _call(tools, "gcd", numbers=["462", "1071"])
    assert r["exact"] == "21"


def test_gcd_needs_two(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["gcd"](numbers=["5"])


def test_lcm_three(tools: dict) -> None:
    r = _call(tools, "lcm", numbers=["6", "8", "10"])
    assert r["exact"] == "120"


def test_lcm_needs_two(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["lcm"](numbers=["5"])


def test_factorint(tools: dict) -> None:
    r = _call(tools, "factorint", number="360")
    assert r["factors"] == {"2": 3, "3": 2, "5": 1}
    assert r["pretty"] == "2^3 * 3^2 * 5"


def test_mersenne_prime(tools: dict) -> None:
    r = _call(tools, "is_prime", number="2**521 - 1")
    assert r["exact"] is True


def test_nth_prime(tools: dict) -> None:
    r = _call(tools, "nth_prime", n=10)
    assert r["exact"] == 29


def test_next_prime(tools: dict) -> None:
    r = _call(tools, "next_prime", number="100")
    assert r["exact"] == 101


def test_mod_pow(tools: dict) -> None:
    r = _call(tools, "mod_pow", base="7", exponent="2**100",
              modulus="10**9+7")
    assert r["exact"] == 641087921


def test_mod_pow_zero_modulus_raises(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["mod_pow"](base="2", exponent="3", modulus="0")


def test_mod_inverse(tools: dict) -> None:
    r = _call(tools, "mod_inverse", a="3", modulus="11")
    assert r["exact"] == 4  # 3*4 = 12 ≡ 1 (mod 11)


# ---------------------------------------------------------------------------
# Linear algebra
# ---------------------------------------------------------------------------


def test_matrix_determinant(tools: dict) -> None:
    r = _call(tools, "matrix_determinant",
              matrix=[["1", "2"], ["3", "4"]])
    assert r["exact"] == "-2"


def test_matrix_inverse(tools: dict) -> None:
    r = _call(tools, "matrix_inverse",
              matrix=[["1", "2"], ["3", "4"]])
    assert r["data"] == [["-2", "1"], ["3/2", "-1/2"]]


def test_matrix_multiply(tools: dict) -> None:
    r = _call(tools, "matrix_multiply",
              a=[["1", "2"], ["3", "4"]],
              b=[["5", "6"], ["7", "8"]])
    assert r["data"] == [["19", "22"], ["43", "50"]]


def test_matrix_eigenvalues(tools: dict) -> None:
    r = _call(tools, "matrix_eigenvalues",
              matrix=[["2", "0"], ["0", "3"]])
    assert r["exact"] == {"2": 1, "3": 1}


def test_matrix_solve(tools: dict) -> None:
    r = _call(tools, "matrix_solve",
              a=[["1", "2"], ["3", "4"]],
              b=[["5"], ["11"]])
    assert r["data"] == [["1"], ["2"]]


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


def test_stats_exact(tools: dict) -> None:
    r = _call(tools, "stats",
              numbers=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])
    d = r["exact"]
    assert d["mean"] == "11/2"
    assert d["variance_sample"] == "55/6"


def test_stats_single_value_zero_variance(tools: dict) -> None:
    r = _call(tools, "stats", numbers=["7"])
    d = r["exact"]
    assert d["mean"] == "7"
    assert d["median"] == "7"
    assert d["variance_sample"] == "0"
    assert d["stdev_sample"] == "0"


def test_stats_odd_count_median(tools: dict) -> None:
    r = _call(tools, "stats", numbers=["1", "2", "3"])
    assert r["exact"]["median"] == "2"


def test_stats_empty_raises(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["stats"](numbers=[])


# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------


def test_to_rational(tools: dict) -> None:
    r = _call(tools, "to_rational", value="0.333333333333",
              max_denominator=1000)
    assert r["exact"] == "1/3"


def test_rejects_empty_expression(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["evaluate"](expression="")


# ---------------------------------------------------------------------------
# Defensive-branch coverage (monkeypatched failures)
# ---------------------------------------------------------------------------


def test_latex_failure_omits_latex_key(monkeypatch, tools: dict) -> None:
    def _boom(*a, **kw):
        raise RuntimeError("latex unavailable")
    monkeypatch.setattr(srv.sp, "latex", _boom)
    r = _call(tools, "evaluate", expression="2+2")
    assert r["exact"] == "4"
    assert "latex" not in r


def test_decimal_failure_captured_as_error(monkeypatch, tools: dict) -> None:
    def _boom(*a, **kw):
        raise RuntimeError("numeric unavailable")
    monkeypatch.setattr(srv.sp, "N", _boom)
    r = _call(tools, "evaluate", expression="pi", precision=10)
    assert "decimal_error" in r
    assert "numeric unavailable" in r["decimal_error"]


def test_evaluate_simplify_exception_fallback(monkeypatch, tools: dict) -> None:
    def _boom(*a, **kw):
        raise RuntimeError("simplify unavailable")
    monkeypatch.setattr(srv.sp, "simplify", _boom)
    # evaluate should fall back to the un-simplified value
    r = _call(tools, "evaluate", expression="2+2")
    assert r["exact"] == "4"


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def test_main_runs_mcp(monkeypatch) -> None:
    """Covers src/math_mcp/server.py::main and __main__.py."""
    calls = {"count": 0}

    def _fake_run(*_a, **_kw) -> None:
        calls["count"] += 1

    monkeypatch.setattr(srv.mcp, "run", _fake_run)
    # Direct call covers server.main()
    srv.main()
    # Module execution covers __main__.py
    runpy.run_module("math_mcp", run_name="__main__")
    assert calls["count"] == 2


def test_server_run_as_script(monkeypatch) -> None:
    """Covers the `if __name__ == '__main__': main()` branch in server.py."""
    from mcp.server.fastmcp import FastMCP
    monkeypatch.setattr(FastMCP, "run", lambda self, *a, **kw: None)
    runpy.run_path(srv.__file__, run_name="__main__")
