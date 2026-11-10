"""Sheet sets: a template names its own sheets and tab order, with a formula rewrite (design note section 3)."""

from __future__ import annotations

import pytest

from omd.harness._eval import evaluate_cells
from omd.sheet import SheetSet, Workbook
from omd.sheet.example import build_reference
from omd.sheet.workbook import _rewrite_refs, _sheet_refs


def _state(wb: Workbook):
    """Names, order and every formula of a book: what a failed apply must leave as it was."""
    return (
        wb.sheet_names,
        {
            (ws.title, c.coordinate): c.value
            for ws in wb.worksheets
            for row in ws.iter_rows()
            for c in row
        },
    )


def _numbers(path: str) -> dict[tuple[str, str], float]:
    """Every evaluated number as {(SHEET, REF): value}; `evaluate_cells` keys are "SHEET'!REF", upper case."""
    out = {}
    for k, v in evaluate_cells(path).items():
        if isinstance(v, int | float) and not isinstance(v, bool):
            sheet, ref = k.rsplit("'!", 1)
            out[(sheet, ref)] = v
    return out


def _same_numbers(before: str, after: str, names: dict[str, str]) -> None:
    """Every number of `before` sits, exactly, at the same cell of the renamed sheet in `after`."""
    up = {o.upper(): n.upper() for o, n in names.items()}
    old, new = _numbers(before), _numbers(after)
    assert old
    assert new == {(up[sheet], ref): v for (sheet, ref), v in old.items()}


# ---- the rewrite --------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "formula,expected",
    [
        ("=Calcs!A1+1", "=Workings!A1+1"),
        ("='Calcs'!A1", "=Workings!A1"),
        ("=SUM(Calcs!$C$5:$E$5)", "=SUM(Workings!$C$5:$E$5)"),
        ("=Calc!A1+Calcs!B2+MyCalcs!C3", "=Sums!A1+Workings!B2+MyCalcs!C3"),
        ('=IF(Calcs!A1>0,"Calcs!A1",0)', '=IF(Workings!A1>0,"Calcs!A1",0)'),
        ("=Inputs!$B$5*2", "='Key inputs'!$B$5*2"),
        ("='Bob''s'!A1", "=Bobs!A1"),
    ],
)
def test_rewrite_whole_references_only(formula, expected):
    names = {"Calcs": "Workings", "Calc": "Sums", "Inputs": "Key inputs", "Bob's": "Bobs"}
    assert _rewrite_refs(formula, names) == expected


def test_rewrite_quotes_an_apostrophe_and_reads_it_back():
    out = _rewrite_refs("=Calcs!A1", {"Calcs": "Bob's"})
    assert out == "='Bob''s'!A1"
    assert _sheet_refs(out) == ["Bob's"]


# ---- the set ------------------------------------------------------------------------------------
def test_a_set_names_each_sheet_once_and_validly():
    with pytest.raises(ValueError, match="once"):
        SheetSet([("A", "X"), ("B", "X")])
    with pytest.raises(ValueError, match="once"):
        SheetSet([("A", "X"), ("A", "Y")])
    for bad in ("", "a/b", "x" * 32, "'quoted'"):
        with pytest.raises(ValueError, match="valid"):
            SheetSet([("A", bad)])


def _book():
    wb = Workbook("Set", periods=["P1", "P2"], opening=True)
    ref = wb.inputs("Assumptions", {"p": ("Price", 3.0)})["p"]
    calcs = wb.calcs()
    calcs.row("price", "  Price", lambda c: f"={ref}", values=[3.0, 3.0])
    calcs.row("rev", "  Revenue", lambda c: f"={c.here('price')}*{c.i}", values=[3.0, 6.0])
    view = wb.period_sheet("Calc")  # a name that is a prefix of another sheet's
    view.row("Revenue", lambda c: f"={calcs.address('rev', col=c.col)}", key="rev_view")
    out = wb.add_sheet("MyCalcs")
    out["A1"] = f"=SUM({calcs.span('rev')})+SUM({view.span('rev_view')})"
    out["A2"] = '="see Calcs!C5"'
    return wb, calcs, view


SET = SheetSet(
    [("MyCalcs", "Key results"), ("Inputs", "Inputs"), ("Calcs", "Workings"), ("Calc", "Calcs")]
)


