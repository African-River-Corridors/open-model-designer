"""Working capital: receivables and payables in days, and the movement; a cash buffer beside them.

    receivables  = revenue x receivable days / days in the period
    payables     = operating cost x payable days / days in the period
    working capital = receivables - payables
    movement     = working capital - the prior period's working capital   (a positive movement uses cash)
    cash buffer  = operating cost x buffer days / days in the period      (minimum cash: its own row)

The cash buffer is not working capital: it sits outside the working capital balance and its movement,
so it does not flow through CFADS as a working capital movement.

The first period's prior working capital is the opening balance, given as an input.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port
from ._plan_module import build_plan, plan_checks

INPUTS = (
    Port("revenue", "USD", "series"),
    Port("operating_cost", "USD", "series"),
    Port("receivable_days", "days", "scalar"),
    Port("payable_days", "days", "scalar"),
    Port("cash_buffer_days", "days", "scalar"),
    Port("days_in_period", "days", "scalar"),
    Port("opening_working_capital", "USD", "scalar"),
)
OUTPUTS = (
    Port("receivables", "USD", "series"),
    Port("payables", "USD", "series"),
    Port("cash_buffer", "USD", "series"),
    Port("working_capital", "USD", "series"),
    Port("working_capital_movement", "USD", "series"),
)
T = "Working capital"
KEYED = {
    "ar": "receivables",
    "ap": "payables",
    "buf": "cash_buffer",
    "wc": "working_capital",
    "move": "working_capital_movement",
}
PLAN = [
    ("link", "rev", "Revenue (USD)", "revenue"),
    ("link", "rd", "Receivable days (days)", "receivable_days"),
    ("link", "dpp", "Days in the period (days)", "days_in_period"),
    ("calc", "ar", "Receivables (USD)", "{rev}*{rd}/{dpp}"),
    ("link", "cost", "Operating cost (USD)", "operating_cost"),
    ("link", "pd", "Payable days (days)", "payable_days"),
    ("link", "dpp2", "Days in the period (days)", "days_in_period"),
    ("calc", "ap", "Payables (USD)", "{cost}*{pd}/{dpp2}"),
    ("link", "cost2", "Operating cost (USD)", "operating_cost"),
    ("link", "bd", "Cash buffer days (days)", "cash_buffer_days"),
    ("link", "dpp3", "Days in the period (days)", "days_in_period"),
    ("calc", "buf", "Cash buffer (USD)", "{cost2}*{bd}/{dpp3}"),
    ("relink", "ar2", "Receivables (USD)", "ar"),
    ("relink", "ap2", "Payables (USD)", "ap"),
    ("calc", "wc", "Working capital (USD)", "{ar2}-{ap2}"),
    ("lp", "wc_open", "Working capital, opening (USD)", "working_capital"),
    ("relink", "wc2", "Working capital (USD)", "wc"),
    ("calc", "move", "Working capital movement (USD)", "{wc2}-{wc_open}"),
]


def _run(inputs):
    rd, pd, bd, dpp = (
        float(inputs[k])
        for k in ("receivable_days", "payable_days", "cash_buffer_days", "days_in_period")
    )
    prev = float(inputs["opening_working_capital"])
    V: dict[str, list[float]] = {name: [] for _k, name, _l, _s in PLAN}
    for rev, cost in zip(inputs["revenue"], inputs["operating_cost"], strict=True):
        rev, cost = float(rev), float(cost)
        ar, ap, buf = rev * rd / dpp, cost * pd / dpp, cost * bd / dpp
        wc = ar - ap
        row = {"rev": rev, "rd": rd, "dpp": dpp, "ar": ar, "cost": cost, "pd": pd, "dpp2": dpp, "ap": ap,
               "cost2": cost, "bd": bd, "dpp3": dpp, "buf": buf, "ar2": ar, "ap2": ap, "wc": wc,
               "wc_open": prev, "wc2": wc, "move": wc - prev}  # fmt: skip
        prev = wc
        for k, v in row.items():
            V[k].append(v)
    return V


def oracle(inputs: dict) -> dict[str, list[float]]:
    V = _run(inputs)
    return {port: V[name] for name, port in KEYED.items()}


def build(ctx: BuildContext) -> None:
    build_plan(
        ctx, T, PLAN, _run(ctx.inputs), KEYED, {"working_capital": "opening_working_capital"}
    )


def checks(ctx: BuildContext) -> dict[str, str]:
    c = ctx.calcs
    r = c.rows()
    cols = list(c.workbook.period_cols)
    first = cols[0]
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col) if "{col}" in src[port] else src[port]  # noqa: E731
    K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
    kr = lambda port: r[ctx.key(port)]  # noqa: E731
    zero = [0.0] * ctx.n

    def prev(x):  # working capital of the period before, from the output row itself
        return (
            src["opening_working_capital"]
            if x.i == 1
            else f"{cols[x.i - 2]}{kr('working_capital')}"
        )

    c.section("Checks")
    c.row("chk_wc", "  Check - balances and movement re-derived from the ports (USD)",
          lambda x: f"=ABS({K('receivables', x)}-{S('revenue', x)}*{S('receivable_days', x)}/{S('days_in_period', x)})"
                    f"+ABS({K('payables', x)}-{S('operating_cost', x)}*{S('payable_days', x)}/{S('days_in_period', x)})"
                    f"+ABS({K('cash_buffer', x)}-{S('operating_cost', x)}*{S('cash_buffer_days', x)}/{S('days_in_period', x)})"
                    f"+ABS({K('working_capital', x)}-({K('receivables', x)}-{K('payables', x)}))"
                    f"+ABS({K('working_capital_movement', x)}-({K('working_capital', x)}-{prev(x)}))", values=zero)  # fmt: skip
    c.row("chk_cumulative", "  Check - opening working capital plus the movements equals working capital (USD)",
          lambda x: f"=ABS({K('working_capital', x)}-({src['opening_working_capital']}"
                    f"+SUM(${first}{kr('working_capital_movement')}:{x.col}{kr('working_capital_movement')})))", values=zero)  # fmt: skip
    label = plan_checks(ctx, T, PLAN, KEYED, lambda port, x: prev(x))
    return {
        "wc": "Check - balances and movement re-derived",
        "cumulative": "Check - opening working capital plus the movements equals working capital",
        "rows": label,
    }


WORKING_CAPITAL = Module(
    name="working_capital",
    version="0.1.0",
    scope={
        "in": [
            "Receivables and payables as days of revenue and of operating cost in a period of given length",
            "A cash buffer (minimum cash) as days of operating cost, on its own row outside the working capital balance and movement",
            "The movement in working capital, positive when it uses cash, from an opening balance",
        ],
        "out": [
            "Inventory, prepayments, accruals and other working-capital items (add a module per item)",
            "Bad debts and VAT (see the VAT account module)",
            "A buffer sized to a target amount rather than to days of cost, and the buffer's own funding (see the DSRA and cash waterfall modules)",
            "Payables driven by the non-payroll share of cost only (they are driven by total operating cost)",
            "Days that vary by period (the days are one value each)",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "revenue": [1000.0, 1200.0, 1100.0, 1300.0],
        "operating_cost": [600.0, 640.0, 620.0, 700.0],
        "receivable_days": 45.0,
        "payable_days": 30.0,
        "cash_buffer_days": 15.0,
        "days_in_period": 90.0,
        "opening_working_capital": 100.0,
    },
    golden=Golden(
        inputs={
            "revenue": [900.0, 1200.0, 1500.0, 1000.0],
            "operating_cost": [540.0, 600.0, 720.0, 500.0],
            "receivable_days": 30.0,
            "payable_days": 45.0,
            "cash_buffer_days": 10.0,
            "days_in_period": 90.0,
            "opening_working_capital": 50.0,
        },
        outputs={
            "receivables": [300.0, 400.0, 500.0, 333.3333333333333],
            "payables": [270.0, 300.0, 360.0, 250.0],
            "cash_buffer": [60.0, 66.66666666666667, 80.0, 55.55555555555556],
            "working_capital": [30.0, 100.0, 140.0, 83.33333333333333],
            "working_capital_movement": [-20.0, 70.0, 40.0, -56.666666666666664],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); without-buffer working capital as ruled (the buffer is its own row); working in docs/golden-cases/working_capital.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = WORKING_CAPITAL
