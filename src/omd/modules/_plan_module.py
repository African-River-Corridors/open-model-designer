"""Shared builder for modules written as an ordered plan of FAST block rows.

A plan is a list of entries `(kind, name, label, spec)`:
- ("link", name, label, port): the input port, restated as a link row; "@key" links a Calcs row
  the module wrote itself outside the block (values come from V)
- ("relink", name, label, other): an earlier calc row of the block, restated just above where used
- ("calc", name, label, expr): one calculation over block rows, `{name}` placeholders
- ("lp", name, label, port): the prior-period value of the output port's closing row (a corkscrew)

`build_plan` writes the rows and sets the Open cell of every corkscrew's closing row. `plan_checks`
returns the checks identity: every row is re-derived from its own inputs (a link from its port, a
calc from its expression over the cells actually in the sheet, a corkscrew start from the caller's
independent balance function). A module adds its own independent checks beside it.
"""

from __future__ import annotations

import re

NAME = re.compile(r"\{(\w+)\}")


def build_plan(ctx, title, plan, V, keyed, openings):
    """keyed: calc name -> output port; openings: closing output port -> opening input port."""
    c = ctx.calcs
    b = ctx.block(title)
    first = c.next_row
    pos = {name: i for i, (_k, name, _l, _s) in enumerate(plan)}
    row_of = {port: first + pos[name] for name, port in keyed.items()}
    for kind, name, label, spec in plan:
        if kind == "lp":
            b.link_prev(name, row_of[spec], label, values=V[name])
        elif kind == "link" and spec.startswith("@"):
            b.link(name, spec[1:], label, values=V[name])
        elif kind == "link":
            b.link(name, ctx.source(spec), label, values=ctx.values(spec))
        elif kind == "relink":
            b.relink(name, spec, label)
        else:
            b.calc(
                name,
                label,
                spec,
                key=ctx.key(keyed[name]) if name in keyed else None,
                values=V[name],
            )
    for port, opening in openings.items():
        assert c.rows()[ctx.key(port)] == row_of[port], f"{port}: predicted row moved"
        c.ws[f"{c.workbook.open_col}{row_of[port]}"] = f"={ctx.source(opening)}"
    return b


def plan_checks(ctx, title, plan, keyed, balance, absum_name="chk_rows"):
    """Write the identity check row; returns (check key, label prefix). `balance(port, x)` gives the
    independent opening value of a corkscrew whose closing port is `port`."""
    c = ctx.calcs
    r = c.rows()
    src = {p.name: ctx.source(p.name) for p in ctx.module.inputs}

    def S(port, x):
        return src[port].format(col=x.col) if "{col}" in src[port] else src[port]

    def cell(name, x):
        if name in keyed:
            return f"{x.col}{r[ctx.key(keyed[name])]}"
        return f"{x.col}{r[f'_{title[:18]}_{name}']}"

    def identity(x):
        parts = []
        for kind, name, _l, spec in plan:
            if kind == "lp":
                parts.append(f"{cell(name, x)}-{balance(spec, x)}")
            elif kind == "link" and spec.startswith("@"):
                parts.append(f"{cell(name, x)}-{x.col}{r[spec[1:]]}")
            elif kind == "link":
                parts.append(f"{cell(name, x)}-{S(spec, x)}")
            elif kind == "relink":
                parts.append(f"{cell(name, x)}-{cell(spec, x)}")
            else:
                ex = NAME.sub(lambda m: cell(m.group(1), x), spec)
                parts.append(f"{cell(name, x)}-({ex})")
        return "=" + "+".join(f"ABS({p})" for p in parts)

    label = "Check - every row re-derived from its inputs"
    c.row(absum_name, f"  {label} (USD)", identity, values=[0.0] * ctx.n)
    return label
