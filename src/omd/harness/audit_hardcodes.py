"""Audit that a workbook's outputs follow its inputs: no typed number outside the input sheets.

A number typed on a calculation or presentation sheet does not move when an input moves. It may be right the day it
is written and wrong the day after, while every check still reads zero. So every numeric constant outside the input
sheets is a finding, unless it is declared, with a reason, in `declared`: {label substring: reason}. A declared
constant still prints, so it stays in view.

On a calculation sheet (`calc_sheets`) a formula is not a finding, even `=12`: a constant row written as a formula is
visible and labelled (FAST 1.03-02). On any other sheet a formula that reads no cell (`=0.153`) is a typed number in
disguise, and is a finding.

The label printed with a finding is the first text cell to the left of the number on its row.
"""

from __future__ import annotations

import re
from collections.abc import Collection, Mapping

import openpyxl
from openpyxl.utils import column_index_from_string

#: a cell reference, with or without a sheet name and $ signs
_REF = re.compile(r"\$?[A-Z]{1,3}\$?\d+(?![\w(])")
#: a string literal in a formula, removed before looking for references
_STR = re.compile(r'"(?:[^"]|"")*"')


def _covered_columns(ws, r: int) -> set[int]:
    """Columns on row `r` that the row's change flag (column B formula) compares, by a cell of this sheet."""
    flag = ws.cell(row=r, column=2).value
    if not (isinstance(flag, str) and flag.startswith("=")):
        return set()
    own = re.findall(r"(?<![!\w$])\$?([A-Z]{1,3})\$?" + str(r) + r"(?![\w(])", _STR.sub("", flag))
    return {column_index_from_string(x) for x in own}


def audit_hardcodes(
    path: str,
    *,
    input_sheets: Collection[str] = ("Inputs", "Feed"),
    calc_sheets: Collection[str] = ("Calcs",),
    stored_sheets: Collection[str] = ("Stored",),
    declared: Mapping[str, str] | None = None,
    out=None,
) -> list[str]:
    """One line per undeclared typed number outside `input_sheets`; empty when every output is a formula.

    A sheet in `stored_sheets` holds results the build computed, guarded by the stored-results check (`compose`'s
    `stored=`). A number is skipped there only in a column the row's change flag (column B) reads on the same sheet;
    any other typed number or constant formula on the sheet is a finding. Skipped numbers print as declared when
    `out` is given."""
    declared = dict(declared or {})
    wb = openpyxl.load_workbook(path)
    problems: list[str] = []
    for ws in wb.worksheets:
        if ws.title in input_sheets:
            continue
        guarded = 0
        for row in ws.iter_rows():
            covered = _covered_columns(ws, row[0].row) if ws.title in stored_sheets else set()
            for c in row:
                v = c.value
                if c.column in covered and isinstance(v, int | float) and not isinstance(v, bool):
                    guarded += 1
                    continue
                if isinstance(v, str) and v.startswith("="):
                    if ws.title in calc_sheets or _REF.search(_STR.sub("", v)):
                        continue
                    what = f"the formula {v[:30]!r}, which reads no cell"
                elif isinstance(v, bool) or not isinstance(v, int | float):
                    continue
                else:
                    what = f"the typed number {v!r}"
                label = next(
                    (
                        str(ws.cell(row=c.row, column=j).value).strip()
                        for j in range(1, c.column)
                        if isinstance(ws.cell(row=c.row, column=j).value, str)
                        and not str(ws.cell(row=c.row, column=j).value).startswith("=")
                    ),
                    "",
                )
                reason = next((why for k, why in declared.items() if k in label), None)
                line = f"{ws.title}!{c.coordinate} holds {what} ({label[:50]!r})"
                if reason is None:
                    problems.append(line)
                elif out is not None:
                    out(f"declared: {line}: {reason}")
        if guarded and out is not None:
            out(
                f"declared: {ws.title} holds {guarded} stored numbers, guarded by the stored-results check"
            )
    return problems
