"""Audit that a Calcs sheet reads other sheets in one place only: its block of mirrored inputs.

A reader should trace any number on Calcs without leaving the sheet. So every input is linked onto Calcs once, at
the top, and every calculation reads those rows. This audit says where that fails:

* a formula outside the mirrored rows that names another sheet;
* a mirrored row that is not a pure link to one cell (`=0.05` or `=Inputs!B5*2` would hide a number on Calcs);
* a mirrored input that no other formula on Calcs reads. The mirror references every input, so without this a dead
  input would look used to a guard that only asks "is this input referenced?".
"""

from __future__ import annotations

import re
from collections.abc import Collection

import openpyxl

#: a sheet name before "!": quoted ('My sheet'!) or bare (Inputs!)
SHEET_REF = re.compile(r"(?:'((?:[^']|'')+)'|([A-Za-z_][\w.]*))!")
_C = r"\$?[A-Z]{1,3}\$?(\d+)"
#: a cell or a range, with an optional sheet name: "q" (quoted) or "b" (bare) is the sheet, "a" and "z" the rows
REF = re.compile(
    r"(?:(?:'(?P<q>(?:[^']|'')+)'|(?P<b>[A-Za-z_][\w.]*))!)?"
    + _C.replace("(\\d+)", "(?P<a>\\d+)")
    + r"(?::"
    + _C.replace("(\\d+)", "(?P<z>\\d+)")
    + r")?(?![\w(])"
)


#: a mirrored row holds a link to one cell on another sheet, and nothing else
PURE_LINK = re.compile(r"^=(?:'(?:[^']|'')+'|[A-Za-z_][\w.]*)!\$?[A-Z]{1,3}\$?\d+$")


def _sheet(q: str | None, b: str | None) -> str | None:
    return q.replace("''", "'") if q else b


def audit_offsheet(path: str, calcs_sheet: str, mirror_rows: Collection[int]) -> list[str]:
    """One line per breach; an empty list means the sheet is self-contained apart from its mirrored inputs."""
    ws = openpyxl.load_workbook(path)[calcs_sheet]
    mirror = set(mirror_rows)
    read: set[int] = set()
    problems: list[str] = []
    for row in ws.iter_rows():
        for c in row:
            v = c.value
            if not (isinstance(v, str) and v.startswith("=")):
                continue
            if c.row in mirror:
                if not PURE_LINK.match(v):
                    problems.append(
                        f"{calcs_sheet}!{c.coordinate} is a mirrored input but not a pure link: {v[:70]}"
                    )
                continue
            others = {
                (q or b).replace("''", "'")
                for q, b in SHEET_REF.findall(v)
                if (q or b).replace("''", "'") != calcs_sheet
            }
            if others:
                problems.append(
                    f"{calcs_sheet}!{c.coordinate} reads {', '.join(sorted(others))}: {v[:70]}"
                )
            # rows read on this sheet: refs with no sheet name, or qualified with this sheet's own name
            for m in REF.finditer(v):
                sheet = _sheet(m.group("q"), m.group("b"))
                if sheet in (None, calcs_sheet):
                    a = int(m.group("a"))
                    read.update(range(a, int(m.group("z") or a) + 1))
    for r in sorted(mirror - read):
        label = str(ws.cell(row=r, column=1).value or "").strip()
        problems.append(f"{calcs_sheet} row {r}: mirrored input {label!r} is read by nothing")
    return problems
