"""Evaluate a workbook's formulas and index every scalar cell by `SHEET'!REF` (upper case)."""

from __future__ import annotations

import warnings

warnings.filterwarnings("ignore")

import formulas  # noqa: E402


def evaluate_cells(path: str, sheets: tuple[str, ...] | None = None) -> dict[str, float | str]:
    """Every scalar cell as {"SHEET'!REF": value}. Ranges and empty cells are left out.

    `sheets` limits the result to those sheet names (any case). Keys come from `formulas` as
    "'[book.xlsx]SHEET'!REF"; the book prefix and leading quote are dropped so a sheet name with
    spaces and one without index the same way.
    """
    want = None if sheets is None else tuple(s.upper() for s in sheets)
    sol = formulas.ExcelModel().loads(path).finish().calculate()
    out: dict[str, float | str] = {}
    for k, v in sol.items():
        ku = k.upper().split("]", 1)[1] if "]" in k else k.upper().lstrip("'")
        if want is not None and not any(ku.startswith(f"{s}'!") for s in want):
            continue
        val = v.value if hasattr(v, "value") else v
        try:
            x = val[0][0]
        except Exception:  # noqa: BLE001 — scalars and odd shapes are not cells we read
            continue
        if isinstance(x, bool):
            continue
        if isinstance(x, int | float):
            out[ku] = float(x)
        elif isinstance(x, str):
            out[ku] = x
    return out


def cell(values: dict[str, float | str], sheet: str, ref: str):
    """One cell from `evaluate_cells`, or None."""
    return values.get(f"{sheet.upper()}'!{ref}")
