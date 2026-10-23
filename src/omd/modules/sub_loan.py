"""Subordinated / shareholder loan.

    interest   = rate x opening balance
    PIK        = PIK share x interest            (capitalised: added to the balance)
    cash interest = interest - PIK
    available  = opening + drawdown + PIK
    repayment  = min(repayment requested, available)
    closing    = available - repayment

Repayment requested is the caller's decision (the distribution waterfall says what may be paid).
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port
from ._plan_module import build_plan, plan_checks

INPUTS = (
    Port("sub_drawdown", "USD", "series"),
    Port("sub_repayment_request", "USD", "series"),
    Port("sub_interest_rate", "ratio", "scalar"),
    Port("sub_pik_share", "ratio", "scalar"),
    Port("opening_sub_loan", "USD", "scalar"),
)
OUTPUTS = (
    Port("sub_interest", "USD", "series"),
    Port("sub_interest_pik", "USD", "series"),
    Port("sub_interest_cash", "USD", "series"),
    Port("sub_repayment", "USD", "series"),
    Port("sub_closing", "USD", "series"),
)
T = "Subordinated loan"
KEYED = {"interest": "sub_interest", "pik": "sub_interest_pik", "cash_int": "sub_interest_cash",
         "repay": "sub_repayment", "close": "sub_closing"}  # fmt: skip
PLAN = [
    ("lp", "open", "Loan, opening (USD)", "sub_closing"),
    ("link", "rate", "Interest rate per period (ratio)", "sub_interest_rate"),
    ("calc", "interest", "Interest (USD)", "{rate}*{open}"),
    ("link", "share", "Share of interest capitalised (ratio)", "sub_pik_share"),
    ("calc", "pik", "Interest capitalised, PIK (USD)", "{share}*{interest}"),
    ("calc", "cash_int", "Interest paid in cash (USD)", "{interest}-{pik}"),
    ("link", "draw", "Drawdown (USD)", "sub_drawdown"),
    ("lp", "open2", "Loan, opening (USD)", "sub_closing"),
    ("calc", "avail", "Balance before repayment (USD)", "{open2}+{draw}+{pik}"),
    ("link", "req", "Repayment requested (USD)", "sub_repayment_request"),
    ("calc", "repay", "Repayment (USD)", "MIN({req},{avail})"),
    ("calc", "close", "Loan, closing (USD)", "{avail}-{repay}"),
]


def _run(inputs):
    r, share, bal = (
        float(inputs["sub_interest_rate"]),
        float(inputs["sub_pik_share"]),
        float(inputs["opening_sub_loan"]),
    )
    V = {
        k: []
        for k in (
            "open",
            "open2",
            "rate",
            "interest",
            "share",
            "pik",
            "cash_int",
            "draw",
            "avail",
            "req",
            "repay",
            "close",
        )
    }
    for draw, req in zip(inputs["sub_drawdown"], inputs["sub_repayment_request"], strict=True):
        interest = r * bal
        pik = share * interest
        avail = bal + float(draw) + pik
        repay = min(float(req), avail)
        row = {"open": bal, "open2": bal, "rate": r, "interest": interest, "share": share, "pik": pik,
               "cash_int": interest - pik, "draw": float(draw), "avail": avail, "req": float(req),
               "repay": repay, "close": avail - repay}  # fmt: skip
        bal = avail - repay
        for k, v in row.items():
            V[k].append(v)
    return V


def oracle(inputs: dict) -> dict[str, list[float]]:
    V = _run(inputs)
    return {
        "sub_interest": V["interest"], "sub_interest_pik": V["pik"], "sub_interest_cash": V["cash_int"],
        "sub_repayment": V["repay"], "sub_closing": V["close"],
    }  # fmt: skip


def build(ctx: BuildContext) -> None:
    build_plan(ctx, T, PLAN, _run(ctx.inputs), KEYED, {"sub_closing": "opening_sub_loan"})


def checks(ctx: BuildContext) -> dict[str, str]:
    c = ctx.calcs
    r = c.rows()
    cols = list(c.workbook.period_cols)
    first = cols[0]
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col)  # noqa: E731
    K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
    kr = lambda port: r[ctx.key(port)]  # noqa: E731
    sheet, ref = src["sub_drawdown"].split("!", 1)
    drow = ref.removeprefix("{col}")

    def bal(x):  # balance brought forward from cumulative flows
        if x.i == 1:
            return src["opening_sub_loan"]
        p = cols[x.i - 2]
        return (f"({src['opening_sub_loan']}+SUM({sheet}!${first}{drow}:{p}{drow})"
                f"+SUM(${first}{kr('sub_interest_pik')}:{p}{kr('sub_interest_pik')})"
                f"-SUM(${first}{kr('sub_repayment')}:{p}{kr('sub_repayment')}))")  # fmt: skip

    c.section("Checks")
    c.row("chk_loan", "  Check - interest, PIK, repayment and balance re-derived from the ports (USD)",
          lambda x: f"=ABS({K('sub_interest', x)}-{src['sub_interest_rate']}*{bal(x)})"
                    f"+ABS({K('sub_interest_pik', x)}-{src['sub_pik_share']}*{K('sub_interest', x)})"
                    f"+ABS({K('sub_interest_cash', x)}-({K('sub_interest', x)}-{K('sub_interest_pik', x)}))"
                    f"+ABS({K('sub_repayment', x)}-MIN({S('sub_repayment_request', x)},{bal(x)}+{S('sub_drawdown', x)}+{K('sub_interest_pik', x)}))"
                    f"+ABS({K('sub_closing', x)}-({bal(x)}+{S('sub_drawdown', x)}+{K('sub_interest_pik', x)}-{K('sub_repayment', x)}))"
                    f"+MAX(-{K('sub_closing', x)},0)", values=[0.0] * ctx.n)  # fmt: skip
    label = plan_checks(ctx, T, PLAN, KEYED, lambda port, x: bal(x))
    return {"loan": "Check - interest, PIK, repayment and balance re-derived", "rows": label}


SUB_LOAN = Module(
    name="sub_loan",
    version="0.1.0",
    scope={
        "in": [
            "Interest on the opening balance only at one rate per period: drawdowns are end-of-period and earn no interest in the period they are drawn",
            "A share of the interest capitalised (PIK), the rest paid in cash",
            "Drawdowns and repayments, repayment never above the balance",
            "A brought-forward balance",
        ],
        "out": [
            "Whether a repayment is allowed (lock-up, waterfall): the caller supplies the request",
            "Withholding tax on interest, thin capitalisation and arm's-length tests",
            "Interest on interest within a period, floating rates and FX",
            "Conversion to equity or write-off",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "sub_drawdown": [200.0, 100.0, 0.0, 0.0],
        "sub_repayment_request": [0.0, 0.0, 150.0, 1000.0],
        "sub_interest_rate": 0.08,
        "sub_pik_share": 0.5,
        "opening_sub_loan": 50.0,
    },
    golden=Golden(
        inputs={
            "sub_drawdown": [300.0, 0.0, 100.0, 0.0],
            "sub_repayment_request": [0.0, 100.0, 0.0, 600.0],
            "sub_interest_rate": 0.1,
            "sub_pik_share": 0.4,
            "opening_sub_loan": 100.0,
        },
        outputs={
            "sub_interest": [10.0, 40.4, 32.016, 43.29664],
            "sub_interest_pik": [4.0, 16.16, 12.8064, 17.318656],
            "sub_interest_cash": [6.0, 24.24, 19.2096, 25.977984],
            "sub_repayment": [0.0, 100.0, 0.0, 450.285056],
            "sub_closing": [404.0, 320.16, 432.9664, 0.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/sub_loan.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = SUB_LOAN
