"""Distribution waterfall: return of capital at a hurdle rate, then a promote split.

    accrual     = opening hurdle balance x ((1 + hurdle rate)^period years - 1)       hurdle rate is per year
    hurdle balance before paying = opening + accrual + contributions                  (contributions at period end)
    tier 1      = min(max(distributable cash, 0), hurdle balance before paying)       paid to the investor
    hurdle balance, closing = before paying - tier 1
    residual    = max(distributable cash, 0) - tier 1                                 only when the hurdle is cleared
    promote     = promote share x residual                                           paid to the sponsor
    investor    = tier 1 + (1 - promote share) x residual

The hurdle balance is the equity contributed, compounded at the hurdle rate, less what tier 1 has paid back.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port
from ._plan_module import build_plan, plan_checks

INPUTS = (
    Port("distributable_cash", "USD", "series"),
    Port("equity_contribution", "USD", "series"),
    Port("hurdle_rate", "ratio/year", "scalar"),
    Port("period_years", "years", "scalar"),
    Port("promote_share", "ratio", "scalar"),
    Port("opening_hurdle_balance", "USD", "scalar"),
)
OUTPUTS = (
    Port("hurdle_accrual", "USD", "series"),
    Port("hurdle_balance_closing", "USD", "series"),
    Port("tier1_distribution", "USD", "series"),
    Port("residual_cash", "USD", "series"),
    Port("sponsor_promote", "USD", "series"),
    Port("investor_distribution", "USD", "series"),
)
T = "Distribution waterfall"
KEYED = {
    "accrual": "hurdle_accrual",
    "close": "hurdle_balance_closing",
    "t1": "tier1_distribution",
    "resid": "residual_cash",
    "promote": "sponsor_promote",
    "inv": "investor_distribution",
}
PLAN = [
    ("lp", "open", "Hurdle balance, opening (USD)", "hurdle_balance_closing"),
    ("link", "h", "Hurdle rate per year (ratio/year)", "hurdle_rate"),
    ("link", "yrs", "Years in the period (years)", "period_years"),
    ("calc", "accrual", "Accrual at the hurdle rate (USD)", "{open}*((1+{h})^{yrs}-1)"),
    ("lp", "open2", "Hurdle balance, opening (USD)", "hurdle_balance_closing"),
    ("relink", "accrual2", "Accrual at the hurdle rate (USD)", "accrual"),
    ("link", "contrib", "Equity contributed (USD)", "equity_contribution"),
    ("calc", "before", "Hurdle balance before paying (USD)", "{open2}+{accrual2}+{contrib}"),
    ("link", "cash", "Distributable cash (USD)", "distributable_cash"),
    (
        "calc",
        "t1",
        "Tier 1: paid to the investor until the hurdle is cleared (USD)",
        "MIN(MAX({cash},0),{before})",
    ),
    ("relink", "before2", "Hurdle balance before paying (USD)", "before"),
    ("relink", "t1b", "Tier 1: paid to the investor (USD)", "t1"),
    ("calc", "close", "Hurdle balance, closing (USD)", "{before2}-{t1b}"),
    ("link", "cash2", "Distributable cash (USD)", "distributable_cash"),
    ("relink", "t1c", "Tier 1: paid to the investor (USD)", "t1"),
    ("calc", "resid", "Residual cash above the hurdle (USD)", "MAX({cash2},0)-{t1c}"),
    ("link", "share", "Promote share to the sponsor (ratio)", "promote_share"),
    ("calc", "promote", "Promote paid to the sponsor (USD)", "{share}*{resid}"),
    ("relink", "t1d", "Tier 1: paid to the investor (USD)", "t1"),
    ("relink", "resid2", "Residual cash above the hurdle (USD)", "resid"),
    ("relink", "promote2", "Promote paid to the sponsor (USD)", "promote"),
    ("calc", "inv", "Paid to the investor in total (USD)", "{t1d}+{resid2}-{promote2}"),
]


def _run(inputs):
    h, yrs = float(inputs["hurdle_rate"]), float(inputs["period_years"])
    share, bal = float(inputs["promote_share"]), float(inputs["opening_hurdle_balance"])
    V: dict[str, list[float]] = {name: [] for _k, name, _l, _s in PLAN}
    for cash, contrib in zip(
        inputs["distributable_cash"], inputs["equity_contribution"], strict=True
    ):
        cash, contrib = float(cash), float(contrib)
        accrual = bal * ((1 + h) ** yrs - 1)
        before = bal + accrual + contrib
        t1 = min(max(cash, 0.0), before)
        close = before - t1
        resid = max(cash, 0.0) - t1
        promote = share * resid
        row = {"open": bal, "h": h, "yrs": yrs, "accrual": accrual, "open2": bal, "accrual2": accrual,
               "contrib": contrib, "before": before, "cash": cash, "t1": t1, "before2": before, "t1b": t1,
               "close": close, "cash2": cash, "t1c": t1, "resid": resid, "share": share, "promote": promote,
               "t1d": t1, "resid2": resid, "promote2": promote, "inv": t1 + resid - promote}  # fmt: skip
        bal = close
        for k, v in row.items():
            V[k].append(v)
    return V


def oracle(inputs: dict) -> dict[str, list[float]]:
    V = _run(inputs)
    return {port: V[name] for name, port in KEYED.items()}


def build(ctx: BuildContext) -> None:
    build_plan(
        ctx, T, PLAN, _run(ctx.inputs), KEYED, {"hurdle_balance_closing": "opening_hurdle_balance"}
    )


def checks(ctx: BuildContext) -> dict[str, str]:
    c = ctx.calcs
    r = c.rows()
    cols = list(c.workbook.period_cols)
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col) if "{col}" in src[port] else src[port]  # noqa: E731
    K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
    kr = lambda port: r[ctx.key(port)]  # noqa: E731
    zero = [0.0] * ctx.n

    def prev(x):  # hurdle balance of the period before, from the output row itself
        return (
            src["opening_hurdle_balance"]
            if x.i == 1
            else f"{cols[x.i - 2]}{kr('hurdle_balance_closing')}"
        )

    def before(x):
        return f"({prev(x)}*(1+{S('hurdle_rate', x)})^{S('period_years', x)}+{S('equity_contribution', x)})"

    cash = lambda x: f"MAX({S('distributable_cash', x)},0)"  # noqa: E731
    c.section("Checks")
    c.row("chk_hurdle", "  Check - hurdle balance and the tier 1 payment re-derived from the ports (USD)",
          lambda x: f"=ABS({K('hurdle_accrual', x)}-{prev(x)}*((1+{S('hurdle_rate', x)})^{S('period_years', x)}-1))"
                    f"+ABS({K('tier1_distribution', x)}-MIN({cash(x)},{before(x)}))"
                    f"+ABS({K('hurdle_balance_closing', x)}-({before(x)}-{K('tier1_distribution', x)}))"
                    f"+MAX(-{K('hurdle_balance_closing', x)},0)", values=zero)  # fmt: skip
    c.row("chk_split", "  Check - the cash paid out equals the distributable cash and the promote split holds (USD)",
          lambda x: f"=ABS({K('investor_distribution', x)}+{K('sponsor_promote', x)}-{cash(x)})"
                    f"+ABS({K('sponsor_promote', x)}-{S('promote_share', x)}*({cash(x)}-{K('tier1_distribution', x)}))"
                    f"+ABS({K('residual_cash', x)}-({cash(x)}-{K('tier1_distribution', x)}))", values=zero)  # fmt: skip
    c.row("chk_priority", "  Check - no residual is paid while the hurdle balance is outstanding (USD)",
          lambda x: f"=MIN({K('residual_cash', x)},{K('hurdle_balance_closing', x)})", values=zero)  # fmt: skip
    label = plan_checks(ctx, T, PLAN, KEYED, lambda port, x: prev(x))
    return {
        "hurdle": "Check - hurdle balance and the tier 1 payment re-derived",
        "split": "Check - the cash paid out equals the distributable cash and the promote split holds",
        "priority": "Check - no residual is paid while the hurdle balance is outstanding",
        "rows": label,
    }


DISTRIBUTION_WATERFALL = Module(
    name="distribution_waterfall",
    version="0.1.0",
    scope={
        "in": [
            "A hurdle balance: equity contributed at period end, compounded at an annual hurdle rate over the period's length in years",
            "Tier 1: all distributable cash to the investor until the hurdle balance is cleared",
            "Tier 2: the residual split between the sponsor (promote share) and the investor",
            "A brought-forward hurdle balance",
        ],
        "out": [
            "More than one hurdle (a second promote step at a higher IRR)",
            "A GP catch-up tier between the hurdle and the split (a two-tier promote only), clawback and the tax on distributions",
            "Carrying negative distributable cash forward: it is floored to nil and dropped, and does not add to the hurdle balance",
            "Dated flows inside a period (flows are at period end; the length of a period is one value)",
            "Distributable cash itself (it comes from the cash waterfall) and lock-up",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "distributable_cash": [0.0, 200.0, 500.0, 900.0],
        "equity_contribution": [800.0, 0.0, 0.0, 0.0],
        "hurdle_rate": 0.1,
        "period_years": 1.0,
        "promote_share": 0.2,
        "opening_hurdle_balance": 0.0,
    },
    golden=Golden(
        inputs={
            "distributable_cash": [0.0, -100.0, 1500.0, 500.0],
            "equity_contribution": [1000.0, 0.0, 0.0, 100.0],
            "hurdle_rate": 0.21,
            "period_years": 0.5,
            "promote_share": 0.2,
            "opening_hurdle_balance": 0.0,
        },
        outputs={
            "hurdle_accrual": [0.0, 100.0, 110.0, 0.0],
            "hurdle_balance_closing": [1000.0, 1100.0, 0.0, 0.0],
            "tier1_distribution": [0.0, 0.0, 1210.0, 100.0],
            "residual_cash": [0.0, 0.0, 290.0, 400.0],
            "sponsor_promote": [0.0, 0.0, 58.0, 80.0],
            "investor_distribution": [0.0, 0.0, 1442.0, 420.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); negative cash floored and dropped, a contribution after clearance is returned in the same period; working in docs/golden-cases/distribution_waterfall_2.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = DISTRIBUTION_WATERFALL
