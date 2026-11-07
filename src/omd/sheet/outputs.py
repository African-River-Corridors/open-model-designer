"""Key figures: the model's headline numbers on one sheet, each a live formula over a Calcs row.

A headline figure is easy to paste in from the oracle, and a pasted figure looks right until an input changes. Here
every figure names the Calcs row it reads and how it reads it, so the sheet cannot hold a typed number::

    key_figures(wb, "Key figures", [
        ("Returns", None),
        ("Equity IRR", "returns.equity_xirr", "first", "0.0%"),
        ("Minimum DSCR, repayment periods", "cover_ratios.dscr", ("min_where", "input.repayment_flag"), "0.00x"),
        ("Peak senior debt", "debt.debt_closing", "max"),
    ])

`how` is "first", "last", "sum", "min" or "max" over the row's periods, a 1-based period number, or
("min_where" | "max_where" | "sum_where", flag key): over the periods where that Calcs row reads 1.
An item `(label, None)` starts a section.
"""

from __future__ import annotations

from collections.abc import Sequence

from openpyxl.styles import Alignment

READS = {
    "first": "first period",
    "last": "last period",
    "sum": "sum of all periods",
    "min": "lowest period",
    "max": "highest period",
}


class KeyFigureError(ValueError):
    pass


def figure_formula(calcs, key: str, how, cols: Sequence[str]) -> tuple[str, str]:
    """The formula for one figure, and a few words saying how it reads the row."""
    rows = calcs.rows()
    if key not in rows:
        raise KeyFigureError(f"key figure reads {key!r}, which is not a Calcs row")
    sheet = f"'{calcs.ws.title}'" if " " in calcs.ws.title else calcs.ws.title
    r = rows[key]
    rng = f"{sheet}!${cols[0]}${r}:${cols[-1]}${r}"
    if isinstance(how, int):
        if not 1 <= how <= len(cols):
            raise KeyFigureError(f"key figure {key!r}: period {how} is outside 1..{len(cols)}")
        return f"={sheet}!${cols[how - 1]}${r}", f"period {how}"
    if how == "first":
        return f"={sheet}!${cols[0]}${r}", READS[how]
    if how == "last":
        return f"={sheet}!${cols[-1]}${r}", READS[how]
    if how in ("sum", "min", "max"):
        return f"={how.upper()}({rng})", READS[how]
    if (
        isinstance(how, tuple)
        and len(how) == 2
        and how[0] in ("min_where", "max_where", "sum_where")
    ):
        fn, flag = how
        if flag not in rows:
            raise KeyFigureError(f"key figure {key!r}: flag {flag!r} is not a Calcs row")
        fr = rows[flag]
        frng = f"{sheet}!${cols[0]}${fr}:${cols[-1]}${fr}"
        # MINIFS and MAXIFS came after Excel 2007: the file must name them with the _xlfn. prefix, or Excel and
        # LibreOffice show #NAME?. SUMIFS needs none.
        name = {"min_where": "_xlfn.MINIFS", "max_where": "_xlfn.MAXIFS", "sum_where": "SUMIFS"}[fn]
        words = {"min_where": "lowest", "max_where": "highest", "sum_where": "sum"}[fn]
        return f"={name}({rng},{frng},1)", f"{words} where {flag} is 1"
    raise KeyFigureError(f"key figure {key!r}: unknown reading {how!r}")


def key_figures(
    wb,
    name: str,
    items: Sequence[tuple],
    *,
    title: str | None = None,
    subtitle: str | None = None,
    calcs=None,
    index: int | None = None,
):
    """Write the key-figures sheet and return it. See the module note for `items`."""
    calcs = calcs or wb._calcs
    if calcs is None:
        raise KeyFigureError("key_figures needs a Calcs sheet — call .calcs() first")
    S = wb.style
    cols = list(wb.period_cols)
    ws = wb.add_sheet(name, index)
    S.white(ws)
    ws.column_dimensions["A"].width = 3
    ws.column_dimensions["B"].width = 44
    ws.column_dimensions["C"].width = 16
    ws.column_dimensions["D"].width = 40
    S.title(ws.cell(row=2, column=2, value=title or name), size=14)
    ws.cell(
        row=3, column=2, value=subtitle or "Every figure is a live formula over the Calcs sheet."
    )
    S.subtitle(ws.cell(row=3, column=2))
    S.colhdr(ws.cell(row=5, column=2, value=""), right=False)
    S.colhdr(ws.cell(row=5, column=3, value="Value"))
    S.colhdr(ws.cell(row=5, column=4, value="Read as"), right=False)
    r = 6
    for item in items:
        label, key = item[0], item[1]
        if key is None:
            r += 1
            S.section(ws.cell(row=r, column=2, value=label))
            S.rule_below(ws, r, 4)
            r += 1
            continue
        how = item[2] if len(item) > 2 else "first"
        fmt = item[3] if len(item) > 3 else None
        formula, words = figure_formula(calcs, key, how, cols)
        ws.cell(row=r, column=2, value=label)
        c = ws.cell(row=r, column=3, value=formula)
        c.number_format = S.token(fmt) if fmt else S.acct2
        c.alignment = Alignment(horizontal="right")
        S.subtitle(ws.cell(row=r, column=4, value=f"{key}: {words}"))
        r += 1
    ws.freeze_panes = "B6"
    wb._painted.add(name)
    return ws
