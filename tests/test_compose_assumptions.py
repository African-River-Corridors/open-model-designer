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


def test_the_external_dict_overrides_the_set():
    comp = template.compose([STEP], {**FLAGS, "interest_rate": 0.07}, "Override", assumptions=ASET)
    assert comp.expected["debt_repay_linear"]["interest"][0] == 900.0 * 0.07


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
