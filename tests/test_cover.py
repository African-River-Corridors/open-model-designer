"""The cover sheet (#8): a painted first page whose basis facts are live over the inputs."""

from __future__ import annotations

import openpyxl
import pytest

from omd.harness._eval import evaluate_cells
from omd.sheet.cover import CoverError, live_text
from omd.sheet.workbook import Workbook
from omd.style import DEFAULT, audit_style


def _book():
    wb = Workbook("Toll road", ["2027", "2028"])
    wb.inputs("Funding", {"debt_share": ("Debt share", 0.7), "capex": ("Capital cost", 1250.0)})
    return wb


def test_a_fact_that_quotes_an_input_is_a_formula_over_it():
    refs = {"debt_share": "Inputs!$B$5"}
    assert live_text("Debt funds {debt_share:0%} of it.", refs) == (
        '="Debt funds "&TEXT(Inputs!$B$5,"0%")&" of it."'
    )
    assert live_text("No inputs here {{braces}}.", refs) == "No inputs here {braces}."
    with pytest.raises(CoverError, match="not an input"):
        live_text("Uses {missing}.", refs)


def test_a_long_fact_is_split_into_literals_excel_accepts():
    text = "x" * 600 + " {debt_share}"
    f = live_text(text, {"debt_share": "Inputs!$B$5"})
    assert all(len(p) <= 252 for p in f[1:].split("&") if p.startswith('"'))


def test_the_cover_is_first_painted_and_follows_its_inputs(tmp_path):
    wb = _book()
    wb.cover(status="Draft.", facts=[("Funding", "Debt funds {debt_share:0%} of {capex:#,##0}.")])
    path = str(tmp_path / "c.xlsx")
    wb.save(path)
    assert wb.sheet_names[0] == "Cover"
    ws = openpyxl.load_workbook(path)["Cover"]
    assert ws["B2"].value == "Toll road"
    assert str(ws["A1"].fill.fgColor.rgb).endswith(DEFAULT.accent)
    assert ws.page_setup.orientation == "landscape"
    fact = next(c for c in ws["C"] if isinstance(c.value, str) and c.value.startswith("="))
    got = evaluate_cells(path, ("Cover",))[f"COVER'!{fact.coordinate}"]
    assert got == "Debt funds 70% of 1,250."
    # change the input: the cover follows
    book = openpyxl.load_workbook(path)
    book["Inputs"]["B5"] = 0.6
    moved = str(tmp_path / "moved.xlsx")
    book.save(moved)
    assert (
        evaluate_cells(moved, ("Cover",))[f"COVER'!{fact.coordinate}"] == "Debt funds 60% of 1,250."
    )


def test_the_cover_is_outside_the_style_audit_and_autosize(tmp_path):
    wb = _book()
    wb.cover(facts=[("Basis", "Plain text.")])
    widths = {c: wb.sheet("Cover").column_dimensions[c].width for c in "ABCD"}
    wb.autosize()
    assert {c: wb.sheet("Cover").column_dimensions[c].width for c in "ABCD"} == widths
    path = str(tmp_path / "c.xlsx")
    wb.save(path)
    assert audit_style(path) == []


def test_the_colours_come_from_the_profile(tmp_path):
    gold = DEFAULT.with_(name="gold-cover", cover_ground="1B2A4A", cover_title="C9A24B")
    wb = Workbook("Styled", ["P1"], style=gold)
    wb.inputs("S", {"x": ("X", 1.0)})
    ws = wb.cover()
    assert str(ws["A1"].fill.fgColor.rgb).endswith("1B2A4A")
    assert str(ws["B2"].font.color.rgb).endswith("C9A24B")


def test_a_cover_image_is_placed_left_of_the_text(tmp_path):
    PIL = pytest.importorskip("PIL.Image")
    img = tmp_path / "hero.png"
    PIL.new("RGB", (400, 300), (30, 60, 90)).save(img)
    wb = _book()
    ws = wb.cover(image=img, facts=[("Basis", "Text.")])
    assert len(ws._images) == 1
    assert ws["D2"].value == "Toll road"
