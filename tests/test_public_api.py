"""T4: the harness and verify use only the public API of Workbook and Calcs, and each public call works."""

import re
from pathlib import Path

import pytest

from omd.sheet.workbook import Workbook

ROOT = Path(__file__).resolve().parent.parent
PRIVATE = re.compile(r"\._(wb|period_cols|open_col|open_col_idx|inputs_ws|row|HDR_ROW|all_cols)\b")


def test_harness_and_verify_use_only_the_public_api():
    offenders = []
    for path in [*(ROOT / "src/omd/harness").glob("*.py"), ROOT / "src/omd/sheet/verify.py"]:
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if PRIVATE.search(line):
                offenders.append(f"{path.name}:{n}")
    assert offenders == []


def test_the_private_scan_sees_a_private_use():
    assert PRIVATE.search("x = wb._period_cols[0]") and PRIVATE.search("c._row += 1")


@pytest.fixture
def wb():
    w = Workbook("T", ["a", "b", "c"], opening=True)
    w.inputs("D", {"x": ("X units", 1.0)})
    return w


def test_n1_n2_columns(wb):
    assert wb.period_cols == ("C", "D", "E")
    assert wb.open_col == "B"
    assert wb.all_cols == ("B", "C", "D", "E")
    assert Workbook("T", ["a"]).open_col is None


def test_columns_cannot_be_changed_through_the_returned_value(wb):
    with pytest.raises(TypeError):
        wb.period_cols[0] = "Z"  # a tuple: item assignment is refused
    assert wb.period_cols == ("C", "D", "E")


def test_n3_set_layout_moves_columns_and_calcs_follow():
    w = Workbook("T", ["a", "b"], opening=True)
    w.set_layout(open_col=4, first_period_col=5)
    assert (w.open_col, w.period_cols, w.all_cols) == ("D", ("E", "F"), ("D", "E", "F"))
    calcs = w.calcs()
    assert calcs.ws["E2"].value == "a" and calcs.ws["F2"].value == "b"
    assert calcs.ws["D2"].value == "Open"


def test_n3_set_layout_after_calcs_is_refused(wb):
    wb.calcs()
    with pytest.raises(ValueError, match="before calcs"):
        wb.set_layout(open_col=4, first_period_col=5)


def test_n3_set_layout_refuses_open_right_of_periods():
    with pytest.raises(ValueError, match="left of"):
        Workbook("T", ["a"], opening=True).set_layout(open_col=5, first_period_col=5)


def test_n4_n5_n7_row_cursor_and_header(wb):
    c = wb.calcs()
    assert c.header_row == 2
    first = c.next_row
    c.section("S")
    assert c.next_row == first + 1
    c.skip_rows(3)
    assert c.next_row == first + 4
    c.skip_rows()
    assert c.next_row == first + 5
    c.row("r", "  Row", lambda x: "=1")
    assert c.rows()["r"] == first + 5
    with pytest.raises(ValueError):
        c.skip_rows(-1)


def test_n6_inputs_sheet(wb):
    assert wb.inputs_sheet is not None and wb.inputs_sheet.title == "Inputs"
    assert wb.inputs_sheet["A5"].value == "X units"
    assert Workbook("T", ["a"]).inputs_sheet is None


def test_n8_sheet_calls(wb):
    wb.calcs()
    s = wb.add_sheet("Summary")
    z = wb.add_sheet("Front", 0)
    assert s.title == "Summary" and wb.sheet_names[0] == "Front"
    assert wb.sheet("Summary") is s
    wb.rename_sheet("Summary", "Totals")
    assert "Totals" in wb.sheet_names and "Summary" not in wb.sheet_names
    wb.order_sheets(["Totals", "Calcs", "Inputs", "Front"])
    assert wb.sheet_names == ["Totals", "Calcs", "Inputs", "Front"]
    assert z.title == "Front"


def test_n8_order_sheets_needs_every_sheet_once(wb):
    wb.calcs()
    with pytest.raises(ValueError, match="every sheet once"):
        wb.order_sheets(["Calcs"])
    with pytest.raises(ValueError, match="every sheet once"):
        wb.order_sheets(["Calcs", "Calcs", "Inputs"])


def test_n8_full_calc_on_load(wb):
    wb.full_calc_on_load = False
    assert wb.full_calc_on_load is False
    wb.full_calc_on_load = True
    assert wb.full_calc_on_load is True


def test_n9_calcs_reaches_its_workbook(wb):
    assert wb.calcs().workbook is wb
