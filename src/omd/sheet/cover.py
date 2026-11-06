"""The cover sheet: what the model is, its status, and the basis it is built on, on the first page a reader sees.

A cover holds no calculation. Its facts are prose, and a fact that quotes an input is written as a formula over that
input, so the cover cannot go stale when the input changes::

    cover(wb, title="Toll road", status="Draft. Not for release.",
          facts=[("Funding", "Debt funds {debt_share:0%} of a capital cost of {capex:#,##0}.")])

`{name}` is an input name (as given to `Workbook.inputs`); the part after the colon is an Excel number format for
`TEXT()`, `General` when left out. A fact with no braces is plain text. Literal braces are written `{{` and `}}`.

Colours come from the style profile: `cover_ground` (the page), `cover_title`, `cover_label` and `cover_text`.
"""

from __future__ import annotations

import re
import string
from collections.abc import Sequence
from pathlib import Path

from openpyxl.styles import Alignment, PatternFill
from openpyxl.worksheet.properties import PageSetupProperties

#: the longest string literal Excel accepts inside a formula is 255 characters
_CHUNK = 250
#: text column width (characters), and the points per wrapped line of 12-point text
TEXT_WIDTH, LINE_PT = 74, 16


class CoverError(ValueError):
    pass


def _literal(text: str) -> list[str]:
    text = text.replace('"', '""')
    return [f'"{text[i : i + _CHUNK]}"' for i in range(0, len(text), _CHUNK)] if text else []


def live_text(template: str, refs: dict[str, str]) -> str:
    """A fact as a cell value: plain text when it quotes no input, else a formula joining text and TEXT(input, fmt)."""
    parts: list[str] = []
    quoted = False
    for literal, name, fmt, _conv in string.Formatter().parse(template):
        parts += _literal(literal or "")
        if name is None:
            continue
        if name not in refs:
            raise CoverError(
                f"cover fact quotes {{{name}}}, which is not an input: {template[:60]!r}"
            )
        fmt = (fmt or "General").replace('"', '""')
        parts.append(f'TEXT({refs[name]},"{fmt}")')
        quoted = True
    if not quoted:
        return template.replace("{{", "{").replace("}}", "}")
    return "=" + "&".join(parts)


def _lines(text: str) -> int:
    """Lines a fact wraps to in the text column (a formula is costed by its literal text)."""
    if text.startswith("="):
        text = "".join(re.findall(r'"((?:[^"]|"")*)"', text)) + " 0000000" * text.count("TEXT(")
    return max(1, -(-len(text) // (TEXT_WIDTH - 4)))


def cover(
    wb,
    *,
    title: str,
    subtitle: str | None = None,
    status: str | None = None,
    facts: Sequence[tuple[str, str]] = (),
    image: str | Path | None = None,
    name: str = "Cover",
):
    """Write the cover as the first sheet and return it.

    `facts` are (label, text) pairs, shown in order beside or under the title block; see the module note for live
    text. `image` is an optional picture (needs Pillow) placed in its own column on the left, with the title block
    and the facts to its right. The page is painted in the profile's ground colour and prints on one landscape page.
    """
    S = wb.style
    refs = dict(wb._refs)
    ws = wb.add_sheet(name, 0)
    wb._painted.add(name)
    ws.sheet_view.showGridLines = False
    ground = S.cover_ground or S.accent

    # columns: margin | (image | gap |) label | text | margin
    widths = [2] + ([110, 2] if image else []) + [26, TEXT_WIDTH, 2]
    for j, w in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(row=1, column=j).column_letter].width = w
    lab_col = 4 if image else 2
    last_col = len(widths)

    def line(row, text, *, size, color, bold=False, italic=False, height=None):
        ws.merge_cells(start_row=row, start_column=lab_col, end_row=row, end_column=lab_col + 1)
        c = ws.cell(row=row, column=lab_col, value=text)
        c.font = S._font(size=size, bold=bold, italic=italic, color=color)
        c.alignment = Alignment(vertical="center")
        if height:
            ws.row_dimensions[row].height = height
        return row + 1

    r = line(2, title, size=22, color=S.cover_title, bold=True, height=32)
    if subtitle:
        r = line(r, subtitle, size=16, color=S.cover_text, italic=True, height=24)
    if status:
        r = line(r, status, size=11, color=S.cover_title, bold=True, italic=True, height=20)
    r += 1
    for label, text in facts:
        lc = ws.cell(row=r, column=lab_col, value=label)
        lc.font = S._font(size=12, bold=True, color=S.cover_label)
        lc.alignment = Alignment(vertical="top")
        value = live_text(text, refs)
        tc = ws.cell(row=r, column=lab_col + 1, value=value)
        tc.font = S._font(size=12, color=S.cover_text)
        tc.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[r].height = LINE_PT * _lines(value)
        r += 1

    img_rows = 0
    if image:
        try:
            from openpyxl.drawing.image import Image
        except (
            ImportError
        ) as e:  # pragma: no cover - openpyxl always has it; Pillow is what may be missing
            raise CoverError("a cover image needs Pillow (pip install pillow)") from e
        try:
            pic = Image(str(image))
        except ImportError as e:
            raise CoverError("a cover image needs Pillow (pip install pillow)") from e
        px = widths[1] * 7 + 5 - 20
        pic.height = int(pic.height * px / float(pic.width))
        pic.width = px
        ws.add_image(pic, "B2")
        img_rows = 2 + int(pic.height / 20) + 1

    # The ground is painted last, over everything above, so a fact that grows can never run off the painted page.
    fill = PatternFill("solid", fgColor=ground)
    bottom = max(r + 1, img_rows + 2, 30)
    for row in range(1, bottom + 1):
        for col in range(1, last_col + 1):
            ws.cell(row=row, column=col).fill = fill
    ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 1
    last_letter = ws.cell(row=1, column=last_col).column_letter
    ws.print_area = f"A1:{last_letter}{bottom}"
    return ws
