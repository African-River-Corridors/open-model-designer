"""Low, base and high inputs side by side (#25): a case grid with a live column, picks, and a selector-proof stale check."""

from __future__ import annotations

import openpyxl
import pytest

from omd import template
from omd.harness._eval import evaluate_cells
from omd.harness.readchecks import read_zero_checks
from omd.modules import debt_repay_linear
from omd.style import audit_style
from omd.template import CaseGrid, Step

GRID = CaseGrid(
    "Cases",
    "case",
    ("Low", "Base", "High"),
    (("Interest rate", ("rate_low", "rate_base", "rate_high"), "interest_rate"),),
)
EXT = {
    "repayment_flag": [0.0, 1.0, 1.0, 1.0],
    "opening_debt": 900.0,
    "case": 2.0,
    "rate_low": 0.04,
    "rate_base": 0.05,
    "rate_high": 0.07,
}


@pytest.fixture()
def built(tmp_path):
    step = Step(
        debt_repay_linear.MODULE, {p.name: f"ext:{p.name}" for p in debt_repay_linear.MODULE.inputs}
    )
    comp = template.compose([step], EXT, "Grid", grids=[GRID], stored=["opening_debt"])
    path = str(tmp_path / "g.xlsx")
    comp.save(path)
    return comp, path


def _grid_rows(ws):
    hdr = next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=2).value == "Live")
    return hdr, [ws.cell(row=hdr + 1, column=j).value for j in range(1, 7)]


def test_the_cases_sit_side_by_side_with_a_live_column(built):
    _comp, path = built
    ws = openpyxl.load_workbook(path)["Inputs"]
    hdr, row = _grid_rows(ws)
    assert [ws.cell(row=hdr, column=j).value for j in range(2, 7)] == [
        "Live",
        "Low",
        "Base",
        "High",
        "Unit",
    ]
    assert (
        row[0] == "Interest rate"
        and row[1].startswith("=CHOOSE(")
        and row[2:5] == [0.04, 0.05, 0.07]
    )
    assert evaluate_cells(path, ("Inputs",))[f"INPUTS'!B{hdr + 1}"] == pytest.approx(0.05)
    assert audit_style(path) == []


def test_the_model_reads_the_live_case_and_follows_the_selector(built, tmp_path):
    comp, path = built
    assert template.evaluate_and_compare(comp) == []
    assert template.inputs_drive_outputs(comp, EXT) == []
    sheet, cell = comp.ext_cells["case"]
    wb = openpyxl.load_workbook(path)
    wb[sheet][cell] = 3
    moved = str(tmp_path / "high.xlsx")
    wb.save(moved)
    want = template.chained_oracle(comp.steps, comp.derive({**EXT, "case": 3.0}))
    row = comp.calcs.rows()["debt_repay_linear.interest"]
    col = comp.wb.period_cols[1]
    got = evaluate_cells(moved, ("Calcs",))[f"CALCS'!{col}{row}"]
    assert got == pytest.approx(want["debt_repay_linear"]["interest"][1])
    assert got == pytest.approx(900.0 * 0.07)


def test_the_selector_does_not_trip_the_stale_check_but_a_case_does(built, tmp_path):
    comp, path = built

    def failing(edit):
        wb = openpyxl.load_workbook(path)
        sheet, cell = comp.ext_cells[edit[0]]
        wb[sheet][cell] = edit[1]
        p = str(tmp_path / f"{edit[0]}.xlsx")
        wb.save(p)
        lines = []
        read_zero_checks(p, "Summary", min_rows=1, out=lines.append)
        return [s for s in lines if "FAIL" in s and "Stored results" in s]

    assert failing(("case", 3)) == []
    assert failing(("rate_high", 0.08))


def test_a_grid_row_needs_one_input_per_case():
    with pytest.raises(ValueError, match="2 inputs for 3 cases"):
        CaseGrid("Bad", "case", ("Low", "Base", "High"), (("Rate", ("a", "b"), None),))
