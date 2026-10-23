"""fastblock and drivertree: the build-time rules, each with a violation that must raise."""

import openpyxl
import pytest
import toy

from omd.harness import fastblock
from omd.harness.drivertree import DriverTree, DriverTreeError
from omd.harness.fastblock import Block, BlockError
from omd.sheet.verify import verify
from omd.sheet.workbook import Workbook


def _calcs(opening=True):
    toy.reset_registry()
    wb = Workbook("T", toy.PERIODS, opening=opening)
    ins = wb.inputs("D", {"x": ("X", 2.0)})
    return wb, wb.calcs(), ins, {}


def test_toy_model_builds_and_verifies(tmp_path):
    path = toy.build(str(tmp_path / "t.xlsx"))
    wb = openpyxl.load_workbook(path)
    calcs = wb["Calcs"]
    # the per-period link reaches the same column on another sheet
    r = toy.row_of(path, "Volume (units)")
    assert calcs[f"C{r}"].value == "=Schedules!C2" and calcs[f"F{r}"].value == "=Schedules!F2"
    # every block row is asserted against its values by the sheet-level verify
    from omd.sheet.verify import evaluate

    vals = evaluate(path)
    rr = toy.row_of(path, "Revenue ($)")
    assert [vals[f"CALCS'!{c}{rr}"] for c in "CDEF"] == toy.REV


def test_block_values_cover_every_row_written(tmp_path):
    toy.build(str(tmp_path / "t.xlsx"))
    assert len(fastblock.BLOCK_VALUES) == 6  # 3 rows in Revenue, 3 in Tax


def test_daisy_chain_is_refused():
    _wb, calcs, ins, reg = _calcs()
    b = Block(calcs, "A", registry=reg)
    b.link("x", ins["x"], "X", values=[2.0] * 4)
    b.calc("y", "Y", "{x}*{x}", key="y")
    b2 = Block(calcs, "B", registry=reg)
    b2.link("y", "y", "Y", values=[4.0] * 4)
    b3 = Block(calcs, "C", registry=reg)
    with pytest.raises(BlockError, match="3.06-02"):
        b3.link("yy", "_B_y", "Y again", values=[4.0] * 4)  # points at a link row


def test_recalculating_a_key_is_refused():
    _wb, calcs, ins, reg = _calcs()
    b = Block(calcs, "A", registry=reg)
    b.link("x", ins["x"], "X", values=[2.0] * 4)
    b.calc("y", "Y", "{x}*{x}", key="y")
    b2 = Block(calcs, "B", registry=reg)
    b2.link("x", ins["x"], "X", values=[2.0] * 4)
    with pytest.raises(BlockError, match="1.01-07"):
        b2.calc("y2", "Y again", "{x}*{x}", key="y")


def test_calc_may_only_name_rows_in_its_block():
    _wb, calcs, ins, reg = _calcs()
    b = Block(calcs, "A", registry=reg)
    b.link("x", ins["x"], "X", values=[2.0] * 4)
    with pytest.raises(BlockError, match="2.02-01"):
        b.calc("y", "Y", "{x}*{ghost}")


def test_too_many_operators_is_refused():
    _wb, calcs, ins, reg = _calcs()
    b = Block(calcs, "A", registry=reg)
    b.link("x", ins["x"], "X", values=[2.0] * 4)
    with pytest.raises(BlockError, match="operators"):
        b.calc("y", "Y", "{x}+{x}+{x}+{x}+{x}+{x}")


def test_link_without_values_is_refused():
    _wb, calcs, ins, reg = _calcs()
    b = Block(calcs, "A", registry=reg)
    with pytest.raises(BlockError, match="values"):
        b.link("x", ins["x"], "X")


def test_driver_declared_twice_is_refused():
    t = DriverTree()
    t.declare("rev", label="Revenue", unit="$", row=5, kind="calc")
    with pytest.raises(DriverTreeError, match="already calculated"):
        t.declare("rev", label="Revenue again", unit="$", row=9, kind="calc")


def test_tree_finds_cycles_orphans_and_depth():
    t = DriverTree()
    t.declare("a", label="A", unit="", row=1, kind="calc", reads=[2])
    t.declare("b", label="B", unit="", row=2, kind="calc", reads=[3])
    t.declare("c", label="C", unit="", row=3, kind="calc", reads=[])
    t.resolve()
    assert t.cycles() == []
    assert t.orphans(roots={"a"}) == []
    assert t.depth("a") == 2
    t.declare("d", label="D", unit="", row=4, kind="calc", reads=[5])
    t.declare("e", label="E", unit="", row=5, kind="calc", reads=[4])
    t.resolve()
    assert t.cycles(), "a circular definition must be reported"
    assert {"d", "e"} <= set(t.cycles()[0])


def test_link_resolves_through_to_the_calculation():
    t = DriverTree()
    t.declare("a", label="A", unit="", row=1, kind="calc")
    t.points_at(2, 1)
    t.declare("b", label="B", unit="", row=3, kind="calc", reads=[2])
    t.resolve()
    assert t.nodes["b"]["reads"] == ["a"]
    assert "flowchart TD" in t.mermaid("b")


def test_verify_from_blocks_goes_red_on_a_wrong_oracle(tmp_path):
    path = toy.build(str(tmp_path / "t.xlsx"))
    wb, calcs, _i, _r = _calcs()  # a fresh Calcs only to reuse the key map below

    class _C:  # the minimal shape verify() reads: name, rows(), period columns
        name = "Calcs"
        workbook = type("W", (), {"period_cols": tuple("CDEF")})()

        @staticmethod
        def rows():
            return {"rev": toy.row_of(path, "Revenue ($)")}

    verify(path, _C, {"rev": toy.REV})
    with pytest.raises(AssertionError, match="rev"):
        verify(path, _C, {"rev": [v + 1000 for v in toy.REV]})
