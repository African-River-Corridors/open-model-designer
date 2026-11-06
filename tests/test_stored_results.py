"""Stored results (#13): a result the build computed sits on a Stored sheet, and a check says when it is stale."""

from __future__ import annotations

import openpyxl
import pytest

from omd import template
from omd.harness.readchecks import read_zero_checks
from omd.modules import debt_repay_linear
from omd.template import Step

# `opening_debt` stands in for a result the build computed (say, a sizing run); the other two are assumptions.
EXT = {"repayment_flag": [0.0, 1.0, 1.0, 1.0], "interest_rate": 0.05, "opening_debt": 900.0}


@pytest.fixture()
def built(tmp_path):
    step = Step(
        debt_repay_linear.MODULE, {p.name: f"ext:{p.name}" for p in debt_repay_linear.MODULE.inputs}
    )
    comp = template.compose([step], EXT, "Stored", stored=["opening_debt"])
    path = str(tmp_path / "s.xlsx")
    comp.save(path)
    return comp, path


def _failing(path):
    lines = []
    read_zero_checks(path, "Summary", min_rows=1, out=lambda s: lines.append(s))
    return [s for s in lines if s.lstrip().startswith("FAIL")]


def test_a_stored_result_is_on_its_own_sheet_and_read_through_the_mirror(built):
    comp, path = built
    ws = openpyxl.load_workbook(path)
    assert "Stored" in ws.sheetnames
    assert comp.ext_cells["opening_debt"] == ("Stored", "B5")
    assert all(ws["Inputs"].cell(row=r, column=1).value != "opening_debt" for r in range(1, 30))
    first = comp.wb.period_cols[0]
    assert ws["Calcs"][f"{first}{comp.mirror_rows['opening_debt']}"].value == "=Stored!$B$5"


def test_the_stale_check_reads_zero_until_an_input_changes(built, tmp_path):
    _comp, path = built
    assert _failing(path) == []
    for sheet, cell, value in (("Inputs", "B5", 0.0501), ("Feed", "D2", 0.0)):
        wb = openpyxl.load_workbook(path)
        assert wb[sheet][cell].value is not None
        wb[sheet][cell] = value
        moved = str(tmp_path / f"moved_{sheet}.xlsx")
        wb.save(moved)
        assert any("Stored results" in s for s in _failing(moved)), sheet


def test_the_model_still_follows_every_input_including_a_stored_one(built):
    comp, _path = built
    assert template.evaluate_and_compare(comp) == []
    assert template.inputs_drive_outputs(comp, EXT) == []


def test_only_scalar_inputs_can_be_stored():
    step = Step(
        debt_repay_linear.MODULE, {p.name: f"ext:{p.name}" for p in debt_repay_linear.MODULE.inputs}
    )
    with pytest.raises(ValueError, match="scalar external inputs"):
        template.compose([step], EXT, "Bad", stored=["repayment_flag"])
