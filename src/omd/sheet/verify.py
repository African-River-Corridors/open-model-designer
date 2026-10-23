"""Self-verification harness: evaluate the generated workbook's *live formulas* and assert
they reproduce a Python source-of-truth within tolerance.

This is what lets us trust *any* generated model: the workbook is not asserting hand-lifted
totals, it is recomputing them from its own SUMIFS / roll-forward / LOOKUP formulas, and we
check that result against the Python engine that built the spec. If a formula is wrong, verify
fails — the same guarantee a golden test gives, packaged for reuse.

Requires the ``formulas`` library (a dev/test dependency).
"""

from __future__ import annotations

import warnings
from collections.abc import Mapping, Sequence

warnings.filterwarnings("ignore")  # `formulas` emits cosmetic SyntaxWarnings on import


def evaluate(path: str) -> dict[str, float]:
    """Evaluate every scalar cell in ``path`` with the ``formulas`` lib.

    Returns a dict keyed by ``"SHEET'!REF"`` (upper-cased), e.g. ``"CALCS'!C10"``.
    """
    import formulas  # imported lazily so the builder has no hard dep on it

    sol = formulas.ExcelModel().loads(str(path)).finish().calculate()
    values: dict[str, float] = {}
    for k, v in sol.items():
        val = v.value if hasattr(v, "value") else v
        try:
            # keys look like "'[book.xlsx]CALCS'!C10"; index by the "SHEET'!REF" suffix.
            values[k.upper().split("]", 1)[1]] = float(val[0][0])
        except Exception:  # noqa: BLE001 — ranges / text cells aren't scalar; skip
            continue
    return values


def _cell(values: Mapping[str, float], sheet: str, ref: str) -> float | None:
    return values.get(f"{sheet.upper()}'!{ref}")


def verify(
    path: str,
    calcs,
    expected: Mapping[str, Sequence[float]],
    *,
    tol: float = 0.01,
) -> None:
    """Assert the workbook's evaluated Calcs formulas match ``expected`` per period.

    ``calcs`` is the :class:`~omd.sheet.workbook.Calcs` used to build it (it maps line
    keys to rows and knows the period columns). ``expected`` maps a line key to a sequence of
    expected period values (one per period, in order). Raises ``AssertionError`` on any drift.
    """
    verify_values(evaluate(path), calcs, expected, tol=tol)


def verify_values(
    values: Mapping[str, float],
    calcs,
    expected: Mapping[str, Sequence[float]],
    *,
    tol: float = 0.01,
) -> None:
    """`verify` on values already evaluated: one evaluation of a workbook can check any number of outputs."""
    rows = calcs.rows()
    period_cols = calcs.workbook.period_cols
    for key, wants in expected.items():
        if key not in rows:
            raise AssertionError(f"verify: line {key!r} not in Calcs")
        rr = rows[key]
        for i, (col, want) in enumerate(zip(period_cols, wants), start=1):
            got = _cell(values, calcs.name, f"{col}{rr}")
            if got is None:
                raise AssertionError(f"{key} p{i}: no evaluated value at {col}{rr}")
            if abs(got - want) > tol:
                raise AssertionError(
                    f"{key} p{i}: workbook {got:,.4f} vs source-of-truth {want:,.4f} (tol {tol})"
                )
