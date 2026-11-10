# Design note: extra sheets, sheet sets, row addresses and a solver

Status: design, for build. Date: 2026-11-10.

## Why

A model that grew up outside `compose` writes its own sheets: a results sheet, a case table, a checks sheet. Today it can only do that by reaching into the builder's private parts: the openpyxl book behind `Workbook`,
the period column list, the Calcs write cursor. Those parts change without notice, so the model breaks on the next
OMD release. A model also has to keep its own sheet names and tab order, and some models carry a value the build
solves (for example a tariff set so a target return is met).

This note fixes the public API for those four needs. Each is generic. The examples are synthetic.

What already exists and stays as it is: `Workbook.period_cols`, `open_col`, `all_cols`, `set_layout`,
`add_sheet`, `sheet`, `sheet_names`, `order_sheets`, `inputs_sheet`; `Calcs.ws`, `next_row`, `skip_rows`,
`header_row`, `last_col`, `workbook`, `rows()`.

## 1. A period sheet: an extra sheet in house style

**Need.** A sheet whose columns line up with Calcs: the same Open column and period columns, the same header row,
white fill, a title, frozen panes. Rows on it link to Calcs, one formula shifted across the periods.

**API.**

```python
ps = wb.period_sheet("Annual view", title="Annual view", subtitle=None)  # -> PeriodSheet
ps.section("Revenue")  # bold accent header with a rule
ps.note("Each line links to its Calcs row.")  # italic muted logic note
ps.row("Revenue", lambda c: f"={calcs.address('rev', col=c.col)}", values=rev, fmt=F.NUM)
ps.skip_rows(2)
ps.next_row, ps.header_row, ps.ws, ps.name  # read-only cursor and handles
```

**Shape.** `PeriodSheet` is the base class; `Calcs` becomes `PeriodSheet` plus the timeline rows, row keys and the
"one Calcs per book" rule. `PeriodSheet.row` returns the row number; it takes an optional `key` so a period sheet
can be addressed like Calcs (`ps.address(key, ...)`). The header row, the column letters and the formats all come
from the workbook and its style profile, so a period sheet cannot drift from Calcs.

**Rules.** A period sheet is a presentation sheet: `audit_offsheet` and `audit_hardcodes` treat it as one (no typed
numbers; it may read Calcs). `Workbook.statement` stays; it is a period sheet with a fixed block form.

## 2. A row's address

**Need.** Write a formula on another sheet that points at a Calcs row, without knowing the row number or the
sheet's quoting rules.

**API** (on `PeriodSheet`, so on Calcs too):

```python
calcs.row_of("rev")  # 41
calcs.address("rev", col="E")  # "Calcs!$E$41"   absolute, sheet-qualified
calcs.address("rev", period=1)  # the first period column
calcs.address("rev", open=True)  # the Open column
calcs.address("rev", col="E", absolute=False, sheet=False)  # "E41"
calcs.span("rev")  # "Calcs!$E$41:$AF$41"   every period column
wb.worksheets  # every worksheet, in tab order (read-only tuple)
```

A sheet name with a space or a quote is quoted (`'Key results'!$E$41`). An unknown key raises `KeyError` naming
the key. Exactly one of `col`, `period`, `open` is given (`span` takes none).

## 3. A sheet set: a template keeps its own sheets

**Need.** A template names its sheets and fixes their tab order. Renaming a sheet in openpyxl does not rewrite the
formulas that point at it, so a rename without a rewrite leaves `#REF!` all over the book.

**API.**

```python
SHEETS = SheetSet(
    [  # build name -> name the reader sees, in tab order
        ("Cover", "Title"),
        ("Outputs", "Key results"),
        ("Inputs", "Inputs"),
        ("Calcs", "Workings"),
        ("Checks", "Checks"),
    ]
)
wb.apply_sheet_set(SHEETS)
```

`apply_sheet_set` does all of this, or raises and changes nothing:

