"""compose takes an assumption set (#26); audit_hardcodes treats the Stored sheet as guarded (#27)."""

from __future__ import annotations

import datetime as dt

import openpyxl

from omd import template
from omd.assumptions import Assumption, AssumptionSet
from omd.harness.audit_hardcodes import audit_hardcodes
from omd.modules import debt_repay_linear
from omd.template import Step

D = dt.date(2026, 11, 8)
ASET = AssumptionSet(
    items={
        "interest_rate": Assumption("interest_rate", 0.05, "ratio", "Interest rate", "Lender term sheet", D, "analyst", False),
        "opening_debt": Assumption("opening_debt", 900.0, "USD", "Opening debt", "Sizing note", D, "analyst", True),
    }
)  # fmt: skip
STEP = Step(
    debt_repay_linear.MODULE, {p.name: f"ext:{p.name}" for p in debt_repay_linear.MODULE.inputs}
)
FLAGS = {"repayment_flag": [0.0, 1.0, 1.0, 1.0]}


def test_inputs_held_by_the_set_carry_their_provenance(tmp_path):
    comp = template.compose([STEP], FLAGS, "Assumed", assumptions=ASET)
    path = str(tmp_path / "a.xlsx")
    comp.save(path)
    ws = openpyxl.load_workbook(path)["Inputs"]
    sheet, cell = comp.ext_cells["opening_debt"]
    r = int(cell[1:])
    row = [ws.cell(row=r, column=j).value for j in range(1, 8)]
    assert row == [
        "Opening debt (USD)",
        900,
        "USD",
        "Sizing note",
        "2026-11-08",
        "analyst",
        "ESTIMATE",
    ]
    assert [ws.cell(row=3, column=j).value for j in range(2, 8)] == [
        "Value",
        "Unit",
        "Source",
        "Date",
        "Who",
        "Flag",
    ]
    assert template.evaluate_and_compare(comp) == []
    assert template.inputs_drive_outputs(comp, {**ASET.values(), **FLAGS}) == []


def test_the_external_dict_overrides_the_set(tmp_path):
    comp = template.compose([STEP], {**FLAGS, "interest_rate": 0.07}, "Override", assumptions=ASET)
    assert comp.expected["debt_repay_linear"]["interest"][0] == 900.0 * 0.07
    path = str(tmp_path / "o.xlsx")
    comp.save(path)
    ws = openpyxl.load_workbook(path)["Inputs"]
    sheet, cell = comp.ext_cells["interest_rate"]
    assert ws[cell].value == 0.07
    r = int(cell[1:])
    # the set's source, date and who describe the set's value, not the override
    assert [ws.cell(row=r, column=j).value for j in (4, 5, 6)] == ["override: external", None, None]
    kept = int(comp.ext_cells["opening_debt"][1][1:])
    assert ws.cell(row=kept, column=4).value == "Sizing note"
    assert template.evaluate_and_compare(comp) == []


def test_the_stored_sheet_is_guarded_not_a_finding(tmp_path):
    comp = template.compose([STEP], {**ASET.values(), **FLAGS}, "Stored", stored=["opening_debt"])
    path = str(tmp_path / "s.xlsx")
    comp.save(path)
    seen = []
    assert audit_hardcodes(path, out=seen.append) == []
    assert any("Stored holds" in s and "guarded" in s for s in seen)
    assert (
        audit_hardcodes(path, stored_sheets=()) != []
    )  # without the guard, its numbers are findings


def _stored_workbook(tmp_path):
    comp = template.compose([STEP], {**ASET.values(), **FLAGS}, "Stored", stored=["opening_debt"])
    path = str(tmp_path / "t.xlsx")
    comp.save(path)
    return path


def test_a_number_typed_on_a_row_the_stale_check_does_not_cover_is_a_finding(tmp_path):
    path = _stored_workbook(tmp_path)
    wb = openpyxl.load_workbook(path)
    ws = wb["Stored"]
    r = ws.max_row + 2  # below the stored rows: no change flag
    ws.cell(row=r, column=1, value="Reviewer note")
    ws.cell(row=r, column=3, value=12345)
    ws.cell(row=r + 1, column=1, value="Reviewer rate")
    ws.cell(row=r + 1, column=3, value="=0.153")
    # a number in an uncovered column of a covered row is also a finding
    ws.cell(row=6, column=5, value=777)
    wb.save(path)
    found = audit_hardcodes(path)
    assert len(found) == 3
    assert any(f"C{r} " in f and "12345" in f for f in found)
    assert any("0.153" in f for f in found)
    assert any("E6 " in f and "777" in f for f in found)
