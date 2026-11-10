"""Calc blocks read as steps (#24): units in their own column, italic links, bold ruled results, a gap per step."""

from __future__ import annotations

import openpyxl
import pytest

from omd import template
from omd.modules import debt_repay_linear
from omd.style import DEFAULT
from omd.template import Step

EXT = {"repayment_flag": [0.0, 1.0, 1.0, 1.0], "interest_rate": 0.05, "opening_debt": 900.0}


def _build(tmp_path, style=None):
    step = Step(
        debt_repay_linear.MODULE, {p.name: f"ext:{p.name}" for p in debt_repay_linear.MODULE.inputs}
    )
    comp = template.compose([step], EXT, "Steps", style=style)
    path = str(tmp_path / "s.xlsx")
    comp.save(path)
    return comp, openpyxl.load_workbook(path)


@pytest.fixture()
def built(tmp_path):
    return _build(tmp_path)


def _row_of(ws, label):
    return next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=1).value == label)


def test_units_sit_in_their_own_column(built):
    comp, wb = built
    ws = wb[comp.calcs.ws.title]
    assert ws["B2"].value == "Unit" and ws["C2"].value == "Open" and ws["D2"].value == "P1"
    r = comp.calcs.rows()["debt_repay_linear.interest"]
    assert ws.cell(row=r, column=1).value.strip() == "Interest"
    assert ws.cell(row=r, column=2).value == "USD"


def test_a_step_is_italic_links_then_a_bold_ruled_result(built):
    comp, wb = built
    ws = wb[comp.calcs.ws.title]
    r = comp.calcs.rows()["debt_repay_linear.interest"]
    result = ws.cell(row=r, column=1)
    assert result.font.b and ws.cell(row=r, column=comp.calcs.last_col).border.top.style == "thin"
    link = ws.cell(row=r - 1, column=1)  # the interest rate, linked in just above
    assert link.font.i and not link.font.b
    assert str(link.font.color.rgb).endswith(DEFAULT.accent)


def test_the_first_link_after_a_result_starts_a_taller_row(built):
    comp, wb = built
    ws = wb[comp.calcs.ws.title]
    r = comp.calcs.rows()["debt_repay_linear.interest"]
    nxt = r + 1  # the next step's first ingredient
    assert ws.cell(row=nxt, column=1).font.i
    assert ws.row_dimensions[nxt].height and ws.row_dimensions[nxt].height > 15


def test_feed_periods_line_up_with_calcs(built):
    comp, wb = built
    feed = wb["Feed"]
    assert feed["D1"].value == "P1" and feed["D2"].value == 0
    assert template.evaluate_and_compare(comp) == []
    assert template.inputs_drive_outputs(comp, EXT) == []


def test_a_profile_can_turn_the_step_style_off(tmp_path):
    comp, wb = _build(tmp_path, DEFAULT.with_(name="no-steps", step_style=False))
    ws = wb[comp.calcs.ws.title]
    r = comp.calcs.rows()["debt_repay_linear.interest"]
    assert not ws.cell(row=r, column=1).font.b and not ws.cell(row=r - 1, column=1).font.i
