"""Row addresses on Calcs, and Workbook.worksheets (design note section 2)."""

from __future__ import annotations

import pytest

from omd.harness._eval import cell, evaluate_cells
from omd.sheet import Workbook


def _book(opening: bool = True, name: str = "Calcs"):
    wb = Workbook("Addr", periods=["P1", "P2", "P3"], opening=opening)
    calcs = wb.calcs(name)
    calcs.row("rev", "  Revenue", lambda c: "=10", values=[10.0] * 3)
    return wb, calcs


def test_row_of_and_unknown_key():
    _, calcs = _book()
    assert calcs.row_of("rev") == calcs.rows()["rev"]
    with pytest.raises(KeyError, match="nope"):
        calcs.row_of("nope")
    with pytest.raises(KeyError, match="nope"):
        calcs.address("nope", col="C")
    with pytest.raises(KeyError, match="nope"):
        calcs.span("nope")


def test_address_forms():
    _, calcs = _book()
    r = calcs.row_of("rev")
    assert calcs.address("rev", col="E") == f"Calcs!$E${r}"
    assert calcs.address("rev", period=1) == f"Calcs!$C${r}"
    assert calcs.address("rev", period=3) == f"Calcs!$E${r}"
    assert calcs.address("rev", open=True) == f"Calcs!$B${r}"
    assert calcs.address("rev", col="E", absolute=False, sheet=False) == f"E{r}"
    assert calcs.address("rev", col="E", absolute=False) == f"Calcs!E{r}"
    assert calcs.span("rev") == f"Calcs!$C${r}:$E${r}"


def test_exactly_one_of_col_period_open():
    _, calcs = _book()
    for kw in ({}, {"col": "C", "period": 1}, {"period": 1, "open": True}, {"open": False}):
        with pytest.raises(ValueError):
            calcs.address("rev", **kw)


def test_period_range_and_missing_open():
    _, calcs = _book()
    for bad in (0, 4, -1):
        with pytest.raises(ValueError, match="period"):
            calcs.address("rev", period=bad)
    _, plain = _book(opening=False)
    with pytest.raises(ValueError, match="Open"):
        plain.address("rev", open=True)


@pytest.mark.parametrize(
    "name,quoted",
    [("Key results", "'Key results'"), ("Bob's", "'Bob''s'"), ("Calcs", "Calcs"), ("Q1", "'Q1'")],
)
def test_sheet_name_quoting(name, quoted):
    _, calcs = _book(name=name)
    r = calcs.row_of("rev")
    assert calcs.address("rev", col="E") == f"{quoted}!$E${r}"
    assert calcs.span("rev").startswith(f"{quoted}!")


def test_follows_set_layout():
    wb = Workbook("Addr", periods=["P1", "P2"], opening=True)
    wb.set_layout(open_col=4, first_period_col=6)
    calcs = wb.calcs()
    calcs.row("rev", "  Revenue", lambda c: "=1", values=[1.0, 1.0])
    r = calcs.row_of("rev")
    assert calcs.address("rev", open=True) == f"Calcs!$D${r}"
    assert calcs.address("rev", period=1) == f"Calcs!$F${r}"
    assert calcs.span("rev") == f"Calcs!$F${r}:$G${r}"


def test_worksheets_in_tab_order():
    wb, calcs = _book()
    extra = wb.add_sheet("Extra")
    assert isinstance(wb.worksheets, tuple)
    assert wb.worksheets == (calcs.ws, extra)
    wb.order_sheets(["Extra", "Calcs"])
    assert wb.worksheets == (extra, calcs.ws)


def test_second_sheet_formula_evaluates_to_calcs_value(tmp_path):
    pytest.importorskip("formulas")
    wb, calcs = _book(name="Key results")
    out = wb.add_sheet("Outputs")
    out["A1"] = f"={calcs.address('rev', period=2)}"
    out["A2"] = f"=SUM({calcs.span('rev')})"
    path = str(tmp_path / "addr.xlsx")
    wb.save(path)
    vals = evaluate_cells(path)
    assert cell(vals, "Outputs", "A1") == 10.0
    assert cell(vals, "Outputs", "A2") == 30.0
