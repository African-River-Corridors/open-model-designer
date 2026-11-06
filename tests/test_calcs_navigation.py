"""Calcs formatting and navigation (#9, #10): chapter bars, logic notes, a contents list, outline groups, frozen panes."""

from __future__ import annotations

import openpyxl
import pytest

from omd import template
from omd.modules import cfads
from omd.style import DEFAULT, audit_style
from omd.template import Step

INPUTS = {
    "revenue": [0.0, 100.0, 120.0, 130.0],
    "operating_cost": [0.0, 40.0, 42.0, 44.0],
    "working_capital_movement": [0.0, 5.0, 2.0, 1.0],
    "tax_paid": [0.0, 0.0, 9.0, 12.0],
}
CHECK = ("Check - a template check row", lambda comp, col: "0")


@pytest.fixture(scope="module")
def book(tmp_path_factory):
    step = Step(cfads.MODULE, {p.name: f"ext:{p.name}" for p in cfads.MODULE.inputs}, title="CFADS")
    comp = template.compose([step], INPUTS, "Nav", link_checks=[CHECK])
    path = tmp_path_factory.mktemp("nav") / "nav.xlsx"
    comp.save(str(path))
    return comp, str(path)


def _find(ws, text):
    return next(r for r in range(1, ws.max_row + 1) if ws.cell(row=r, column=1).value == text)


def test_each_module_opens_on_a_bar_and_a_logic_note(book):
    comp, path = book
    ws = openpyxl.load_workbook(path)[comp.calcs.ws.title]
    hdr = _find(ws, "CFADS")
    for col in range(1, comp.calcs.last_col + 1):
        assert str(ws.cell(row=hdr, column=col).fill.fgColor.rgb).endswith(DEFAULT.accent)
    note = ws.cell(row=hdr + 1, column=1)
    assert note.value == "; ".join(cfads.MODULE.scope["in"])
    assert note.font.i


def test_the_contents_list_links_every_chapter(book):
    comp, path = book
    ws = openpyxl.load_workbook(path)[comp.calcs.ws.title]
    assert ws.cell(row=4, column=1).value == "Contents"
    links = {}
    r = 6
    while ws.cell(row=r, column=1).hyperlink is not None:
        links[ws.cell(row=r, column=1).value.strip()] = ws.cell(row=r, column=1).hyperlink.location
        r += 1
    assert {"Timeline", "CFADS", "Template checks"} <= set(links)
    for title, loc in links.items():
        row = int(loc.rsplit("A", 1)[1])
        assert ws.cell(row=row, column=1).value == title


def test_each_chapter_body_is_grouped_and_its_header_and_note_are_not(book):
    comp, path = book
    ws = openpyxl.load_workbook(path)[comp.calcs.ws.title]
    hdr = _find(ws, "CFADS")
    assert ws.row_dimensions[hdr].outlineLevel == 0
    assert ws.row_dimensions[hdr + 1].outlineLevel == 0
    cfads_row = comp.calcs.rows()["cfads.cfads"]
    assert ws.row_dimensions[cfads_row].outlineLevel == 1
    assert ws.sheet_properties.outlinePr.summaryBelow is False


def test_calcs_freezes_labels_and_headers_and_passes_the_style_audit(book):
    comp, path = book
    ws = openpyxl.load_workbook(path)[comp.calcs.ws.title]
    assert ws.freeze_panes == "B3"
    assert audit_style(path) == []


def test_a_profile_can_turn_the_bars_off(tmp_path):
    plain = DEFAULT.with_(name="no-bars", section_banner=False)
    step = Step(cfads.MODULE, {p.name: f"ext:{p.name}" for p in cfads.MODULE.inputs})
    comp = template.compose([step], INPUTS, "Plain", style=plain)
    path = str(tmp_path / "p.xlsx")
    comp.save(path)
    ws = openpyxl.load_workbook(path)[comp.calcs.ws.title]
    hdr = _find(ws, "Cfads")
    assert ws.cell(row=hdr, column=1).fill.fill_type is None
    assert audit_style(path, plain) == []


def test_a_bar_on_the_inputs_sheet_is_still_a_style_breach(tmp_path):
    from omd.sheet.workbook import Workbook

    wb = Workbook("Bars", ["P1"])
    wb.inputs("Section", {"x": ("X", 1.0)})
    wb.inputs_sheet["D9"].fill = openpyxl.styles.PatternFill("solid", fgColor=DEFAULT.accent)
    bad = str(tmp_path / "bad.xlsx")
    wb.save(bad)
    assert any("Inputs!D9" in p for p in audit_style(bad))
