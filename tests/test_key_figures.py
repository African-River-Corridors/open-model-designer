"""No hardcoded outputs (#12): key figures are live formulas, and the hardcode audit finds a typed number."""

from __future__ import annotations

import openpyxl
import pytest

from omd import template
from omd.harness._eval import evaluate_cells
from omd.harness.audit_hardcodes import audit_hardcodes
from omd.modules import debt_repay_linear
from omd.sheet.outputs import KeyFigureError
from omd.template import Step

EXT = {"repayment_flag": [0.0, 1.0, 1.0, 1.0], "interest_rate": 0.05, "opening_debt": 900.0}
ITEMS = [
    ("Debt", None),
    ("Interest, total", "debt_repay_linear.interest", "sum"),
    ("Debt service, lowest repayment period", "debt_repay_linear.debt_service", ("min_where", "input.repayment_flag")),
    ("Closing debt, period 2", "debt_repay_linear.debt_closing", 2),
    ("Closing debt, last", "debt_repay_linear.debt_closing", "last"),
]  # fmt: skip


@pytest.fixture()
def built(tmp_path):
    step = Step(
        debt_repay_linear.MODULE, {p.name: f"ext:{p.name}" for p in debt_repay_linear.MODULE.inputs}
    )
    comp = template.compose([step], EXT, "Key figures")
    comp.wb.key_figures("Key figures", ITEMS, index=0)
    path = str(tmp_path / "k.xlsx")
    comp.save(path)
    return comp, path


def _figures(path):
    ws = openpyxl.load_workbook(path)["Key figures"]
    vals = evaluate_cells(path, ("Key figures",))
    return {
        ws.cell(row=r, column=2).value: vals.get(f"KEY FIGURES'!C{r}")
        for r in range(6, ws.max_row + 1)
        if isinstance(ws.cell(row=r, column=3).value, str)
    }


def test_each_figure_is_a_formula_that_reads_its_row(built):
    comp, path = built
    exp = comp.expected["debt_repay_linear"]
    got = _figures(path)
    assert got["Interest, total"] == pytest.approx(sum(exp["interest"]))
    assert got["Debt service, lowest repayment period"] == pytest.approx(
        min(exp["debt_service"][1:])
    )
    assert got["Closing debt, period 2"] == pytest.approx(exp["debt_closing"][1])
    assert got["Closing debt, last"] == pytest.approx(exp["debt_closing"][-1])


def test_minifs_is_written_so_excel_knows_it(built):
    _comp, path = built
    ws = openpyxl.load_workbook(path)["Key figures"]
    formulas = [c.value for c in ws["C"] if isinstance(c.value, str) and "MINIFS" in c.value]
    assert formulas and all(f.startswith("=_xlfn.MINIFS(") for f in formulas)


def test_the_figures_follow_an_input(built, tmp_path):
    comp, path = built
    wb = openpyxl.load_workbook(path)
    ref = comp.ext_cells["opening_debt"][1]
    wb["Inputs"][ref] = 1800.0
    moved = str(tmp_path / "moved.xlsx")
    wb.save(moved)
    want = template.chained_oracle(comp.steps, {**EXT, "opening_debt": 1800.0})["debt_repay_linear"]
    assert _figures(moved)["Interest, total"] == pytest.approx(sum(want["interest"]))


def test_the_workbook_has_no_typed_output_and_the_audit_finds_one(built, tmp_path):
    _comp, path = built
    assert audit_hardcodes(path) == []
    wb = openpyxl.load_workbook(path)
    wb["Key figures"]["C8"] = 1234.5
    bad = str(tmp_path / "bad.xlsx")
    wb.save(bad)
    found = audit_hardcodes(bad)
    assert found and "Key figures!C8" in found[0] and "Interest, total" in found[0]
    seen = []
    assert audit_hardcodes(bad, declared={"Interest": "a test"}, out=seen.append) == []
    assert seen and "a test" in seen[0]


def test_a_number_pasted_as_a_formula_is_found_too(built, tmp_path):
    _comp, path = built
    wb = openpyxl.load_workbook(path)
    wb["Key figures"]["C8"] = "=0.153"
    wb["Key figures"]["C9"] = '=TEXT(1,"0")&"x"'
    bad = str(tmp_path / "bad.xlsx")
    wb.save(bad)
    found = audit_hardcodes(bad)
    assert sorted(f.split(" holds")[0] for f in found) == ["Key figures!C8", "Key figures!C9"]
    assert all("reads no cell" in f for f in found)


def test_a_figure_must_name_a_real_row(built):
    comp, _path = built
    with pytest.raises(KeyFigureError, match="not a Calcs row"):
        comp.wb.key_figures("Bad", [("X", "nope.nothing", "sum")])
