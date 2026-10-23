"""Returns and valuation: XIRR and NPV by holder, and equity payback, on dated flows.

For each holder (the project, and the equity investor), from cash flows with dates:

    years since the first flow = (date - first date) / days per year
    NPV   = sum of flow x 1 / (1 + discount rate)^years since the first flow     (discounted to the first flow's date)
    XIRR  = the annual rate at which that NPV is nil, on a 365-day year (the XIRR function's convention)

Equity payback is the first period in which cumulative equity cash flow is nil or positive; 0 if it never is.
A result of one value per holder is written on every period's column (the same number across the row).
Dates are whole days (XIRR drops any fraction of a day). Set `days_per_year` to 365 so NPV and XIRR use the same day count.
"""

from __future__ import annotations

import math

from ..module import BuildContext, Golden, Module, Port

INPUTS = (
    Port("project_cash_flow", "USD", "series"),
    Port("equity_cash_flow", "USD", "series"),
    Port("flow_dates", "days", "series"),
    Port("project_discount_rate", "ratio/year", "scalar"),
    Port("equity_discount_rate", "ratio/year", "scalar"),
    Port("days_per_year", "days", "scalar"),
)
OUTPUTS = (
    Port("project_xirr", "ratio/year", "series"),
    Port("equity_xirr", "ratio/year", "series"),
    Port("project_npv", "USD", "series"),
    Port("equity_npv", "USD", "series"),
    Port("equity_cumulative_cash", "USD", "series"),
    Port("equity_payback_period", "periods", "series"),
)
T = "Returns"


def xirr(flows, dates) -> float:
    """The rate r with sum flow / (1 + r)^((date - date0) / 365) = 0, by bisection (as XIRR defines it)."""
    d0 = math.floor(dates[0])
    t = [(math.floor(d) - d0) / 365.0 for d in dates]
    f = lambda r: sum(c / (1 + r) ** y for c, y in zip(flows, t, strict=True))  # noqa: E731
    lo, hi = -0.999, 1000.0
    if f(lo) * f(hi) > 0:
        raise ValueError("XIRR: the flows have no sign change, so no rate makes their NPV nil")
    for _ in range(300):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def _npv(flows, dates, rate, dpy):
    return sum(
        c / (1 + rate) ** ((math.floor(d) - math.floor(dates[0])) / dpy)
        for c, d in zip(flows, dates, strict=True)
    )


def _cum(xs):
    out, run = [], 0.0
    for x in xs:
        run += x
        out.append(run)
    return out


def oracle(inputs: dict) -> dict[str, list[float]]:
    p = [float(x) for x in inputs["project_cash_flow"]]
    e = [float(x) for x in inputs["equity_cash_flow"]]
    d = [float(x) for x in inputs["flow_dates"]]
    dpy = float(inputs["days_per_year"])
    n = len(p)
    cum = _cum(e)
    payback = float(sum(1 for c in cum if c < 0) + 1) if cum[-1] >= 0 else 0.0
    return {
        "project_xirr": [xirr(p, d)] * n,
        "equity_xirr": [xirr(e, d)] * n,
        "project_npv": [_npv(p, d, float(inputs["project_discount_rate"]), dpy)] * n,
        "equity_npv": [_npv(e, d, float(inputs["equity_discount_rate"]), dpy)] * n,
        "equity_cumulative_cash": cum,
        "equity_payback_period": [payback] * n,
    }


