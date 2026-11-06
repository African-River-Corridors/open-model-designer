"""Inputs mirrored at the top of Calcs (#11): modules read the mirror, and nothing else on Calcs reads another sheet."""

from __future__ import annotations

import openpyxl
import pytest

from omd import template
from omd.harness.audit_offsheet import audit_offsheet
from omd.modules import debt_repay_linear
from omd.template import Step

EXT = {"repayment_flag": [0.0, 1.0, 1.0, 1.0], "interest_rate": 0.05, "opening_debt": 900.0}


@pytest.fixture()
def built(tmp_path):
    step = Step(
        debt_repay_linear.MODULE, {p.name: f"ext:{p.name}" for p in debt_repay_linear.MODULE.inputs}
    )
    comp = template.compose([step], EXT, "Mirror")
    path = str(tmp_path / "m.xlsx")
    comp.save(path)
    return comp, path


def test_every_input_is_mirrored_once_and_the_modules_read_the_mirror(built):
    comp, _path = built
    assert set(comp.mirror_rows) == set(EXT)
    title = comp.calcs.ws.title
    rate_row = comp.mirror_rows["interest_rate"]
    flag_row = comp.mirror_rows["repayment_flag"]
    ctx = comp.ctxs["debt_repay_linear"]
    assert ctx.source("interest_rate") == f"{title}!${comp.wb.period_cols[0]}${rate_row}"
    assert ctx.source("repayment_flag") == f"{title}!{{col}}{flag_row}"
    ws = comp.calcs.ws
    first = comp.wb.period_cols[0]
    assert ws[f"{first}{rate_row}"].value.startswith("=Inputs!")
    assert ws[f"{first}{flag_row}"].value.startswith("=Feed!")


def test_the_mirror_sits_above_every_module(built):
    comp, _path = built
    first_module_row = min(
        r for k, r in comp.calcs.rows().items() if k.startswith("debt_repay_linear.")
    )
    assert max(comp.mirror_rows.values()) < first_module_row


def test_the_workbook_still_reproduces_the_oracle_and_follows_its_inputs(built):
    comp, _path = built
    assert template.evaluate_and_compare(comp) == []
    assert template.inputs_drive_outputs(comp, EXT) == []


def test_nothing_outside_the_mirror_reads_another_sheet(built):
    comp, path = built
    assert audit_offsheet(path, comp.calcs.ws.title, comp.mirror_rows.values()) == []


def test_the_audit_catches_a_calculation_that_reads_another_sheet(built, tmp_path):
    comp, path = built
    wb = openpyxl.load_workbook(path)
    ws = wb[comp.calcs.ws.title]
    row = comp.calcs.rows()["debt_repay_linear.interest"]
    col = comp.wb.period_cols[1]
    ws[f"{col}{row}"] = "=Inputs!$B$5*2"
    bad = str(tmp_path / "bad.xlsx")
    wb.save(bad)
    found = audit_offsheet(bad, comp.calcs.ws.title, comp.mirror_rows.values())
    assert any(f"{col}{row} reads Inputs" in f for f in found)


def test_the_audit_catches_a_mirrored_input_nothing_reads(built, tmp_path):
    comp, path = built
    wb = openpyxl.load_workbook(path)
    ws = wb[comp.calcs.ws.title]
    rate_row = comp.mirror_rows["interest_rate"]
    for row in ws.iter_rows():
        for c in row:
            if c.row != rate_row and isinstance(c.value, str) and c.value.startswith("="):
                c.value = c.value.replace(f"${rate_row}", "$1").replace(
                    f"{comp.calcs.ws.title}!", ""
                )
    bad = str(tmp_path / "dead.xlsx")
    wb.save(bad)
    found = audit_offsheet(bad, comp.calcs.ws.title, comp.mirror_rows.values())
    assert any("interest_rate" in f and "read by nothing" in f for f in found)
