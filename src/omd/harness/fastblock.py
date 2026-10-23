"""FAST calculation blocks for an omd spec module.

Implements FAST Standard 02c (July 2019, CC-BY 4.0) section 2.02, which codifies the layout
this module follows:

  FAST 2.02-01  "Construct all calculations in a separate calculation block. All ingredients
                 must be presented as LINKS IMMEDIATELY ABOVE the calculation, with consistent
                 calculation order and appearance in the formula."
  FAST 2.02-04  "List precedents in the order they appear in a formula."
  FAST 1.01-05  "Repeated links have the dual benefit of increasing formula comprehension by
                 co-locating ingredients ... within a single calculation block."

So the extra rows and the repeated input rows are not a cost the standard tolerates — they are
the mechanism. Two rules bound it, and this module enforces both:

  FAST 1.01-07  Calculate only once. Repeat a LINK freely; never repeat a CALCULATION.
                -> `link()` may point at the same source any number of times. `calc()` keys are
                   unique across the sheet, and a duplicate raises.
  FAST 3.06-02  Do not create daisy chains; do not link to links. A link points at the original
                source. -> `link()` refuses a source that is itself a link row.

And FAST 2.02-06: timing conditionals belong in their own flag row, multiplied in — not
embedded as IF() inside every formula. Use `Calcs`-level flag rows and reference them.

Why a block, mechanically: `calc()` expressions name only rows inside their own block, so the
precedent distance is bounded by construction, not by discipline. `check()` asserts it.
"""

from __future__ import annotations

import re

from omd.sheet import formatting as F

from .drivertree import DriverTree

TREE = DriverTree()

NAME = re.compile(r"\{(~?)([A-Za-z_][A-Za-z0-9_]*)\}")

#: A calc row may reach this far back. Enough for a short block; a declared `total()` may
#: reach over its whole block. The rule of thumb is 2-3 rows; 6 leaves room for a link
#: triple plus an intermediate without inviting sprawl.
MAX_PRECEDENT_DISTANCE = 6

#: A calc row may use at most this many arithmetic operators. FAST wants "short, simple,
#: direct". The pre-block model had rows with 13.
MAX_OPERATORS = 4

_OPS = re.compile(r"[+\-*/^]")

#: Every row a block writes, with the values verify should assert it against. Blocks must not
#: silently lower the model's verify coverage — the whole point is more rows, and an unasserted
#: row is a row nobody checked.
BLOCK_VALUES: dict[str, list[float]] = {}


class BlockError(AssertionError):
    """A block violated a FAST rule this module enforces."""


