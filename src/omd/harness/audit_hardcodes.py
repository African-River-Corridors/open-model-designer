"""Audit that a workbook's outputs follow its inputs: no typed number outside the input sheets.

A number typed on a calculation or presentation sheet does not move when an input moves. It may be right the day it
is written and wrong the day after, while every check still reads zero. So every numeric constant outside the input
sheets is a finding, unless it is declared, with a reason, in `declared`: {label substring: reason}. A declared
constant still prints, so it stays in view.

Formulas are not findings, even `=12`: a constant row written as a formula is visible and labelled (FAST 1.03-02).
"""

from __future__ import annotations

from collections.abc import Collection, Mapping

import openpyxl


def audit_hardcodes(
    path: str,
    *,
    input_sheets: Collection[str] = ("Inputs", "Feed"),
    declared: Mapping[str, str] | None = None,
    label_col: int = 1,
    out=None,
) -> list[str]:
    """One line per undeclared typed number outside `input_sheets`; empty when every output is a formula."""
    declared = dict(declared or {})
    wb = openpyxl.load_workbook(path)
    problems: list[str] = []
    for ws in wb.worksheets:
        if ws.title in input_sheets:
            continue
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if isinstance(v, bool) or not isinstance(v, int | float):
                    continue
                label = str(ws.cell(row=c.row, column=label_col).value or "").strip()
                reason = next((why for k, why in declared.items() if k in label), None)
                line = f"{ws.title}!{c.coordinate} holds the typed number {v!r} ({label[:50]!r})"
                if reason is None:
                    problems.append(line)
                elif out is not None:
                    out(f"declared: {line}: {reason}")
    return problems
