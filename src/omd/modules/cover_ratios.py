"""Cover ratios: DSCR, rolling DSCR, LLCR and PLCR.

    DSCR_t        = CFADS_t / debt service_t
    rolling DSCR  = CFADS over the last `WINDOW` periods / debt service over the same periods,
                    0 in a period that starts with no debt outstanding
    LLCR_t        = PV of CFADS over the loan life from the start of period t / debt at the start of period t
    PLCR_t        = PV of CFADS over the project life from the start of period t / debt at the start of period t

PV discounts each period's CFADS one full period from the start of its own period at the discount rate
(cash arrives at the end of the period). A ratio whose denominator is nil reads 0, not an error.
The rolling window is built into the module (WINDOW periods, shorter at the start).
"""

from __future__ import annotations

from openpyxl.utils import column_index_from_string, get_column_letter

from ..module import BuildContext, Golden, Module, Port

WINDOW = 2
INPUTS = (
    Port("cfads", "USD", "series"),
    Port("debt_service", "USD", "series"),
    Port("debt_closing", "USD", "series"),
    Port("loan_life_flag", "count", "series"),
    Port("discount_rate", "ratio", "scalar"),
    Port("opening_debt", "USD", "scalar"),
)
OUTPUTS = (
    Port("dscr", "ratio", "series"),
    Port("dscr_rolling", "ratio", "series"),
    Port("llcr", "ratio", "series"),
    Port("plcr", "ratio", "series"),
)
T = "Cover ratios"


def _pv(flows, r):
    out, nxt = [0.0] * len(flows), 0.0
    for i in range(len(flows) - 1, -1, -1):
        nxt = (flows[i] + nxt) / (1 + r)
        out[i] = nxt
    return out


def _div(a, b):
    return a / b if b > 0 else 0.0


def oracle(inputs: dict) -> dict[str, list[float]]:
    cf = [float(x) for x in inputs["cfads"]]
    ds = [float(x) for x in inputs["debt_service"]]
    close = [float(x) for x in inputs["debt_closing"]]
    flag = [float(x) for x in inputs["loan_life_flag"]]
    r = float(inputs["discount_rate"])
    opened = [float(inputs["opening_debt"]), *close[:-1]]
    pv_loan = _pv([c * f for c, f in zip(cf, flag, strict=True)], r)
    pv_proj = _pv(cf, r)
    n = len(cf)
    return {
        "dscr": [_div(cf[i], ds[i]) for i in range(n)],
        "dscr_rolling": [
            _div(sum(cf[max(0, i - WINDOW + 1) : i + 1]), sum(ds[max(0, i - WINDOW + 1) : i + 1]))
            if opened[i] > 0
            else 0.0
            for i in range(n)
        ],
        "llcr": [_div(pv_loan[i], opened[i]) for i in range(n)],
        "plcr": [_div(pv_proj[i], opened[i]) for i in range(n)],
    }


def _rows(ctx):
    """(key, label, formula(x), values) for every row, in sheet order. Shared by build and checks."""
    c = ctx.calcs
    n = ctx.n
    cols = list(c.workbook.period_cols)
    oc = c.workbook.open_col
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    return c, n, cols, oc, src