def build(ctx: BuildContext) -> None:
    c = ctx.calcs
    n = ctx.n
    cols = list(c.workbook.period_cols)
    a, z = cols[0], cols[-1]
    want = oracle(ctx.inputs)
    p, e = ctx.values("project_cash_flow"), ctx.values("equity_cash_flow")
    d, dpy = ctx.values("flow_dates"), float(ctx.inputs["days_per_year"])
    src = {q.name: ctx.source(q.name) for q in INPUTS}
    S = lambda port, x: src[port].format(col=x.col) if "{col}" in src[port] else src[port]  # noqa: E731
    years = [(math.floor(x) - math.floor(d[0])) / dpy for x in d]
    pdf = [1 / (1 + float(ctx.inputs["project_discount_rate"])) ** y for y in years]
    edf = [1 / (1 + float(ctx.inputs["equity_discount_rate"])) ** y for y in years]
    neg = [1.0 if x < 0 else 0.0 for x in want["equity_cumulative_cash"]]
    R: dict[str, int] = {}

    def add(name, label, f, values, key=None):
        R[name] = c.next_row
        c.row(key or name, label, f, values=values)

    rng = lambda k: f"${a}${R[k]}:${z}${R[k]}"  # noqa: E731
    c.skip_rows()
    c.section(T)
    add("r_pcf", "    Project cash flow (USD)", lambda x: "=" + S("project_cash_flow", x), p)
    add("r_ecf", "    Equity cash flow (USD)", lambda x: "=" + S("equity_cash_flow", x), e)
    add("r_date", "    Flow date (days)", lambda x: "=" + S("flow_dates", x), d)
    add("r_prate", "    Project discount rate (ratio/year)", lambda x: "=" + S("project_discount_rate", x), [float(ctx.inputs["project_discount_rate"])] * n)  # fmt: skip
    add("r_erate", "    Equity discount rate (ratio/year)", lambda x: "=" + S("equity_discount_rate", x), [float(ctx.inputs["equity_discount_rate"])] * n)  # fmt: skip
    add("r_dpy", "    Days per year (days)", lambda x: "=" + S("days_per_year", x), [dpy] * n)
    add("r_years", "  Years since the first flow (years)", lambda x: f"=(INT({x.col}{R['r_date']})-INT(${a}{R['r_date']}))/{x.col}{R['r_dpy']}", years)  # fmt: skip
    add("r_pdf", "  Project discount factor (ratio)", lambda x: f"=1/(1+{x.col}{R['r_prate']})^{x.col}{R['r_years']}", pdf)  # fmt: skip
    add("r_ppv", "  Project present value of the flow (USD)", lambda x: f"={x.col}{R['r_pcf']}*{x.col}{R['r_pdf']}", [u * v for u, v in zip(p, pdf, strict=True)])  # fmt: skip
    add("r_edf", "  Equity discount factor (ratio)", lambda x: f"=1/(1+{x.col}{R['r_erate']})^{x.col}{R['r_years']}", edf)  # fmt: skip
    add("r_epv", "  Equity present value of the flow (USD)", lambda x: f"={x.col}{R['r_ecf']}*{x.col}{R['r_edf']}", [u * v for u, v in zip(e, edf, strict=True)])  # fmt: skip
    add("project_npv", "  Project NPV (USD)", lambda x: f"=SUM({rng('r_ppv')})", want["project_npv"], key=ctx.key("project_npv"))  # fmt: skip
    add("equity_npv", "  Equity NPV (USD)", lambda x: f"=SUM({rng('r_epv')})", want["equity_npv"], key=ctx.key("equity_npv"))  # fmt: skip
    add("project_xirr", "  Project XIRR (ratio/year)", lambda x: f"=XIRR({rng('r_pcf')},{rng('r_date')})", want["project_xirr"], key=ctx.key("project_xirr"))  # fmt: skip
    add("equity_xirr", "  Equity XIRR (ratio/year)", lambda x: f"=XIRR({rng('r_ecf')},{rng('r_date')})", want["equity_xirr"], key=ctx.key("equity_xirr"))  # fmt: skip
    add("equity_cumulative_cash", "  Equity cumulative cash flow (USD)", lambda x: f"=SUM(${a}{R['r_ecf']}:{x.col}{R['r_ecf']})", want["equity_cumulative_cash"], key=ctx.key("equity_cumulative_cash"))  # fmt: skip
    add("r_neg", "  Cumulative equity cash is negative (flag)", lambda x: f"=({x.col}{R['equity_cumulative_cash']}<0)*1", neg)  # fmt: skip
    add("equity_payback_period", "  Equity payback period (periods)",
        lambda x: f"=(${z}{R['equity_cumulative_cash']}>=0)*(SUM({rng('r_neg')})+1)",
        want["equity_payback_period"], key=ctx.key("equity_payback_period"))  # fmt: skip
    ctx.registry["returns.rows"] = dict(R)


