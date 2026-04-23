"""Pydantic response models returned by the math-mcp tools.

Every tool returns one of these models rather than a free-form JSON string.
FastMCP exposes them as structured tool results with a generated JSON schema,
so MCP clients (and LLMs driving them) know the exact shape to expect.

Conventions:
- `exact` is always the canonical symbolic or rational form as a string.
- `decimal` is an optional arbitrary-precision decimal approximation.
- `latex` is an optional LaTeX rendering for display.
- `parsed` echoes how the input was parsed, so the caller can audit.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Base(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ExactResult(_Base):
    """A single exact (symbolic, rational, or integer) scalar result."""

    exact: str = Field(
        description=(
            "Canonical exact form — integer literal, p/q rational, or "
            "symbolic expression. Always present."
        )
    )
    latex: str | None = Field(
        default=None, description="LaTeX rendering of the exact form."
    )
    decimal: str | None = Field(
        default=None,
        description="Decimal approximation (present for numeric results).",
    )
    decimal_digits: int | None = Field(
        default=None,
        description="Significant digits used for the decimal approximation.",
    )
    decimal_error: str | None = Field(
        default=None,
        description="Error message if decimal evaluation failed.",
    )
    parsed: str | None = Field(
        default=None,
        description="How the input was parsed (audit echo).",
    )


class IntegerResult(_Base):
    """A pure-integer result (arbitrary size).

    `value` is a decimal-digit string rather than a raw int so the full
    precision survives JSON transport — MCP clients that parse numbers as
    IEEE-754 float64 would otherwise silently truncate integers above 2**53.
    """

    value: str = Field(
        description=(
            "Exact integer as a decimal-digit string. Convert with int(value) "
            "if you need arithmetic."
        )
    )
    latex: str | None = None
    context: dict[str, str] | None = Field(
        default=None,
        description=(
            "Named inputs that produced this result (e.g. "
            "{'base': '7', 'exponent': '...', 'modulus': '...'})."
        ),
    )


class BooleanResult(_Base):
    """A yes/no predicate result."""

    value: bool
    subject: str = Field(
        description="Stringified input the predicate was applied to."
    )


class RationalResult(_Base):
    """A rational (p/q) result with optional decimal and original-exact form."""

    rational: str = Field(description="p/q form as a string.")
    numer: str = Field(description="Numerator as a decimal-digit string (int-safe).")
    denom: str = Field(description="Denominator as a decimal-digit string (int-safe).")
    decimal: str | None = None
    exact_rational: str | None = Field(
        default=None,
        description=(
            "Unbounded exact rational before limit_denominator truncation, "
            "if applicable."
        ),
    )


class MatrixResult(_Base):
    """A matrix-valued result."""

    rows: int
    cols: int
    data: list[list[str]] = Field(
        description="Row-major cell values as strings (exact)."
    )
    latex: str | None = None


class SolutionSet(_Base):
    """Solutions to a single-variable equation."""

    equation: str
    domain: str
    solutions: list[str] | None = Field(
        default=None,
        description=(
            "Exact solutions as strings; null when the solution set is not "
            "enumerable (e.g. ConditionSet for equations SymPy could not solve)."
        ),
    )
    set_repr: str = Field(
        description=(
            "String repr of the full solution set — FiniteSet, Interval, "
            "Union, ImageSet, or ConditionSet."
        )
    )
    latex: str | None = None


class SystemSolution(_Base):
    """Solutions to a system of equations."""

    equations: list[str]
    solutions: list[dict[str, str]] = Field(
        description="List of variable -> value maps (each a solution)."
    )


class Factorization(_Base):
    """Prime factorization of a positive integer."""

    number: str
    factors: dict[str, int] = Field(description="prime -> exponent mapping.")
    pretty: str = Field(
        description="Human-readable factorization like '2^3 * 3^2 * 5'."
    )
    distinct_primes: int


class Stats(_Base):
    """Descriptive statistics for a list of numbers."""

    count: int
    mean: str
    median: str
    variance_sample: str
    stdev_sample: str
    min: str
    max: str
    decimal: dict[str, str] | None = Field(
        default=None,
        description=(
            "Numeric approximations (~30 digits) of mean/variance/stdev "
            "for convenience."
        ),
    )


class IntervalResult(_Base):
    """Result of an inequality solve — a set of intervals."""

    inequality: str
    variable: str
    solution_set: str = Field(
        description=(
            "String repr of the solution set: Interval, Union of intervals, "
            "EmptySet, or Reals."
        )
    )
    latex: str | None = None


class Eigenvalues(_Base):
    """Eigenvalues of a matrix with algebraic multiplicities."""

    dim: int
    eigenvalues: dict[str, int] = Field(
        description="eigenvalue -> algebraic multiplicity."
    )
    latex: str | None = None


class Roots(_Base):
    """Exact roots of a polynomial with multiplicities."""

    polynomial: str
    variable: str
    roots: list[str]
    multiplicities: dict[str, int] = Field(
        description="root -> multiplicity."
    )


class NumericRoots(_Base):
    """Numerical (floating-point) roots of an expression."""

    expression: str
    variable: str
    roots: list[str] = Field(description="Numeric roots as decimal strings.")
    digits: int


class CombinatoricResult(_Base):
    """Result of a combinatoric operation.

    `value` is a decimal-digit string to preserve precision across JSON
    transport (binomial coefficients grow very fast — C(200, 100) is 59 digits).
    """

    operation: str = Field(
        description='"binomial" | "permutations" | "combinations".'
    )
    n: int
    k: int
    value: str = Field(
        description="Exact value as a decimal-digit string."
    )


class BaseConversionResult(_Base):
    """Result of an integer base conversion."""

    input: str
    decimal_value: str = Field(
        description="Integer value in base 10 as a decimal-digit string."
    )
    base_from: int
    base_to: int
    digits: str = Field(
        description="Integer representation in the target base."
    )


class BatchItem(_Base):
    """One entry inside a BatchResult — success or per-item error.

    A single bad expression must not void an entire batch, so failures are
    reported per-item (`error` set, `exact` null) rather than raised.
    """

    expression: str = Field(description="The input expression for this slot.")
    exact: str | None = Field(
        default=None,
        description="Canonical exact form (null if this item errored).",
    )
    latex: str | None = None
    decimal: str | None = None
    decimal_digits: int | None = None
    decimal_error: str | None = None
    parsed: str | None = None
    error: str | None = Field(
        default=None,
        description=(
            "Error message for this item if parsing/evaluation failed; null "
            "on success. Inspect this field before reading `exact`."
        ),
    )


class BatchResult(_Base):
    """Aligned results for an evaluate_batch call.

    `items[i]` corresponds to the i-th input expression. The ordering is
    preserved, so callers can drop results straight into tabular cells.
    """

    count: int = Field(description="Number of items in the batch (== len(items)).")
    items: list[BatchItem]


class UnitConversion(_Base):
    """Result of a physical-unit conversion (SymPy units)."""

    value: str
    source_unit: str
    target_unit: str
    converted: str = Field(
        description="Exact converted value, often with a rational prefactor."
    )
    decimal: str | None = Field(
        default=None,
        description="Decimal approximation of the conversion factor.",
    )
