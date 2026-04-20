"""Correctness tests: each case compares the tool output to a known-exact value."""

from __future__ import annotations

import json

import pytest

from math_mcp.server import mcp


@pytest.fixture(scope="module")
def tools() -> dict:
    return {t.name: t.fn for t in mcp._tool_manager._tools.values()}


def _call(tools: dict, name: str, **kwargs):
    return json.loads(tools[name](**kwargs))


def test_registered_tool_count(tools: dict) -> None:
    assert len(tools) == 27


def test_bigint_arithmetic(tools: dict) -> None:
    r = _call(tools, "evaluate", expression="2**100 + 1")
    assert r["exact"] == "1267650600228229401496703205377"


def test_rational_no_float_drift(tools: dict) -> None:
    r = _call(tools, "evaluate", expression="1/3 + 1/7 + 1/11")
    assert r["exact"] == "131/231"


def test_pi_to_60_digits(tools: dict) -> None:
    r = _call(tools, "numeric", expression="pi", digits=60)
    assert r["exact"].startswith("3.14159265358979323846264338327950288419716939937510582097494")


def test_simplify(tools: dict) -> None:
    r = _call(tools, "simplify", expression="(x**2 - 1)/(x - 1)", symbols=["x"])
    assert r["exact"] == "x + 1"


def test_factor(tools: dict) -> None:
    r = _call(tools, "factor", expression="x**4 - 1", symbols=["x"])
    assert r["exact"] == "(x - 1)*(x + 1)*(x**2 + 1)"


def test_solve_real(tools: dict) -> None:
    r = _call(tools, "solve_equation", equation="x**2 - 2 = 0",
              variable="x", domain="real")
    assert set(r["solutions"]) == {"-sqrt(2)", "sqrt(2)"}


def test_solve_system(tools: dict) -> None:
    r = _call(tools, "solve_system",
              equations=["x + y = 3", "x - y = 1"], variables=["x", "y"])
    assert r["exact"] == [{"x": 2, "y": 1}]


def test_derivative(tools: dict) -> None:
    r = _call(tools, "differentiate", expression="sin(x)*exp(x)",
              variable="x", order=2)
    assert r["exact"] == "2*exp(x)*cos(x)"


def test_integral_arctan(tools: dict) -> None:
    r = _call(tools, "integrate", expression="1/(1+x**2)",
              variable="x", lower="0", upper="1")
    assert r["exact"] == "pi/4"


def test_limit_sinc(tools: dict) -> None:
    r = _call(tools, "limit", expression="sin(x)/x", variable="x", point="0")
    assert r["exact"] == "1"


def test_basel_problem(tools: dict) -> None:
    r = _call(tools, "summation", expression="1/n**2",
              index="n", lower="1", upper="oo")
    assert r["exact"] == "pi**2/6"


def test_gcd(tools: dict) -> None:
    r = _call(tools, "gcd", numbers=["462", "1071"])
    assert r["exact"] == "21"


def test_mersenne_prime(tools: dict) -> None:
    r = _call(tools, "is_prime", number="2**521 - 1")
    assert r["exact"] is True


def test_mod_pow(tools: dict) -> None:
    r = _call(tools, "mod_pow", base="7", exponent="2**100",
              modulus="10**9+7")
    assert r["exact"] == 641087921


def test_matrix_determinant(tools: dict) -> None:
    r = _call(tools, "matrix_determinant",
              matrix=[["1", "2"], ["3", "4"]])
    assert r["exact"] == "-2"


def test_matrix_inverse(tools: dict) -> None:
    r = _call(tools, "matrix_inverse",
              matrix=[["1", "2"], ["3", "4"]])
    assert r["data"] == [["-2", "1"], ["3/2", "-1/2"]]


def test_matrix_eigenvalues(tools: dict) -> None:
    r = _call(tools, "matrix_eigenvalues",
              matrix=[["2", "0"], ["0", "3"]])
    assert r["exact"] == {"2": 1, "3": 1}


def test_stats_exact(tools: dict) -> None:
    r = _call(tools, "stats",
              numbers=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"])
    d = r["exact"]
    assert d["mean"] == "11/2"
    assert d["variance_sample"] == "55/6"


def test_to_rational(tools: dict) -> None:
    r = _call(tools, "to_rational", value="0.333333333333",
              max_denominator=1000)
    assert r["exact"] == "1/3"


def test_rejects_empty_expression(tools: dict) -> None:
    with pytest.raises(ValueError):
        tools["evaluate"](expression="")