def build(ctx: BuildContext) -> None:
    c, n, cols, oc, src = _rows(ctx)
    want = oracle(ctx.inputs)
    cf, ds = ctx.values("cfads"), ctx.values("debt_service")
    close, flag = ctx.values("debt_closing"), ctx.values("loan_life_flag")
    r = float(ctx.inputs["discount_rate"])
    opened = [float(ctx.inputs["opening_debt"]), *close[:-1]]
    loan_cf = [a * b for a, b in zip(cf, flag, strict=True)]
    pv_loan, pv_proj = _pv(loan_cf, r), _pv(cf, r)
    S = lambda port, x: src[port].format(col=x.col)  # noqa: E731
    c.skip_rows()
    c.section(T)
    rows: dict[str, int] = {}

    def add(name, label, f, values, key=None):
        rows[name] = c.next_row
        c.row(key or name, label, f, values=values)

    R = lambda k: rows[k]  # noqa: E731
    add("cr_cf", "    CFADS (USD)", lambda x: "=" + S("cfads", x), cf)
    add("cr_ds", "    Debt service (USD)", lambda x: "=" + S("debt_service", x), ds)
    add("cr_close", "    Debt, closing (USD)", lambda x: "=" + S("debt_closing", x), close)
    add("cr_flag", "    Loan life (flag)", lambda x: "=" + S("loan_life_flag", x), flag)
    add(
        "cr_rate",
        "    Discount rate per period (ratio)",
        lambda x: "=" + src["discount_rate"],
        [r] * n,
    )
    add("cr_open", "  Debt at the start of the period (USD)",
        lambda x: f"={([oc] + cols)[x.i - 1]}{R('cr_close')}", opened)  # fmt: skip
    c.ws[f"{oc}{R('cr_close')}"] = (
        f"={src['opening_debt']}"  # the Open cell of the closing row: period 1 reads it
    )
    add(
        "cr_loancf",
        "  CFADS within the loan life (USD)",
        lambda x: f"={x.col}{R('cr_cf')}*{x.col}{R('cr_flag')}",
        loan_cf,
    )
    nextcol = lambda x: get_column_letter(column_index_from_string(x.col) + 1)  # noqa: E731  (empty past the last period)
    left = c.rows()["periods_left"]
    gate = lambda x: f"({x.col}{left}>0)"  # noqa: E731  (a next period exists; the cell past the last period is never read)
    add("cr_pvloan", "  PV of CFADS over the loan life (USD)",
        lambda x: f"=({x.col}{R('cr_loancf')}+{nextcol(x)}{c.next_row}*{gate(x)})/(1+{x.col}{R('cr_rate')})", pv_loan)  # fmt: skip
    add("cr_pvproj", "  PV of CFADS over the project life (USD)",
        lambda x: f"=({x.col}{R('cr_cf')}+{nextcol(x)}{c.next_row}*{gate(x)})/(1+{x.col}{R('cr_rate')})", pv_proj)  # fmt: skip
    win = lambda x, k: f"SUM({cols[max(0, x.i - WINDOW)]}{R(k)}:{x.col}{R(k)})"  # noqa: E731
    flag = lambda k, x: f"{x.col}{R(k)}"  # noqa: E731
    add("f_dscr", "  Debt service is positive (flag)", lambda x: f"=({x.col}{R('cr_ds')}>0)*1",
        [1.0 if v > 0 else 0.0 for v in ds])  # fmt: skip
    add("dscr", "  DSCR (ratio)", lambda x: f"={flag('f_dscr', x)}*{x.col}{R('cr_cf')}/({x.col}{R('cr_ds')}+1-{flag('f_dscr', x)})",
        want["dscr"], key=ctx.key("dscr"))  # fmt: skip
    wds = [sum(ds[max(0, i - WINDOW + 1) : i + 1]) for i in range(n)]
    add("f_roll", "  Debt is outstanding and the window's debt service is positive (flag)",
        lambda x: f"=({x.col}{R('cr_open')}>0)*({win(x, 'cr_ds')}>0)",
        [1.0 if opened[i] > 0 and wds[i] > 0 else 0.0 for i in range(n)])  # fmt: skip
    add("dscr_rolling", f"  DSCR, rolling {WINDOW} periods (ratio)",
        lambda x: f"={flag('f_roll', x)}*{win(x, 'cr_cf')}/({win(x, 'cr_ds')}+1-{flag('f_roll', x)})",
        want["dscr_rolling"], key=ctx.key("dscr_rolling"))  # fmt: skip
    add("f_open", "  Debt is outstanding at the start of the period (flag)", lambda x: f"=({x.col}{R('cr_open')}>0)*1",
        [1.0 if v > 0 else 0.0 for v in opened])  # fmt: skip
    add("llcr", "  LLCR (ratio)", lambda x: f"={flag('f_open', x)}*{x.col}{R('cr_pvloan')}/({x.col}{R('cr_open')}+1-{flag('f_open', x)})",
        want["llcr"], key=ctx.key("llcr"))  # fmt: skip
    add("plcr", "  PLCR (ratio)", lambda x: f"={flag('f_open', x)}*{x.col}{R('cr_pvproj')}/({x.col}{R('cr_open')}+1-{flag('f_open', x)})",
        want["plcr"], key=ctx.key("plcr"))  # fmt: skip
    ctx.registry["cover.rows"] = dict(rows)


