"""Returns and valuation for flows of any shape: XIRR near a guess, NPV by holder, equity payback, and whether the
IRR is unique.

`returns` (released, write-once) finds XIRR by bisection on a fixed bracket and fails when the flows change sign more
than once, for example equity flows that end with a final fee (OMD issue 15). This module:

    IRRs            = every rate in (-0.99, 10] at which the NPV is nil, found on a grid and refined by bisection
    reported XIRR   = the IRR nearest `irr_guess`; the workbook passes the same guess to XIRR()
    sign changes    = how often the flows change sign, zero flows skipped; more than one means more than one IRR may exist
    IRR unique      = 1 when the flows change sign exactly once (then the IRR is unique), else 0

For each holder (the project, and the equity investor), from cash flows with dates:

    years since the first flow = (date - first date) / days per year
    NPV   = sum of flow x 1 / (1 + discount rate)^years since the first flow     (discounted to the first flow's date)
    XIRR  = the annual rate at which that NPV is nil, on a 365-day year (the XIRR function's convention)

`irr_guess` must lie in [0, 0.5] ratio/year. XIRR() in the workbook is Newton's method: from a guess below 0 it
returns #NUM!, and from a guess above about 0.75 it can overshoot to another root or to the solver's clamp, on the
golden flows. In [0, 0.5] the workbook and the oracle agree there. The oracle rejects a guess outside it.

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
    Port("irr_guess", "ratio/year", "scalar"),
)
OUTPUTS = (
    Port("project_xirr", "ratio/year", "series"),
    Port("equity_xirr", "ratio/year", "series"),
    Port("project_npv", "USD", "series"),
    Port("equity_npv", "USD", "series"),
    Port("equity_cumulative_cash", "USD", "series"),
    Port("equity_payback_period", "periods", "series"),
    Port("project_sign_changes", "count", "series"),
    Port("equity_sign_changes", "count", "series"),
    Port("project_irr_unique", "flag", "series"),
    Port("equity_irr_unique", "flag", "series"),
)
T = "Returns"
GRID_LO, GRID_HI, GRID_STEP = -0.99, 10.0, 0.0005
GUESS_LO, GUESS_HI = 0.0, 0.5  # the guesses at which XIRR() in the workbook and the oracle agree


def irrs(flows, dates) -> list[float]:
    """Every rate in (-0.99, 10] at which the NPV of the dated flows (365-day year) is nil."""
    d0 = math.floor(dates[0])
    t = [(math.floor(d) - d0) / 365.0 for d in dates]
    f = lambda r: sum(c / (1 + r) ** y for c, y in zip(flows, t, strict=True))  # noqa: E731
    out = []
    n = int(round((GRID_HI - GRID_LO) / GRID_STEP))
    prev_r, prev_v = GRID_LO, f(GRID_LO)
    for i in range(1, n + 1):
        r = GRID_LO + i * GRID_STEP
        v = f(r)
        if v == 0:
            out.append(r)
        elif prev_v * v < 0:
            lo, hi = prev_r, r
            for _ in range(200):
                mid = (lo + hi) / 2
                if f(lo) * f(mid) <= 0:
                    hi = mid
                else:
                    lo = mid
            out.append((lo + hi) / 2)
        prev_r, prev_v = r, v
    return out


def xirr_near(flows, dates, guess) -> float:
    """The IRR nearest the guess (what XIRR(values, dates, guess) finds when the guess is nearer that root)."""
    found = irrs(flows, dates)
    if not found:
        raise ValueError("XIRR: no rate in (-0.99, 10] makes the NPV of these flows nil")
    return min(found, key=lambda r: abs(r - guess))


def sign_changes(flows) -> int:
    """How often the flows change sign, zero flows skipped."""
    signs = [1 if c > 0 else -1 for c in flows if c != 0]
    return sum(1 for a, b in zip(signs, signs[1:]) if a != b)


def _carried(flows) -> list[float]:
    out, last = [], 0.0
    for c in flows:
        last = (1.0 if c > 0 else -1.0) if c != 0 else last
        out.append(last)
    return out


def _changes(carried) -> list[float]:
    return [1.0 if i > 0 and carried[i] * carried[i - 1] < 0 else 0.0 for i in range(len(carried))]


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
    g = float(inputs["irr_guess"])
    if not GUESS_LO <= g <= GUESS_HI:
        raise ValueError(
            f"irr_guess {g} is outside [{GUESS_LO}, {GUESS_HI}]: XIRR() in the workbook does not reliably "
            "find the root nearest a guess outside that range"
        )
    ps, es = float(sign_changes(p)), float(sign_changes(e))
    return {
        "project_xirr": [xirr_near(p, d, g)] * n,
        "equity_xirr": [xirr_near(e, d, g)] * n,
        "project_npv": [_npv(p, d, float(inputs["project_discount_rate"]), dpy)] * n,
        "equity_npv": [_npv(e, d, float(inputs["equity_discount_rate"]), dpy)] * n,
        "equity_cumulative_cash": cum,
        "equity_payback_period": [payback] * n,
        "project_sign_changes": [ps] * n,
        "equity_sign_changes": [es] * n,
        "project_irr_unique": [1.0 if ps == 1 else 0.0] * n,
        "equity_irr_unique": [1.0 if es == 1 else 0.0] * n,
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
    add("r_guess", "    IRR guess (ratio/year)", lambda x: "=" + S("irr_guess", x), [float(ctx.inputs["irr_guess"])] * n)  # fmt: skip
    add("r_years", "  Years since the first flow (years)", lambda x: f"=(INT({x.col}{R['r_date']})-INT(${a}{R['r_date']}))/{x.col}{R['r_dpy']}", years)  # fmt: skip
    add("r_pdf", "  Project discount factor (ratio)", lambda x: f"=1/(1+{x.col}{R['r_prate']})^{x.col}{R['r_years']}", pdf)  # fmt: skip
    add("r_ppv", "  Project present value of the flow (USD)", lambda x: f"={x.col}{R['r_pcf']}*{x.col}{R['r_pdf']}", [u * v for u, v in zip(p, pdf, strict=True)])  # fmt: skip
    add("r_edf", "  Equity discount factor (ratio)", lambda x: f"=1/(1+{x.col}{R['r_erate']})^{x.col}{R['r_years']}", edf)  # fmt: skip
    add("r_epv", "  Equity present value of the flow (USD)", lambda x: f"={x.col}{R['r_ecf']}*{x.col}{R['r_edf']}", [u * v for u, v in zip(e, edf, strict=True)])  # fmt: skip
    add("project_npv", "  Project NPV (USD)", lambda x: f"=SUM({rng('r_ppv')})", want["project_npv"], key=ctx.key("project_npv"))  # fmt: skip
    add("equity_npv", "  Equity NPV (USD)", lambda x: f"=SUM({rng('r_epv')})", want["equity_npv"], key=ctx.key("equity_npv"))  # fmt: skip
    add("project_xirr", "  Project XIRR (ratio/year)", lambda x: f"=XIRR({rng('r_pcf')},{rng('r_date')},{x.col}{R['r_guess']})", want["project_xirr"], key=ctx.key("project_xirr"))  # fmt: skip
    add("equity_xirr", "  Equity XIRR (ratio/year)", lambda x: f"=XIRR({rng('r_ecf')},{rng('r_date')},{x.col}{R['r_guess']})", want["equity_xirr"], key=ctx.key("equity_xirr"))  # fmt: skip
    add("equity_cumulative_cash", "  Equity cumulative cash flow (USD)", lambda x: f"=SUM(${a}{R['r_ecf']}:{x.col}{R['r_ecf']})", want["equity_cumulative_cash"], key=ctx.key("equity_cumulative_cash"))  # fmt: skip
    add("r_neg", "  Cumulative equity cash is negative (flag)", lambda x: f"=({x.col}{R['equity_cumulative_cash']}<0)*1", neg)  # fmt: skip
    add("equity_payback_period", "  Equity payback period (periods)",
        lambda x: f"=(${z}{R['equity_cumulative_cash']}>=0)*(SUM({rng('r_neg')})+1)",
        want["equity_payback_period"], key=ctx.key("equity_payback_period"))  # fmt: skip
    prev = lambda x, k: f"{x.prev_col}{R[k]}" if x.prev_col else "0"  # noqa: E731
    for h, flows in (("project", p), ("equity", e)):
        cf = "r_pcf" if h == "project" else "r_ecf"
        car = _carried(flows)
        chg = _changes(car)
        cnt = float(sign_changes(flows))
        add(f"r_{h}_sgn", f"  {h.capitalize()} flow sign, carried past zero flows (sign)",
            lambda x, cf=cf, h=h: f"=SIGN({x.col}{R[cf]})+({x.col}{R[cf]}=0)*{prev(x, f'r_{h}_sgn')}", car)  # fmt: skip
        add(f"r_{h}_chg", f"  {h.capitalize()} flow changes sign here (flag)",
            lambda x, h=h: f"=({x.col}{R[f'r_{h}_sgn']}*{prev(x, f'r_{h}_sgn')}<0)*1", chg)  # fmt: skip
        add(f"{h}_sign_changes", f"  {h.capitalize()} sign changes (count)",
            lambda x, h=h: f"=SUM({rng(f'r_{h}_chg')})", [cnt] * n, key=ctx.key(f"{h}_sign_changes"))  # fmt: skip
        add(f"{h}_irr_unique", f"  {h.capitalize()} IRR guaranteed unique (flag)",
            lambda x, h=h: f"=({x.col}{R[f'{h}_sign_changes']}=1)*1", [1.0 if cnt == 1 else 0.0] * n,
            key=ctx.key(f"{h}_irr_unique"))  # fmt: skip
    ctx.registry["returns_irr.rows"] = dict(R)


def checks(ctx: BuildContext) -> dict[str, str]:
    c = ctx.calcs
    n = ctx.n
    cols = list(c.workbook.period_cols)
    a, z = cols[0], cols[-1]
    R = ctx.registry["returns_irr.rows"]
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
                           f"{x.col}{R['r_erate']}-{src['equity_discount_rate']}", f"{x.col}{R['r_dpy']}-{src['days_per_year']}",
                           f"{x.col}{R['r_guess']}-{src['irr_guess']}"]), values=zero)  # fmt: skip

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

    def sign_terms(x):
        pv = lambda k: f"{x.prev_col}{R[k]}" if x.prev_col else "0"  # noqa: E731
        terms = []
        for h in ("project", "equity"):
            port = "project_cash_flow" if h == "project" else "equity_cash_flow"
            cf, sg, ch = S(port, x), f"{x.col}{R[f'r_{h}_sgn']}", f"{x.col}{R[f'r_{h}_chg']}"
            terms += [
                f"{sg}-(SIGN({cf})+({cf}=0)*{pv(f'r_{h}_sgn')})",
                f"{ch}-({sg}*{pv(f'r_{h}_sgn')}<0)*1",
                f"{K(f'{h}_sign_changes', x)}-SUM(${a}{R[f'r_{h}_chg']}:${z}{R[f'r_{h}_chg']})",
                f"{K(f'{h}_irr_unique', x)}-({K(f'{h}_sign_changes', x)}=1)*1",
            ]
        return terms

    c.row("chk_signs", "  Check - signs, sign changes and the unique flags re-derived from the ports (count)",
          lambda x: absum(sign_terms(x)), values=zero)  # fmt: skip
    return {
        "signs": "Check - signs, sign changes and the unique flags re-derived from the ports",
        "links": "Check - linked inputs equal their ports",
        "irr": "Check - NPV at each XIRR is nil on the ports' own flows, as a share of the flows",
        "npv": "Check - both NPVs re-derived from the ports",
        "payback": "Check - cumulative equity cash and the payback period re-derived",
    }


RETURNS_IRR = Module(
    name="returns_irr",
    version="0.1.0",
    scope={
        "in": [
            "XIRR (365-day year) and NPV for two holders, the project and the equity investor, from dated flows of any shape",
            "Flows that change sign more than once: every IRR in (-0.99, 10] is found; the one nearest the guess is reported, and XIRR() in the workbook starts from the same guess",
            "Sign changes per holder, and a flag that the IRR is unique (exactly one sign change)",
            "NPV on the XNPV convention: dated flows discounted to the first flow's date (the first flow is not discounted) at one annual rate per holder, on the same day count as XIRR",
            "Cumulative equity cash flow and the equity payback period (the first period it is nil or positive; 0 if never)",
        ],
        "out": [
            "Further holders (lenders, sponsor promote): one module use per holder's flows",
            "An `irr_guess` outside [0, 0.5] ratio/year (the module rejects it: XIRR() in the workbook returns #NUM! below 0 and can overshoot above about 0.75)",
            "An IRR outside (-0.99, 10]; a guess nearer the wrong root (XIRR() may then find that root: the check that the NPV at the answer is nil still holds, and the unique flag reads 0)",
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
        "project_cash_flow": [-1000.0, 1200.0, 400.0, -500.0],
        "equity_cash_flow": [-400.0, 50.0, 200.0, 500.0],
        "flow_dates": [0.0, 365.0, 730.0, 1095.0],
        "project_discount_rate": 0.1,
        "equity_discount_rate": 0.15,
        "days_per_year": 365.0,
        "irr_guess": 0.1,
    },
    golden=Golden(
        inputs={
            "project_cash_flow": [-1000.0, 800.0, 800.0, -500.0],
            "equity_cash_flow": [-300.0, 200.0, 260.0, -120.0],
            "flow_dates": [0.0, 365.0, 730.0, 1095.0],
            "project_discount_rate": 0.08,
            "equity_discount_rate": 0.12,
            "days_per_year": 365.0,
            "irr_guess": 0.1,
        },
        outputs={
            "project_xirr": [0.115335033314822] * 4,
            "equity_xirr": [0.121425213546952] * 4,
            "project_npv": [29.6956764720830] * 4,
            "equity_npv": [0.428206997085000] * 4,
            "equity_cumulative_cash": [-300.0, -100.0, 160.0, 40.0],
            "equity_payback_period": [3.0] * 4,
            "project_sign_changes": [2.0] * 4,
            "equity_sign_changes": [2.0] * 4,
            "project_irr_unique": [0.0] * 4,
            "equity_irr_unique": [0.0] * 4,
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-11-08): two IRRs per "
        "holder (grid scan with bisection, and the cubic in 1/(1+r) solved directly), the one nearest the guess "
        "reported; working in docs/golden-cases/returns_irr.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = RETURNS_IRR
