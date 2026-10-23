"""CFADS, cash flow available for debt service, before and after tax.

    CFADS before tax = revenue - operating cost - working capital movement
    CFADS            = CFADS before tax - tax paid

A positive working capital movement uses cash; a negative one (a release) adds to CFADS.
Debt service, capex and distributions sit below CFADS: they are not deducted here.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port
from ._plan_module import build_plan, plan_checks

INPUTS = (
    Port("revenue", "USD", "series"),
    Port("operating_cost", "USD", "series"),
    Port("working_capital_movement", "USD", "series"),
    Port("tax_paid", "USD", "series"),
)
OUTPUTS = (
    Port("cfads_pre_tax", "USD", "series"),
    Port("cfads", "USD", "series"),
)
T = "CFADS"
KEYED = {"pre": "cfads_pre_tax", "cfads": "cfads"}
PLAN = [
    ("link", "rev", "Revenue (USD)", "revenue"),
    ("link", "cost", "Operating cost (USD)", "operating_cost"),
    ("link", "wcm", "Working capital movement (USD)", "working_capital_movement"),
    ("calc", "pre", "CFADS before tax (USD)", "{rev}-{cost}-{wcm}"),
    ("relink", "pre2", "CFADS before tax (USD)", "pre"),
    ("link", "tax", "Tax paid (USD)", "tax_paid"),
    ("calc", "cfads", "CFADS (USD)", "{pre2}-{tax}"),
]


def _run(inputs):
    V: dict[str, list[float]] = {name: [] for _k, name, _l, _s in PLAN}
    for rev, cost, wcm, tax in zip(
        inputs["revenue"],
        inputs["operating_cost"],
        inputs["working_capital_movement"],
        inputs["tax_paid"],
        strict=True,
    ):
        rev, cost, wcm, tax = float(rev), float(cost), float(wcm), float(tax)
        pre = rev - cost - wcm
        row = {
            "rev": rev,
            "cost": cost,
            "wcm": wcm,
            "pre": pre,
            "pre2": pre,
            "tax": tax,
            "cfads": pre - tax,
        }
        for k, v in row.items():
            V[k].append(v)
    return V


def oracle(inputs: dict) -> dict[str, list[float]]:
    V = _run(inputs)
    return {port: V[name] for name, port in KEYED.items()}


def build(ctx: BuildContext) -> None:
    build_plan(ctx, T, PLAN, _run(ctx.inputs), KEYED, {})


def checks(ctx: BuildContext) -> dict[str, str]:
    c = ctx.calcs
    r = c.rows()
    cols = list(c.workbook.period_cols)
    first = cols[0]
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col)  # noqa: E731
    K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
    kr = lambda port: r[ctx.key(port)]  # noqa: E731
    zero = [0.0] * ctx.n

    def total(port, x):  # the port's cumulative sum to this period
        sheet, ref = src[port].split("!", 1)
        row = ref.removeprefix("{col}")
        return f"SUM({sheet}!${first}{row}:{x.col}{row})"

    c.section("Checks")
    c.row("chk_cfads", "  Check - CFADS before and after tax re-derived from the ports (USD)",
          lambda x: f"=ABS({K('cfads_pre_tax', x)}-({S('revenue', x)}-{S('operating_cost', x)}-{S('working_capital_movement', x)}))"
                    f"+ABS({K('cfads', x)}-({S('revenue', x)}-{S('operating_cost', x)}-{S('working_capital_movement', x)}-{S('tax_paid', x)}))"
                    f"+ABS({K('cfads_pre_tax', x)}-{K('cfads', x)}-{S('tax_paid', x)})", values=zero)  # fmt: skip
    c.row("chk_cumulative", "  Check - cumulative CFADS equals cumulative revenue less costs, working capital and tax (USD)",
          lambda x: f"=ABS(SUM(${first}{kr('cfads')}:{x.col}{kr('cfads')})-({total('revenue', x)}-{total('operating_cost', x)}"
                    f"-{total('working_capital_movement', x)}-{total('tax_paid', x)}))", values=zero)  # fmt: skip
    label = plan_checks(ctx, T, PLAN, KEYED, lambda port, x: "0")
    return {
        "cfads": "Check - CFADS before and after tax re-derived",
        "cumulative": "Check - cumulative CFADS equals cumulative revenue less costs, working capital and tax",
        "rows": label,
    }


CFADS = Module(
    name="cfads",
    version="0.1.0",
    scope={
        "in": [
            "CFADS before tax: revenue less operating cost less the working capital movement",
            "CFADS after tax: CFADS before tax less tax paid",
            "A working capital release (negative movement) adding to CFADS",
        ],
        "out": [
            "Maintenance capex and movements in non-debt reserves: netted upstream, there are no inputs for them here",
            "Capex, debt service, reserve transfers and distributions (all below CFADS)",
            "Tax calculation (see the tax engine) and its timing: tax paid is an input",
            "Insurance proceeds, grants, and other non-operating receipts",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "revenue": [0.0, 1000.0, 1200.0, 1100.0],
        "operating_cost": [0.0, 400.0, 420.0, 410.0],
        "working_capital_movement": [0.0, 150.0, 40.0, -30.0],
        "tax_paid": [0.0, 0.0, 90.0, 120.0],
    },
    golden=Golden(
        inputs={
            "revenue": [800.0, 1000.0, 1200.0, 900.0],
            "operating_cost": [350.0, 400.0, 450.0, 380.0],
            "working_capital_movement": [120.0, 60.0, -30.0, -80.0],
            "tax_paid": [0.0, 40.0, 100.0, 70.0],
        },
        outputs={
            "cfads_pre_tax": [330.0, 540.0, 780.0, 600.0],
            "cfads": [330.0, 500.0, 680.0, 530.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/cfads.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = CFADS