1. The set names every sheet in the book exactly once (no sheet left out, none extra).
2. Every formula that names an old sheet is rewritten to the new name, quoted when needed.
   Plain (`Calcs!A1`) and quoted (`'Calcs'!A1`) references are both rewritten. An old name that is a prefix of
   another (`Calc` and `Calcs`) is handled by matching whole sheet references, not substrings.
3. The sheets are renamed and put in the set's order. `Calcs.name` and every `PeriodSheet.name` follow.
4. A scan proves no formula still names an old sheet.

`compose` gains `sheets: SheetSet | None`; when given it applies the set last. Its defaults are today's names.

A **template** is then: a sheet set, a style profile, a layout (`set_layout`) and the steps or build code. A model
that keeps a layout of its own is a template in its private library, built on this API; it is not a fork of OMD.

## 4. A solved value

**Need.** Some inputs are not assumptions: the build solves them so a target holds (a tariff that gives a target
equity return, a loan size that meets a cover ratio). The value is written to the workbook as a number. The
workbook must say, live, when an edited input means the value needs solving again.

**API** (`omd.solve`, engine core, not a library module):

```python
from omd.solve import bisect_threshold, solve_check, solved_input

s = bisect_threshold(
    f,  # x -> residual; f is non-increasing in x
    lo=0.5,
    hi=2.0,  # the bracket; hi grows by `grow` until f(hi) <= tol
    tol=1e-6,  # done when f(x) <= tol
    steps=60,  # fixed number of halvings: the answer is exact and repeatable
    grow=2.0,
    cap=64.0,
)
s.value  # the smallest x found with f(x) <= tol (the `hi` side of the final bracket)
s.lo, s.hi, s.residual, s.steps, s.evaluations

ref = solved_input(
    wb, "tariff_mult", "Tariff multiplier", s, fmt=F.RATE
)  # an input cell, marked SOLVED
solve_check(calcs, "tariff_check", "Tariff solve still holds", residual_formula, tol=1e-6)
```

**Rules.**

- The algorithm is fixed and documented, so a model moved onto it gets the same bits it had before: expand
  `hi` (and move `lo` up to the old `hi`) while `f(hi) > tol`, failing past `cap`; fail if `f(lo) <= tol`;
  then `steps` halvings, keeping `hi` on the side where `f <= tol`. No early exit.
- `solved_input` writes the value on the Inputs sheet with a distinct mark (a "SOLVED" note in the unit or source
  column) so a reader does not edit it as an assumption.
- `solve_check` writes a Calcs check row that reads 0 when the live residual is within `tol` and 1 when it is not.
  The Summary gathers it like any check. Edit an input that moves the residual and the check goes to 1:
  rebuild to re-solve.
- The golden case comes from a function with a closed-form root, not from the solver itself.

Why not the `Stored` sheet: a stored result is a snapshot. A solved value has a residual the workbook can compute
live, so the check is exact rather than "some input changed".

## 5. Proving a move is exact (for any model)

A model moving onto OMD from another builder proves the move with a frozen baseline in its own repo: every numeric
cell of the old build, compared bit for bit with the new build through a declared old-to-new address map. The map is
built from structure (row keys, sheet names), never from values. New rows that OMD adds (the Calcs timeline rows)
are listed as new, by key. This tooling lives with the model, not in OMD; OMD's part is that `rows()` on every
period sheet gives the keys the map is built from.

## Out of scope

- Two instances of one module in one book (issue #7).
- Any national tax logic: that belongs in a private library.
- Changing a released library module (they are write-once).

## Tickets

- Set A (`src/omd/sheet/workbook.py`, `tests/sheet/`): the period sheet; row addresses and `worksheets`; the sheet
  set and `apply_sheet_set`.
- Set B (new files, plus `src/omd/template.py`): `omd.solve` with `solved_input` and `solve_check`, built on the public
  `Workbook.inputs` and `Calcs.row` only; then `compose(sheets=)`, once the sheet set from set A is merged.