def checks(ctx: BuildContext) -> dict[str, str]:
    c = ctx.calcs
    n = ctx.n
    cols = list(c.workbook.period_cols)
    a, z = cols[0], cols[-1]
    R = ctx.registry["returns.rows"]
    r = c.rows()
    src = {q.name: ctx.source(q.name) for q in INPUTS}
    S = lambda port, x: src[port].format(col=x.col) if "{col}" in src[port] else src[port]  # noqa: E731
    K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
    zero = [0.0] * n

    def prng(port):  # the whole feed row of a series port
        sheet, ref = src[port].split("!", 1)
        row = ref.removeprefix("{col}")
        return f"{sheet}!${a}${row}:${z}${row}"

    absum = lambda parts: "=" + "+".join(f"ABS({q})" for q in parts)  # noqa: E731
    cumr = (
        f"${a}${r[ctx.key('equity_cumulative_cash')]}:${z}${r[ctx.key('equity_cumulative_cash')]}"
    )

    c.section("Checks")
    c.row("chk_links", "  Check - linked inputs equal their ports (USD)",
          lambda x: absum([f"{x.col}{R['r_pcf']}-{S('project_cash_flow', x)}", f"{x.col}{R['r_ecf']}-{S('equity_cash_flow', x)}",
                           f"{x.col}{R['r_date']}-{S('flow_dates', x)}", f"{x.col}{R['r_prate']}-{src['project_discount_rate']}",
                           f"{x.col}{R['r_erate']}-{src['equity_discount_rate']}", f"{x.col}{R['r_dpy']}-{src['days_per_year']}"]), values=zero)  # fmt: skip

    def irr_residual(
        cf, xirr_port, x
    ):  # NPV at the XIRR as a share of the flows' size; XIRR is exact to ~1e-8 only
        d0 = f"INT(${a}{R['r_date']})"
        pv = f"SUMPRODUCT({prng(cf)}/(1+{K(xirr_port, x)})^((INT({prng('flow_dates')})-{d0})/365))"
        return f"ROUND(ABS({pv})/SUMPRODUCT(ABS({prng(cf)})),6)"

    c.row("chk_irr", "  Check - NPV at each XIRR is nil on the ports' own flows, as a share of the flows (ratio)",
          lambda x: absum([irr_residual("project_cash_flow", "project_xirr", x),
                           irr_residual("equity_cash_flow", "equity_xirr", x)]), values=zero)  # fmt: skip

    def npv(cf, rate):
        return f"SUMPRODUCT({prng(cf)}/(1+{src[rate]})^((INT({prng('flow_dates')})-INT(${a}{R['r_date']}))/{src['days_per_year']}))"

    c.row("chk_npv", "  Check - both NPVs re-derived from the ports (USD)",
          lambda x: absum([f"{K('project_npv', x)}-{npv('project_cash_flow', 'project_discount_rate')}",
                           f"{K('equity_npv', x)}-{npv('equity_cash_flow', 'equity_discount_rate')}"]), values=zero)  # fmt: skip
    c.row("chk_payback", "  Check - cumulative equity cash and the payback period re-derived (USD)",
          lambda x: (f"=ABS({K('equity_cumulative_cash', x)}-SUM({src['equity_cash_flow'].split('!')[0]}!${a}{src['equity_cash_flow'].split('!')[1].removeprefix('{col}')}:{x.col}{src['equity_cash_flow'].split('!')[1].removeprefix('{col}')}))"
                     f"+({K('equity_payback_period', x)}>0)*MAX(-INDEX({cumr},MAX(MIN({K('equity_payback_period', x)},{n}),1)),0)"
                     f"+({K('equity_payback_period', x)}>1)*MAX(INDEX({cumr},MAX({K('equity_payback_period', x)}-1,1)),0)"
                     f"+({K('equity_payback_period', x)}=0)*MAX(${z}{r[ctx.key('equity_cumulative_cash')]},0)"
                     f"+ABS({K('equity_payback_period', x)}-(${z}{r[ctx.key('equity_cumulative_cash')]}>=0)*(SUMPRODUCT(({cumr}<0)*1)+1))"), values=zero)  # fmt: skip
    return {
        "links": "Check - linked inputs equal their ports",
        "irr": "Check - NPV at each XIRR is nil on the ports' own flows, as a share of the flows",
        "npv": "Check - both NPVs re-derived from the ports",
        "payback": "Check - cumulative equity cash and the payback period re-derived",
    }