def checks(ctx: BuildContext) -> dict[str, str]:
    c, n, cols, oc, src = _rows(ctx)
    rows = ctx.registry["cover.rows"]
    R = lambda k: rows[k]  # noqa: E731
    S = lambda port, x: src[port].format(col=x.col)  # noqa: E731
    A = lambda k, x: f"{x.col}{R(k)}"  # noqa: E731
    absum = lambda parts: "=" + "+".join(f"ABS({p})" for p in parts)  # noqa: E731
    zero = [0.0] * n
    nxt = lambda x: cols[x.i] if x.i < n else None  # noqa: E731

    def opened(x):
        return src["opening_debt"] if x.i == 1 else S("debt_closing", replace_prev(x))

    class P:  # a column-like object for the previous period
        pass

    def replace_prev(x):
        p = P()
        p.col = cols[x.i - 2]
        return p

    c.section("Checks")
    c.row("chk_links", "  Check - linked inputs and start-of-period debt equal their ports (USD)",
          lambda x: absum([A("cr_cf", x) + "-" + S("cfads", x), A("cr_ds", x) + "-" + S("debt_service", x),
                           A("cr_close", x) + "-" + S("debt_closing", x), A("cr_flag", x) + "-" + S("loan_life_flag", x),
                           A("cr_rate", x) + "-" + src["discount_rate"], A("cr_open", x) + "-" + opened(x),
                           A("cr_loancf", x) + f"-{S('cfads', x)}*{S('loan_life_flag', x)}"]), values=zero)  # fmt: skip

    def pv_identity(row, flow):
        def f(x):
            after = f"+{nxt(x)}{R(row)}" if nxt(x) else ""
            return f"={A(row, x)}*(1+{src['discount_rate']})-({flow(x)}{after})"

        return f

    c.row("chk_pv_loan", "  Check - PV over the loan life satisfies its recursion (USD)",
          pv_identity("cr_pvloan", lambda x: f"{S('cfads', x)}*{S('loan_life_flag', x)}"), values=zero)  # fmt: skip
    c.row("chk_pv_proj", "  Check - PV over the project life satisfies its recursion (USD)",
          pv_identity("cr_pvproj", lambda x: S("cfads", x)), values=zero)  # fmt: skip

    def wsum(x, port):
        sheet, ref = src[port].split("!", 1)
        row = ref.removeprefix("{col}")
        return f"SUM({sheet}!{cols[max(0, x.i - WINDOW)]}{row}:{x.col}{row})"

    g = lambda e: f"({e}>0)"  # noqa: E731
    c.row("chk_ratios", "  Check - the four ratios re-derived from the ports (ratio)",
          lambda x: absum([
              A("dscr", x) + f"-{g(S('debt_service', x))}*{S('cfads', x)}/({S('debt_service', x)}+1-{g(S('debt_service', x))})",
              A("dscr_rolling", x) + f"-{g(opened(x))}*{g(wsum(x, 'debt_service'))}*{wsum(x, 'cfads')}/({wsum(x, 'debt_service')}+1-{g(opened(x))}*{g(wsum(x, 'debt_service'))})",
              A("llcr", x) + f"-{g(opened(x))}*{A('cr_pvloan', x)}/({opened(x)}+1-{g(opened(x))})",
              A("plcr", x) + f"-{g(opened(x))}*{A('cr_pvproj', x)}/({opened(x)}+1-{g(opened(x))})",
          ]), values=zero)  # fmt: skip
    return {
        "links": "Check - linked inputs and start-of-period debt equal their ports",
        "pv_loan": "Check - PV over the loan life satisfies its recursion",
        "pv_proj": "Check - PV over the project life satisfies its recursion",
        "ratios": "Check - the four ratios re-derived from the ports",
    }


COVER_RATIOS = Module(
    name="cover_ratios",
    version="0.1.0",
    scope={
        "in": [
            "DSCR per period, and a rolling DSCR over the last two periods (shorter at the start); "
            "the rolling DSCR reads 0 in a period that starts with no debt outstanding",
            "LLCR and PLCR from the start of each period: PV of CFADS over the loan life or the "
            "project life, divided by debt at the start of the period",
            "A loan-life flag series; end-of-period cash flows discounted at one rate per period",
            "A ratio with a nil denominator reads 0",
        ],
        "out": [
            "Covenant thresholds, lock-up and default tests (see the lock-up module)",
            "A different rolling window (the window is built in) or a time-varying discount rate",
            "Mid-period discounting and XIRR-style dating",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "cfads": [300.0, 320.0, 340.0, 360.0],
        "debt_service": [200.0, 200.0, 200.0, 0.0],
        "debt_closing": [700.0, 450.0, 200.0, 0.0],
        "loan_life_flag": [1.0, 1.0, 1.0, 0.0],
        "discount_rate": 0.05,
        "opening_debt": 900.0,
    },
    golden=Golden(
        inputs={
            "cfads": [400.0, 380.0, 360.0, 340.0],
            "debt_service": [250.0, 250.0, 250.0, 100.0],
            "debt_closing": [800.0, 600.0, 300.0, 0.0],
            "loan_life_flag": [1.0, 1.0, 1.0, 1.0],
            "discount_rate": 0.06,
            "opening_debt": 1000.0,
        },
        outputs={
            "dscr": [1.6, 1.52, 1.44, 3.4],
            "dscr_rolling": [1.6, 1.56, 1.48, 2.0],
            "llcr": [1.2871319251640045, 1.2054498008423058, 1.0703690518571258, 1.069182389937107],
            "plcr": [1.2871319251640045, 1.2054498008423058, 1.0703690518571258, 1.069182389937107],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/cover_ratios.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = COVER_RATIOS