class Block:
    """One FAST 2.02-01 calculation block on a `Calcs` sheet."""

    def __init__(self, calcs, title: str, *, registry: dict):
        self.c = calcs
        self.wb = calcs.workbook
        self.cols = list(self.wb.period_cols)
        self.n = len(self.cols)
        self.title = title
        self.reg = registry  # sheet-wide: key -> ("link" | "calc")
        self.local: dict[str, int] = {}  # block-local name -> sheet row
        self.kinds: dict[str, str] = {}  # block-local name -> "link" | "calc"
        self.vals: dict[str, list[float]] = {}
        calcs.skip_rows()  # FAST readability: breathing room before a block header
        calcs.section(title)

    # -- ingredients ---------------------------------------------------------------------
    def link(self, name: str, source, label: str, *, values=None, fmt=F.NUM):
        """A link row: the ingredient, restated immediately above the calculation that uses it.

        `source` is an Inputs reference string ("Inputs!$B$47"; any fixed cell "Sheet!$C$9" reads the same way, for a scalar taken from the first period of a row), a per-period row on another
        sheet written with a `{col}` placeholder ("Schedules!{col}5"), or the key of a Calcs
        row. Linking to another link row raises — FAST 3.06-02.
        """
        if isinstance(source, str) and (source.startswith("Inputs!") or "!$" in source):
            per_col = lambda col: f"={source}"
            src_vals = values
        elif isinstance(source, str) and "{col}" in source:
            # A time-series input row on another sheet, e.g. "Schedules!{col}5": the same
            # column as this period, not one fixed cell.
            per_col = lambda col, source=source: "=" + source.format(col=col)
            src_vals = values
        else:
            if self.reg.get(source) == "link":
                raise BlockError(
                    f"{self.title!r}: link {name!r} points at {source!r}, which is itself a "
                    f"link row. FAST 3.06-02 forbids daisy chains — point at the original "
                    f"source calculation instead."
                )
            rr = self.c.rows()[source]
            per_col = lambda col, rr=rr: f"={col}{rr}"
            src_vals = values
        if src_vals is None:
            raise BlockError(
                f"{self.title!r}: link {name!r} needs `values` so verify can assert it"
            )
        row = self._write(name, label, per_col, src_vals, fmt, kind="link")
        if isinstance(source, str) and source in self.c.rows():
            TREE.points_at(row, self.c.rows()[source])
        return row

    def const(self, name: str, label: str, value: float, *, fmt=F.NUM):
        """A literal constant as its own row — a unit conversion, a divisor, a count.

        FAST 1.03-02: a number that means something belongs on a row a reader can see and a
        units column can police, not buried inside a formula. `12` inside `{fte}*{rate}*12` is
        invisible; `Months per year` above the calculation is not.
        """
        return self._write(
            name, label, lambda col: f"={value:g}", [value] * self.n, fmt, kind="link"
        )

    def relink(self, name: str, source: str, label: str, *, fmt=F.NUM):
        """Restate an earlier row of THIS block immediately above where it is used again.

        FAST 1.01-05: "Repeated links have the dual benefit of increasing formula
        comprehension by co-locating ingredients ... within a single calculation block."
        The precedent distance resets to one row, which is the whole point.

        FAST 3.06-02 still applies: you may not relink a link. Point at the calculation.
        """
        if source not in self.local:
            raise BlockError(f"{self.title!r}: relink {name!r} — {source!r} is not in this block")
        if self.kinds.get(source) == "link":
            raise BlockError(
                f"{self.title!r}: relink {name!r} points at {source!r}, which is already a "
                f"link. FAST 3.06-02 forbids daisy chains — point at the calculation."
            )
        rr = self.local[source]
        _lr = self._write(
            name, label, lambda col, rr=rr: f"={col}{rr}", self.vals[source], fmt, kind="link"
        )
        TREE.points_at(_lr, rr)
        return _lr

    def link_prev(self, name: str, source: str, label: str, *, values, fmt=F.NUM):
        """Link the PRIOR column of a Calcs row — the ingredient a roll-forward needs.

        Written as its own row so the corkscrew's arithmetic stays one operation wide, and
        so a reader can see the opening position rather than decode a column offset inside
        a longer formula.
        """
        if isinstance(source, int):
            # A self-referencing corkscrew: the row is defined at the END of this block, so
            # its number is predicted here and asserted by the caller once it exists.
            rr = source
        else:
            if self.reg.get(source) == "link":
                raise BlockError(
                    f"{self.title!r}: link_prev {name!r} points at {source!r}, which is itself "
                    f"a link. FAST 3.06-02 forbids daisy chains."
                )
            rr = self.c.rows()[source]
        cols = self.cols
        allc = ([self.wb.open_col] if self.wb.open_col else []) + list(cols)

        def per_col(col, rr=rr, allc=allc):
            i = allc.index(col)
            return f"={allc[i - 1]}{rr}" if i > 0 else "=0"

        return self._write(name, label, per_col, values, fmt, kind="link")

    # -- the calculation -----------------------------------------------------------------
    def calc(
        self,
        name: str,
        label: str,
        expr: str,
        *,
        key: str | None = None,
        fmt=F.NUM,
        allow_distance: int | None = None,
        values=None,
        close: bool = False,
    ):
        """One simple calculation over rows in THIS block.

        `expr` names block-local rows: "{overhead}*{share}". `{~name}` is the PRIOR column of
        that row, for corkscrews (FAST 2.02-05). `key` also registers the row sheet-wide so
        later blocks can link to it.
        """
        names = NAME.findall(expr)
        for prev, nm in names:
            if nm not in self.local:
                raise BlockError(
                    f"{self.title!r}: calc {name!r} references {nm!r}, which is not a row in "
                    f"this block. Every ingredient must be linked in above it (FAST 2.02-01)."
                )
        nops = len(_OPS.findall(NAME.sub("x", expr)))
        if nops > MAX_OPERATORS:
            raise BlockError(
                f"{self.title!r}: calc {name!r} has {nops} operators (limit {MAX_OPERATORS}). "
                f"Split it into more rows — that is the point of a block."
            )

        limit = allow_distance if allow_distance is not None else MAX_PRECEDENT_DISTANCE
        row_will_be = self.c.next_row
        for prev, nm in names:
            d = row_will_be - self.local[nm]
            if d > limit:
                raise BlockError(
                    f"{self.title!r}: calc {name!r} reaches {d} rows back for {nm!r} "
                    f"(limit {limit}). Re-link the ingredient immediately above (FAST 2.02-01)."
                )

        def per_col(col, expr=expr):
            def sub(m):
                prev, nm = m.group(1), m.group(2)
                rr = self.local[nm]
                if prev:
                    i = self.cols.index(col)
                    if i == 0:
                        return "0"
                    return f"{self.cols[i - 1]}{rr}"
                return f"{col}{rr}"

            return "=" + NAME.sub(sub, expr)

        vals = values if values is not None else self._evaluate(expr)
        _rr = self._write(name, label, per_col, vals, fmt, kind="calc", key=key, bold=close)
        # Declare the driver. `key` is the canonical name for WHAT this row computes; without one
        # the node is scoped to the block, which is enough to build the graph but not enough to
        # catch a re-derivation across blocks. Mandatory `key` is the end state.
        TREE.declare(
            key or f"{self.title}::{name}",
            label=label.strip(),
            unit="",
            row=_rr,
            kind="calc",
            # NAME has two groups, so findall yields (prior_marker, name) tuples -- take the name
            reads=[self.local[_m[1]] for _m in NAME.findall(expr) if _m[1] in self.local],
        )
        return _rr

    def carry(self, name: str, source: str, *, fmt=F.NUM):
        """Bring a subtotal down onto its own row before a SUM.

        Rationale: a total is clearer as a sum of subtotals brought down onto rows of their own
        than as one sum over every row above it.
        Label and unit are linked too, not retyped, so a renamed subtotal cannot drift from the
        row that carries it.
        """
        rr = self.local[source]
        row = self._write(
            name,
            f"@CARRY@{rr}",
            lambda col, rr=rr: f"={col}{rr}",
            self.vals[source],
            fmt,
            kind="link",
        )
        TREE.points_at(row, rr)
        self.c.ws.cell(row=row, column=1, value=f"=A{rr}")
        self.c.ws.cell(row=row, column=2, value=f"=B{rr}")
        return row

    def total(self, name: str, label: str, over, *, key=None, fmt=F.NUM, values=None):
        """A total over a run of block rows — the one case FAST allows to reach further."""
        rows = [self.local[nm] for nm in over]
        if rows != sorted(rows):
            raise BlockError(f"{self.title!r}: total {name!r} must sum rows in sheet order")
        if rows == list(range(rows[0], rows[-1] + 1)) and len(rows) > 1:
            per_col = lambda col: f"=SUM({col}{rows[0]}:{col}{rows[-1]})"
        else:
            per_col = lambda col: "=" + "+".join(f"{col}{r}" for r in rows)
        vals = (
            values
            if values is not None
            else [sum(self.vals[nm][i] for nm in over) for i in range(self.n)]
        )
        _rr = self._write(name, label, per_col, vals, fmt, kind="calc", key=key, bold=True)
        TREE.declare(
            key or f"{self.title}::{name}",
            label=label.strip(),
            unit="",
            row=_rr,
            kind="total",
            reads=rows,
        )
        return _rr

    # -- internals -----------------------------------------------------------------------
    def _evaluate(self, expr: str):
        """Mirror the expression in Python so verify has something to assert against.

        This is NOT the model's oracle — Excel and Python compile the same expression through
        two different engines, so it catches reference and syntax faults, not logic. The
        block's OUTPUT is what gets cross-checked against the independent engine series.
        """
        out = []
        for i in range(self.n):
            env = {}
            py = expr.replace("^", "**")

            def sub(m, i=i, env=env):
                prev, nm = m.group(1), m.group(2)
                v = self.vals[nm][i - 1] if prev else self.vals[nm][i]
                if prev and i == 0:
                    v = 0.0
                key = f"_{'p' if prev else ''}{nm}"
                env[key] = v
                return key

            out.append(float(eval(NAME.sub(sub, py), {"__builtins__": {}}, env)))
        return out

    def _write(self, name, label, per_col, values, fmt, *, kind, key=None, bold=False):
        if name in self.local:
            raise BlockError(f"{self.title!r}: {name!r} is already a row in this block")
        rowkey = key or f"_{self.title[:18]}_{name}"
        if key and key in self.reg:
            raise BlockError(
                f"calc key {key!r} already exists on this sheet. FAST 1.01-07: calculate only "
                f"once — link to the existing row instead of recomputing it."
            )
        prefix = "    " if kind == "link" else "  "
        self.c.row(
            rowkey, f"{prefix}{label}", lambda cc: per_col(cc.col), values=list(values), fmt=fmt
        )
        rr = self.c.rows()[rowkey]
        self.local[name] = rr
        self.kinds[name] = kind
        self.vals[name] = list(values)
        BLOCK_VALUES[rowkey] = list(values)
        self.reg[rowkey] = kind
        if key:
            self.reg[key] = kind
        if bold:
            # A total reads as a total: a rule above it, a double rule below, and a blank row
            # after — so the eye sees that this figure sums the rows immediately above.
            self.wb.style.bold(self.c.ws.cell(row=rr, column=1))
            # Span the full width: label, units, Open and every period column. It used to be
            # derived from the period count, which left the leading columns (and, after the
            # units-column shift, the last period) without a rule.
            from openpyxl.utils import column_index_from_string as _CIS

            _last = _CIS(self.wb.period_cols[-1])
            for j in range(1, _last + 1):
                # a rule above the total, and a DOUBLE rule below it — which is drawn as a
                # top border on the blank row that follows, the usual accounting presentation
                self.c.ws.cell(row=rr, column=j).border = self.wb.style.total_top
                self.c.ws.cell(row=rr + 1, column=j).border = self.wb.style.total_bottom
            self.c.skip_rows()
        return rr


def reset() -> None:
    """Forget every driver and row value recorded so far. The tree and the row values are
    module-level state; call this before building a second workbook in one process."""
    TREE.__init__()
    BLOCK_VALUES.clear()
