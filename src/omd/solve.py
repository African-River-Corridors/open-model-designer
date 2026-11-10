"""A solved value: the build sets an input so a target holds, and a live check says when it needs solving again.

Engine core, not a library module. The algorithm is fixed and has no early exit, so a model moved onto it gets the
same bits it had before. See docs/design/extra-sheets-sheet-sets-solver.md, section 4.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from omd.sheet import formatting as F
from omd.sheet.workbook import Calcs, Workbook, _Ctx

SOLVED_MARK = "[SOLVED by the build — rebuild, do not edit]"


@dataclass(frozen=True)
class Solve:
    """What `bisect_threshold` found. `value` is the `hi` side of the final bracket."""

    value: float
    lo: float
    hi: float
    residual: float
    steps: int
    evaluations: int


def bisect_threshold(
    f: Callable[[float], float],
    *,
    lo: float,
    hi: float,
    tol: float,
    steps: int,
    grow: float = 2.0,
    cap: float = 64.0,
) -> Solve:
    """The smallest x found with `f(x) <= tol`, for an `f` that does not increase with x.

    1. While `f(hi) > tol`: `lo, hi = hi, hi * grow`; raise if `hi >= cap`.
    2. Raise if `f(lo) <= tol` (the bracket does not hold the threshold).
    3. Halve `steps` times with no early exit: `mid = (lo + hi) / 2`; `lo = mid` if `f(mid) > tol`, else `hi = mid`.
    4. `value = hi`; `residual = f(hi)`.
    """
    evaluations = 0

    def call(x: float) -> float:
        nonlocal evaluations
        evaluations += 1
        return f(x)

    while call(hi) > tol:
        lo, hi = hi, hi * grow
        if hi >= cap:
            raise ValueError(f"no solution below the cap {cap}: f is still above {tol} at hi={hi}")
    if call(lo) <= tol:
        raise ValueError(f"the bracket does not hold the threshold: f(lo={lo}) is already <= {tol}")
    for _ in range(steps):
        mid = (lo + hi) / 2
        if call(mid) > tol:
            lo = mid
        else:
            hi = mid
    residual = call(hi)
    return Solve(hi, lo, hi, residual, steps, evaluations)


def solved_input(wb: Workbook, name: str, label: str, solve: Solve, *, fmt: str = F.NUM) -> str:
    """Write the solved value as an input cell under "Solved values", marked so a reader does not edit it.

    Returns the cell reference (for example `Inputs!$B$9`).
    """
    return wb.inputs("Solved values", {name: (f"{label} {SOLVED_MARK}", solve.value, fmt)})[name]


def solve_check(
    calcs: Calcs,
    key: str,
    label: str,
    residual_formula: str | Callable[[_Ctx], str],
    *,
    tol: float,
) -> str:
    """A Calcs check row: 0 when `ABS(residual) <= tol`, 1 when it is not (rebuild to solve again).

    `residual_formula` is a formula string, the same in every column, or a callable `ctx -> str`.
    A leading `=` is allowed.
    """

    def formula(c: _Ctx) -> str:
        raw = residual_formula(c) if callable(residual_formula) else residual_formula
        return f"=IF(ABS({raw.removeprefix('=')})<={tol!r},0,1)"

    return calcs.row(key, label, formula, fmt=F.NUM)
