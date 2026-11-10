"""Period sheets: an extra sheet in house style, lined up with Calcs (design note section 1)."""

from __future__ import annotations

import hashlib
import json

import openpyxl
import pytest

from omd.harness._eval import cell, evaluate_cells
from omd.harness.audit_hardcodes import audit_hardcodes
from omd.harness.audit_offsheet import audit_offsheet
from omd.sheet import PeriodSheet, Workbook
from omd.sheet.example import build_reference

# Cell-map digests of two books, taken from `main` before Calcs moved onto the shared base.
REFERENCE_DIGEST = "c6190d5ac9acb4e8644dfc4ea5855526d7b8079ae47eda08d0ee537a7d8c6e28"
UNITS_DIGEST = "bdeae1a0936d70a23c62dbb0840d311a924af4af32d843c37f4c5fe5ba84225b"


def _cell_map_digest(path: str) -> str:
    """Values, formulas, number formats, bold, italic, fill, merges and frozen panes, sheet by sheet."""
    book = openpyxl.load_workbook(path)
    items = []
    for ws in book.worksheets:
        items.append(
            ["sheet", ws.title, ws.freeze_panes, sorted(str(m) for m in ws.merged_cells.ranges)]
        )
        for row in ws.iter_rows():
            for c in row:
                if c.value is None and not c.has_style:
                    continue
                fill = c.fill.fgColor.rgb if c.fill and c.fill.fill_type else None
                items.append(
                    [ws.title, c.coordinate, repr(c.value), c.number_format, bool(c.font.b), c.font.i, fill]
                )  # fmt: skip
    return hashlib.sha256(json.dumps(items).encode()).hexdigest()


def _units_book(path: str) -> None:
    wb = Workbook("Units", periods=["P1", "P2"], opening=True)
    wb.set_layout(open_col=3, first_period_col=4, units_col=2)
    ref = wb.inputs("A", {"p": ("Price", 2.0)})["p"]
    c = wb.calcs()
    c.section("Flows", note="A note.")
    c.row("rev", "  Revenue (USD)", lambda x: f"={ref}*{x.i}", values=[2.0, 4.0])
    c.roll("cash", "  Cash (USD)", opening=1.0, add=["rev"], values=[3.0, 7.0])
    c.chapter("Part two")
    wb.statement("Accounts", [("P&L", [("Revenue", "rev", {"total": True})])])
    wb.save(path)


def _book(opening: bool = True, layout: tuple[int | None, int] | None = None):
    wb = Workbook("Period", periods=["P1", "P2", "P3"], opening=opening)
    if layout is not None:
        wb.set_layout(open_col=layout[0], first_period_col=layout[1])
    ref = wb.inputs("Assumptions", {"price": ("Price", 4.0)})["price"]
    calcs = wb.calcs()
    calcs.row("price", "  Price", lambda c: f"={ref}", values=[4.0] * 3)  # the mirrored input
    calcs.row("rev", "  Revenue", lambda c: f"={c.here('price')}*{c.i}", values=[4.0, 8.0, 12.0])
    return wb, calcs


def test_books_built_with_todays_api_are_unchanged(tmp_path):
    ref, units = str(tmp_path / "ref.xlsx"), str(tmp_path / "units.xlsx")
    build_reference(ref)
    _units_book(units)
    assert _cell_map_digest(ref) == REFERENCE_DIGEST
    assert _cell_map_digest(units) == UNITS_DIGEST


@pytest.mark.parametrize("opening,layout", [(True, None), (False, None), (True, (4, 6))])
def test_columns_and_header_row_line_up_with_calcs(opening, layout):
    wb, calcs = _book(opening, layout)
    ps = wb.period_sheet("Annual view", subtitle="Each line links to its Calcs row.")
    assert isinstance(ps, PeriodSheet)
    assert ps.header_row == calcs.header_row
    assert ps.last_col == calcs.last_col
    for letter, label in zip(wb.period_cols, ["P1", "P2", "P3"]):
        assert ps.ws[f"{letter}{ps.header_row}"].value == label
    if wb.open_col:
        assert ps.ws[f"{wb.open_col}{ps.header_row}"].value == "Open"
    assert ps.ws.freeze_panes == calcs.ws.freeze_panes
    assert ps.ws["A1"].value == "Annual view"
    assert ps.ws["A3"].value == "Each line links to its Calcs row."


def test_set_layout_after_a_period_sheet_raises():
    wb = Workbook("Period", periods=["P1"], opening=True)
    wb.period_sheet("View")
    with pytest.raises(ValueError, match="period_sheet"):
        wb.set_layout(open_col=3, first_period_col=4)


def test_rows_sections_and_cursor():
    wb, calcs = _book()
    ps = wb.period_sheet("View", title="A view")
    assert ps.ws["A1"].value == "A view"
    start = ps.next_row
    ps.section("Revenue")
    ps.note("Linked to Calcs.")
    r = ps.row("Revenue", lambda c: f"={calcs.address('rev', col=c.col)}", key="rev_view")
    assert r == start + 2
    assert ps.next_row == r + 1
    ps.skip_rows(2)
    assert ps.next_row == r + 3
    unkeyed = ps.row("Spare", lambda c: f"={calcs.address('rev', col=c.col)}*0")
    assert unkeyed == r + 3
    assert ps.rows() == {"rev_view": r}
    assert ps.name == ps.ws.title == "View"


def test_address_and_span_on_a_period_sheet(tmp_path):
    wb, calcs = _book()
    ps = wb.period_sheet("Annual view")
    r = ps.row("Revenue", lambda c: f"={calcs.address('rev', col=c.col)}", key="rev_view")
    assert ps.address("rev_view", period=1) == f"'Annual view'!$C${r}"
    assert ps.address("rev_view", open=True) == f"'Annual view'!$B${r}"
    assert ps.span("rev_view") == f"'Annual view'!$C${r}:$E${r}"
    with pytest.raises(KeyError, match="nope"):
        ps.address("nope", period=1)

    out = wb.add_sheet("Out")
    out["A1"] = f"=SUM({ps.span('rev_view')})"
    path = str(tmp_path / "ps.xlsx")
    wb.save(path)
    vals = evaluate_cells(path)
    assert cell(vals, "Annual view", f"D{r}") == 8.0
    assert cell(vals, "Out", "A1") == 24.0


def test_audits_pass_a_linked_period_sheet_and_catch_a_typed_number(tmp_path):
    wb, calcs = _book()
    ps = wb.period_sheet("View")
    ps.section("Revenue")
    r = ps.row("Revenue", lambda c: f"={calcs.address('rev', col=c.col)}", key="rev_view")
    path = str(tmp_path / "clean.xlsx")
    wb.save(path)
    assert audit_hardcodes(path) == []
    assert audit_offsheet(path, "Calcs", [calcs.row_of("price")]) == []

    ps.ws.cell(row=r, column=4, value=8.0)  # a typed number over a link
    path = str(tmp_path / "typed.xlsx")
    wb.save(path)
    found = audit_hardcodes(path)
    assert len(found) == 1 and found[0].startswith(f"View!D{r} holds the typed number 8 ")


def test_calcs_rows_return_the_key_and_period_rows_their_number():
    wb, calcs = _book()
    assert calcs.row("cost", "  Cost", lambda c: "=1") == "cost"
    ps = wb.period_sheet("View")
    assert isinstance(ps.row("Cost", lambda c: "=1"), int)