RETURNS = Module(
    name="returns",
    version="0.1.0",
    scope={
        "in": [
            "XIRR (365-day year) and NPV for two holders, the project and the equity investor, from dated flows",
            "NPV on the XNPV convention: dated flows discounted to the first flow's date (the first flow is not discounted) at one annual rate per holder, on the same day count as XIRR",
            "Cumulative equity cash flow and the equity payback period (the first period it is nil or positive; 0 if never)",
        ],
        "out": [
            "Further holders (lenders, sponsor promote): one module use per holder's flows",
            "Flows that change sign more than once (XIRR may then have several answers: a check on the NPV at the answer reads nil, but the answer is not unique)",
            "Terminal value, and cost of equity or WACC build-up (the discount rates are inputs)",
            "Payback measured in years or interpolated within a period (it is a whole period number), on discounted flows, and a payback that is reached, lost and reached again",
        ],
    },
    fast_declared={
        "3.04-01 Check - NPV at each XIRR": "XIRR's own 365-day year, and the rounding digits that absorb its 1e-8 accuracy",
        "3.04-01 Check - cumulative equity": "the number of periods bounds the payback index",
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "project_cash_flow": [-1000.0, 300.0, 450.0, 700.0],
        "equity_cash_flow": [-400.0, 50.0, 200.0, 500.0],
        "flow_dates": [0.0, 365.0, 730.0, 1095.0],
        "project_discount_rate": 0.1,
        "equity_discount_rate": 0.15,
        "days_per_year": 365.0,
    },
    golden=Golden(
        inputs={
            "project_cash_flow": [-1200.0, 400.0, 500.0, 800.0],
            "equity_cash_flow": [-500.0, 0.0, 300.0, 650.0],
            "flow_dates": [0.0, 365.0, 730.0, 1100.0],
            "project_discount_rate": 0.1,
            "equity_discount_rate": 0.15,
            "days_per_year": 365.0,
        },
        outputs={
            "project_xirr": [
                0.17253646415915672,
                0.17253646415915672,
                0.17253646415915672,
                0.17253646415915672,
            ],
            "equity_xirr": [
                0.2721984033427649,
                0.2721984033427649,
                0.2721984033427649,
                0.2721984033427649,
            ],
            "project_npv": [
                177.12711227535044,
                177.12711227535044,
                177.12711227535044,
                177.12711227535044,
            ],
            "equity_npv": [
                153.41118426782964,
                153.41118426782964,
                153.41118426782964,
                153.41118426782964,
            ],
            "equity_cumulative_cash": [-500.0, -500.0, -200.0, 450.0],
            "equity_payback_period": [4.0, 4.0, 4.0, 4.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); XNPV convention on dated flows, payback a whole period number; working in docs/golden-cases/returns.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = RETURNS
