"""compose takes a sheet set (#36): a composed book keeps its own sheet names and order, and every gate still runs."""

from __future__ import annotations

import openpyxl
import pytest

from omd import template
from omd.harness._eval import cell, evaluate_cells
from omd.harness.readchecks import read_zero_checks
from omd.modules import debt_repay_linear
from omd.sheet import SheetSet
from omd.template import Step

# `opening_debt` stands in for a result the build computed, so the book has a Stored sheet and a stale check.
EXT = {"repayment_flag": [0.0, 1.0, 1.0, 1.0], "interest_rate": 0.05, "opening_debt": 900.0}
SHEETS = SheetSet(
    [
        ("Summary", "Checks"),
        ("Inputs", "Key inputs"),
        ("Feed", "Series"),
        ("Stored", "Stored results"),
        ("Calcs", "Workings"),
    ]
)


def _compose(**kw):
    step = Step(
        debt_repay_linear.MODULE, {p.name: f"ext:{p.name}" for p in debt_repay_linear.MODULE.inputs}
    )
    return template.compose([step], EXT, "Renamed", stored=["opening_debt"], **kw)


def _failing(path, sheet):
    lines = []
    read_zero_checks(path, sheet, min_rows=1, out=lines.append)
    return [s for s in lines if s.lstrip().startswith("FAIL")]


@pytest.fixture()
def renamed(tmp_path):
    comp = _compose(sheets=SHEETS)
    path = str(tmp_path / "renamed.xlsx")
    comp.save(path)
    return comp, path


def test_no_set_gives_todays_book_cell_for_cell():
    plain, none = _compose(), _compose(sheets=None)
    assert plain.wb.cells() == none.wb.cells()
    assert plain.wb.sheet_names == none.wb.sheet_names
    assert plain.sheet("Calcs") == "Calcs"


def test_the_set_names_and_orders_the_sheets(renamed):
    comp, path = renamed
    assert openpyxl.load_workbook(path).sheetnames == SHEETS.order
    assert comp.calcs.name == comp.sheet("Calcs") == "Workings"
    assert comp.sheet("Summary") == "Checks"
    assert comp.ext_cells["opening_debt"][0] == "Stored results"


def test_the_renamed_book_evaluates_to_the_same_numbers(renamed, tmp_path):
    comp, path = renamed
    plain = _compose()
    plain_path = str(tmp_path / "plain.xlsx")
    plain.save(plain_path)
    up = {o.upper(): n.upper() for o, n in SHEETS.names.items()}
    before = {
        (up[k.rsplit("'!", 1)[0]], k.rsplit("'!", 1)[1]): v
        for k, v in evaluate_cells(plain_path).items()
        if isinstance(v, float)
    }
    after = {
        tuple(k.rsplit("'!", 1)): v for k, v in evaluate_cells(path).items() if isinstance(v, float)
    }
    assert before and after == before


def test_every_gate_passes_on_the_renamed_book(renamed):
    comp, path = renamed
    assert _failing(path, comp.sheet("Summary")) == []
    assert template.evaluate_and_compare(comp) == []
    assert template.corruption_audit(comp) == []
    assert template.inputs_drive_outputs(comp, EXT) == []


def test_the_stale_check_still_fires_after_a_rename(renamed, tmp_path):
    comp, path = renamed
    sheet, where = comp.ext_cells["interest_rate"]
    assert sheet == "Key inputs"
    wb = openpyxl.load_workbook(path)
    wb[sheet][where] = 0.0501
    moved = str(tmp_path / "moved.xlsx")
    wb.save(moved)
    assert any("Stored results" in s for s in _failing(moved, comp.sheet("Summary")))


def test_key_figures_added_after_the_rename_read_the_renamed_calcs(renamed, tmp_path):
    comp, _path = renamed
    comp.wb.key_figures("Key figures", [("Peak debt", "debt_repay_linear.debt_closing", "max")])
    path = str(tmp_path / "kf.xlsx")
    comp.save(path)
    formulas = [
        c.value for row in openpyxl.load_workbook(path)["Key figures"].iter_rows() for c in row
    ]
    assert any(isinstance(f, str) and "Workings!" in f for f in formulas)
    values = evaluate_cells(path)
    got = [v for k, v in values.items() if k.startswith("KEY FIGURES'!") and isinstance(v, float)]
    assert 900.0 in got
    assert (
        cell(
            values,
            "Workings",
            f"{comp.wb.period_cols[0]}{comp.calcs.row_of('debt_repay_linear.debt_closing')}",
        )
        is not None
    )