def test_apply_renames_reorders_and_keeps_every_number(tmp_path):
    wb, calcs, view = _book()
    before = str(tmp_path / "before.xlsx")
    wb.save(before)
    wb.apply_sheet_set(SET)
    assert wb.sheet_names == ["Key results", "Inputs", "Workings", "Calcs"]
    assert (calcs.name, view.name) == ("Workings", "Calcs")
    assert calcs.address("rev", period=1).startswith("Workings!")
    assert wb.sheet("Key results")["A2"].value == '="see Calcs!C5"'  # a string literal is text
    after = str(tmp_path / "after.xlsx")
    wb.save(after)
    _same_numbers(before, after, SET.names)


def test_a_swap(tmp_path):
    wb = Workbook("Swap", periods=["P1"])
    a, b = wb.add_sheet("A"), wb.add_sheet("B")
    a["A1"], b["A1"] = 1, 2
    a["A2"], b["A2"] = "=B!A1", "=A!A1"
    wb.apply_sheet_set(SheetSet([("A", "B"), ("B", "A")]))
    assert wb.sheet_names == ["B", "A"]
    assert wb.sheet("B")["A2"].value == "=A!A1"  # the old A, now named B, still reads the old B
    assert wb.sheet("A")["A1"].value == 2


def test_a_name_with_a_space_and_an_input_ref():
    wb, _calcs, _view = _book()
    wb.apply_sheet_set(
        SheetSet(
            [("MyCalcs", "Out"), ("Inputs", "Key inputs"), ("Calcs", "Calcs"), ("Calc", "View")]
        )
    )
    assert wb.sheet("Calcs")[f"C{_calcs.row_of('price')}"].value == "='Key inputs'!$B$5"
    assert wb._refs["p"] == "'Key inputs'!$B$5"


def test_a_hyperlink_follows_the_rename():
    from openpyxl.worksheet.hyperlink import Hyperlink

    wb = Workbook("Link", periods=["P1"])
    a = wb.add_sheet("A")
    wb.add_sheet("B")
    a["A1"].hyperlink = Hyperlink(ref="A1", location="'B'!A1")
    wb.apply_sheet_set(SheetSet([("A", "A"), ("B", "Target")]))
    assert wb.sheet("A")["A1"].hyperlink.location == "Target!A1"


@pytest.mark.parametrize(
    "pairs",
    [
        [("MyCalcs", "Key results"), ("Inputs", "Inputs"), ("Calcs", "Workings")],  # one left out
        [*SET.pairs, ("Ghost", "Ghost")],  # one extra
    ],
)
def test_a_bad_set_changes_nothing(pairs):
    wb, calcs, _view = _book()
    before = _state(wb)
    with pytest.raises(ValueError, match="every sheet"):
        wb.apply_sheet_set(SheetSet(pairs))
    assert _state(wb) == before and calcs.name == "Calcs"


def test_a_3d_range_is_rewritten():
    assert _rewrite_refs("=SUM(Jan:Mar!B1)", {"Jan": "January"}) == "=SUM(January:Mar!B1)"
    assert _rewrite_refs("=SUM('Jan:Mar'!B1)", {"Mar": "Q1 end"}) == "=SUM('Jan:Q1 end'!B1)"
    assert _sheet_refs("=SUM(Jan:Mar!B1)+'A b'!C1") == ["Jan", "Mar", "A b"]


def test_a_reference_the_rewrite_misses_changes_nothing(monkeypatch):
    from omd.sheet import workbook

    wb, calcs, _view = _book()
    before = _state(wb)
    monkeypatch.setattr(
        workbook, "_rewrite_refs", lambda f, names: f
    )  # the final scan must catch it
    with pytest.raises(ValueError, match="old sheet"):
        wb.apply_sheet_set(SET)
    assert _state(wb) == before and calcs.name == "Calcs"


def test_the_reference_book_renamed_keeps_its_numbers(tmp_path):
    before = str(tmp_path / "ref.xlsx")
    wb, _calc, _sot = build_reference(before)
    order = wb.sheet_names
    new = {n: f"{n} sheet" for n in order}
    wb.apply_sheet_set(SheetSet([(n, new[n]) for n in reversed(order)]))
    after = str(tmp_path / "ref-renamed.xlsx")
    wb.save(after)
    _same_numbers(before, after, new)
