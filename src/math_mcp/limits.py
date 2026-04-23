"""Input-size limits that guard the math tools against pathological inputs.

These are defensive defaults intended for a shared / interactive MCP server.
Most real-world math questions fit comfortably inside them. Raise the caps
(by editing this module) only if callers are trusted and you have the CPU
budget for long symbolic computations.
"""

from __future__ import annotations

MAX_EXPR_LEN = 4096
"""Max character length of a parsed expression string."""

MAX_INTEGER_BITS = 4096
"""Max bit length of integers flowing into heavy ops (factorint, gcd, etc.).

4096 bits covers RSA-4096 key sizes. Factorization of such integers is
intractable, but we accept the input and let SymPy report what it can find
before the caller cancels. Smaller caps would reject legitimate uses."""

MAX_PRIMALITY_BITS = 8192
"""Primality testing uses deterministic tests below ~25 digits and BPSW
above, which remains fast well past our usual cap."""

MAX_MATRIX_DIM = 32
"""Max rows or columns for a matrix input. Determinant/inverse/eigenvalues
are super-linear in dim; 32 stays under a second for rational entries."""

MAX_NUMERIC_DIGITS = 10_000
"""Max significant digits for arbitrary-precision numeric evaluation.
10k digits of pi is about 10kB of text."""

MAX_SERIES_ORDER = 50
"""Max order of Taylor / Laurent series expansion."""

MAX_DIFF_ORDER = 20
"""Max order of differentiation."""

MAX_STATS_N = 100_000
"""Max size of a stats input list."""

MAX_COMBINATORIC_N = 10_000
"""Max n for binomial, permutations, combinations."""

MAX_NTH_PRIME_INDEX = 1_000_000
"""Max index for nth_prime (sieve-based generation scales with index)."""

MAX_BATCH_SIZE = 64
"""Max number of expressions in a single evaluate_batch call."""

MIN_BASE = 2
MAX_BASE = 36
"""Base range for to_base / from_base conversions (compatible with int())."""


def validate_expr_len(s: str, *, label: str = "expression") -> None:
    """Reject over-long expression strings before parsing."""
    if not isinstance(s, str):
        raise ValueError(f"{label} must be a string")
    if len(s) > MAX_EXPR_LEN:
        raise ValueError(
            f"{label} too long ({len(s)} chars; max {MAX_EXPR_LEN})"
        )


def validate_integer_bits(
    n: int, *, label: str = "integer", cap: int = MAX_INTEGER_BITS
) -> None:
    """Reject integers that exceed a configurable bit-length cap."""
    if n.bit_length() > cap:
        raise ValueError(
            f"{label} too large ({n.bit_length()} bits; max {cap})"
        )


def validate_matrix_dims(rows: int, cols: int) -> None:
    """Reject matrices that are empty, ragged-by-caller, or too large."""
    if rows < 1 or cols < 1:
        raise ValueError(
            f"matrix dimensions must be positive (got {rows}x{cols})"
        )
    if rows > MAX_MATRIX_DIM or cols > MAX_MATRIX_DIM:
        raise ValueError(
            f"matrix too large ({rows}x{cols}; max "
            f"{MAX_MATRIX_DIM}x{MAX_MATRIX_DIM})"
        )


def clamp_digits(digits: int) -> int:
    """Clamp numeric-evaluation digits to [1, MAX_NUMERIC_DIGITS]."""
    digits = int(digits)
    if digits < 1:
        return 1
    if digits > MAX_NUMERIC_DIGITS:
        return MAX_NUMERIC_DIGITS
    return digits


def validate_order(n: int, *, label: str, cap: int) -> int:
    """Require 0 <= n <= cap for series/differentiation orders."""
    n = int(n)
    if n < 0:
        raise ValueError(f"{label} must be non-negative (got {n})")
    if n > cap:
        raise ValueError(f"{label} too large ({n}; max {cap})")
    return n


def validate_combinatoric(n: int, k: int) -> tuple[int, int]:
    """Validate n and k for binomial / permutations / combinations."""
    n = int(n)
    k = int(k)
    if n < 0 or k < 0:
        raise ValueError(f"n and k must be non-negative (got n={n}, k={k})")
    if n > MAX_COMBINATORIC_N or k > MAX_COMBINATORIC_N:
        raise ValueError(
            f"n or k too large (got n={n}, k={k}; max {MAX_COMBINATORIC_N})"
        )
    return n, k


def validate_base(base: int) -> int:
    """Require 2 <= base <= 36."""
    base = int(base)
    if base < MIN_BASE or base > MAX_BASE:
        raise ValueError(
            f"base must be in [{MIN_BASE}, {MAX_BASE}] (got {base})"
        )
    return base


def validate_stats_n(n: int) -> None:
    if n > MAX_STATS_N:
        raise ValueError(
            f"stats input too large ({n}; max {MAX_STATS_N})"
        )


def validate_batch_size(n: int) -> None:
    """Reject empty or oversized expression batches."""
    if n < 1:
        raise ValueError("need at least one expression")
    if n > MAX_BATCH_SIZE:
        raise ValueError(
            f"batch too large ({n} expressions; max {MAX_BATCH_SIZE})"
        )
