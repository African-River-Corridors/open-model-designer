"""omd.solve (#35): a bisection that is exact and repeatable, a solved input, and a live check."""

from __future__ import annotations

import pytest

from omd.harness._eval import evaluate_cells
from omd.sheet import formatting as F
from omd.sheet.workbook import Workbook
from omd.solve import Solve, bisect_threshold, solve_check, solved_input

TOL = 1e-6
# Root of f(x) = 100/x - 40 at the tolerance: 100/x = 40 + TOL, worked by hand (docs/golden-cases/solve.md).
ROOT = 100 / (40 + TOL)


def f(x: float) -> float:
    return 100 / x - 40


# ---- the algorithm, step by step ----------------------------------------------------------------
def test_no_growth_when_the_bracket_holds_the_threshold():
    s = bisect_threshold(f, lo=1.0, hi=4.0, tol=TOL, steps=60)
    assert (s.value, s.hi) == (pytest.approx(ROOT, abs=1e-12), s.value)
    assert s.lo < ROOT <= s.hi or s.lo == pytest.approx(ROOT, abs=1e-12)
    assert s.steps == 60
    assert s.evaluations == 1 + 1 + 60 + 1  # f(hi), f(lo), the halvings, the final residual
    assert s.residual == f(s.hi) <= TOL


def test_hi_grows_and_lo_follows_the_old_hi():
    seen = []

    def traced(x):
        seen.append(x)
        return f(x)

    s = bisect_threshold(traced, lo=0.5, hi=1.0, tol=TOL, steps=0)
    # f(1)=60 and f(2)=10 are above tol, so the bracket moves twice: (1,2) then (2,4). Then f(lo=2), no halvings, f(hi=4).
    assert seen == [1.0, 2.0, 4.0, 2.0, 4.0]
    assert (s.lo, s.hi, s.value) == (2.0, 4.0, 4.0)
    assert s.evaluations == 5


def test_growth_case_finds_the_same_root():
    s = bisect_threshold(f, lo=0.5, hi=1.0, tol=TOL, steps=60)
    assert s.value == pytest.approx(ROOT, abs=1e-12)
    assert s.evaluations == 3 + 1 + 60 + 1


def test_a_custom_grow():
    seen = []

    def traced(x):
        seen.append(x)
        return f(x)

    bisect_threshold(traced, lo=0.5, hi=1.0, tol=TOL, steps=0, grow=4.0)
    # f(1) > tol, so lo, hi = 1, 4; f(4) <= tol; then f(lo=1) and the final f(hi=4).
    assert seen == [1.0, 4.0, 1.0, 4.0]


def test_no_early_exit_even_if_a_midpoint_is_exact():
    # f is a step: every point at or above 3 is exactly 0. All 60 halvings still run.
    calls = []

    def step(x):
        calls.append(x)
        return 0.0 if x >= 3.0 else 1.0

    s = bisect_threshold(step, lo=1.0, hi=5.0, tol=0.0, steps=60)
    assert s.value == 3.0
    assert len(calls) == s.evaluations == 1 + 1 + 60 + 1


def test_raises_when_hi_reaches_the_cap():
    with pytest.raises(ValueError, match="cap"):
        bisect_threshold(lambda x: 1.0, lo=1.0, hi=2.0, tol=TOL, steps=60, cap=64.0)


def test_raises_when_the_low_end_already_meets_the_target():
    with pytest.raises(ValueError, match="bracket"):
        bisect_threshold(f, lo=3.0, hi=4.0, tol=TOL, steps=60)


def test_two_runs_give_identical_floats():
    a = bisect_threshold(f, lo=0.5, hi=2.0, tol=TOL, steps=60)
    b = bisect_threshold(f, lo=0.5, hi=2.0, tol=TOL, steps=60)
    assert a == b
    assert a.value.hex() == b.value.hex()


def test_the_result_is_a_solve():
    assert isinstance(bisect_threshold(f, lo=1.0, hi=4.0, tol=TOL, steps=4), Solve)


# ---- the workbook helpers -----------------------------------------------------------------------
def _book(tmp_path, demand=100.0):
    """A one-input model: residual = demand / tariff - 40, solved for the tariff."""
    wb = Workbook("Solve", ["P1", "P2"])
    ref = wb.inputs("Assumptions", {"demand": ("Demand", demand)})["demand"]
    s = bisect_threshold(lambda x: demand / x - 40, lo=1.0, hi=4.0, tol=TOL, steps=60)
    tariff = solved_input(wb, "tariff_mult", "Tariff multiplier", s, fmt=F.RATE)
    calcs = wb.calcs()
    solve_check(calcs, "tariff_check", "Tariff solve still holds", f"={ref}/{tariff}-40", tol=TOL)
    path = str(tmp_path / "solve.xlsx")
    wb.save(path)
    return wb, calcs, s, tariff, path


def _check(path, calcs):
    got = evaluate_cells(path)
    row = calcs.rows()["tariff_check"]
    return [got[f"CALCS'!{c}{row}"] for c in ("B", "C")]


def test_solved_input_is_a_marked_input_cell(tmp_path):
    import openpyxl

    wb, _calcs, s, tariff, path = _book(tmp_path)
    assert wb.inputs_sheet is not None
    ws = openpyxl.load_workbook(path)["Inputs"]
    sheet, ref = tariff.split("!")
    assert sheet == "Inputs"
    assert ws[ref.replace("$", "")].value == s.value
    labels = [ws.cell(row=r, column=1).value for r in range(1, ws.max_row + 1)]
    assert "Solved values" in labels
    label = ws.cell(row=ws[ref.replace("$", "")].row, column=1).value
    assert label == "Tariff multiplier [SOLVED by the build — rebuild, do not edit]"


def test_the_check_reads_zero_then_one_when_an_input_moves(tmp_path):
    import openpyxl

    _wb, calcs, _s, _tariff, path = _book(tmp_path)
    assert _check(path, calcs) == [0.0, 0.0]
    book = openpyxl.load_workbook(path)
    book["Inputs"]["B5"] = 101.0  # the demand the tariff was solved for
    moved = str(tmp_path / "moved.xlsx")
    book.save(moved)
    assert _check(moved, calcs) == [1.0, 1.0]


def test_a_callable_residual_gets_the_column_context(tmp_path):
    wb = Workbook("Solve", ["P1", "P2"])
    ref = wb.inputs("Assumptions", {"x": ("X", 5.0)})["x"]
    calcs = wb.calcs()
    solve_check(calcs, "chk", "Check", lambda c: f"={ref}-5+0*ROW({c.col}1)", tol=TOL)
    path = str(tmp_path / "c.xlsx")
    wb.save(path)
    got = evaluate_cells(path)
    row = calcs.rows()["chk"]
    assert got[f"CALCS'!B{row}"] == got[f"CALCS'!C{row}"] == 0.0
