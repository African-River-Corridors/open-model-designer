"""Senior debt, draw to need.

    draw    = min(need x availability flag, headroom)      headroom = commitment - debt drawn so far
    gap     = need - draw                                  the visible funding gap

The funding gap is a row of its own, never a plug: need that the facility cannot meet (the window is
shut, or the commitment is used up) shows there, and nothing else in the model absorbs it silently.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port

INPUTS = (
    Port("funding_need", "USD", "series"),
    Port("availability_flag", "count", "series"),
    Port("facility_limit", "USD", "scalar"),
    Port("opening_debt", "USD", "scalar"),
)
OUTPUTS = (
    Port("debt_drawdown", "USD", "series"),
    Port("funding_gap", "USD", "series"),
    Port("debt_closing", "USD", "series"),
)
T = "Debt draw to need"


def oracle(inputs: dict) -> dict[str, list[float]]:
    limit, debt = float(inputs["facility_limit"]), float(inputs["opening_debt"])
    draw, gap, close = [], [], []
    for need, flag in zip(inputs["funding_need"], inputs["availability_flag"], strict=True):
        d = min(float(need) * float(flag), limit - debt)
        debt += d
        draw.append(d)
        gap.append(float(need) - d)
        close.append(debt)
    return {"debt_drawdown": draw, "funding_gap": gap, "debt_closing": close}


def build(ctx: BuildContext) -> None:
    want = oracle(ctx.inputs)
    c = ctx.calcs
    limit = float(ctx.inputs["facility_limit"])
    need, flag = ctx.values("funding_need"), ctx.values("availability_flag")
    close, draw = want["debt_closing"], want["debt_drawdown"]
    open_v = [float(ctx.inputs["opening_debt"]), *close[:-1]]
    headroom = [limit - o for o in open_v]
    avail = [n * f for n, f in zip(need, flag, strict=True)]
    b = ctx.block(T)
    first = c.next_row
    close_row = first + 10
    b.link_prev("open", close_row, "Debt drawn, opening (USD)", values=open_v)
    b.link(
        "limit",
        ctx.source("facility_limit"),
        "Facility commitment (USD)",
        values=ctx.values("facility_limit"),
    )
    b.calc("headroom", "Undrawn commitment (USD)", "{limit}-{open}", values=headroom)
    b.link("need", ctx.source("funding_need"), "Funding need (USD)", values=need)
    b.link(
        "win", ctx.source("availability_flag"), "Drawing allowed in the period (flag)", values=flag
    )
    b.calc("avail", "Need within the availability window (USD)", "{need}*{win}", values=avail)
    b.calc("draw", "Drawdown (USD)", "MIN({avail},{headroom})",
           key=ctx.key("debt_drawdown"), values=draw)  # fmt: skip
    b.link("need2", ctx.source("funding_need"), "Funding need (USD)", values=need)
    b.calc("gap", "Funding gap, never a plug (USD)", "{need2}-{draw}",
           key=ctx.key("funding_gap"), values=want["funding_gap"])  # fmt: skip
    b.link_prev("open2", close_row, "Debt drawn, opening (USD)", values=open_v)
    b.calc("close", "Debt drawn, closing (USD)", "{open2}+{draw}",
           key=ctx.key("debt_closing"), values=close)  # fmt: skip
    assert c.rows()[ctx.key("debt_closing")] == close_row
    c.ws[f"{c.workbook.open_col}{close_row}"] = f"={ctx.source('opening_debt')}"


def checks(ctx: BuildContext) -> dict[str, str]:
    c = ctx.calcs
    r = c.rows()
    cols = list(c.workbook.period_cols)
    first = cols[0]
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col)  # noqa: E731
    B = lambda name, x: f"{x.col}{r[f'_{T[:18]}_{name}']}"  # noqa: E731
    K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
    drow = r[ctx.key("debt_drawdown")]
    absum = lambda parts: "=" + "+".join(f"ABS({p})" for p in parts)  # noqa: E731
    zero = [0.0] * ctx.n

    def opening(x):
        if x.i == 1:
            return src["opening_debt"]
        return f"({src['opening_debt']}+SUM(${first}{drow}:{cols[x.i - 2]}{drow}))"

    c.section("Checks")
    c.row("chk_draw", "  Check - drawdown re-derived from the ports (USD)",
          lambda x: f"={K('debt_drawdown', x)}-MIN({S('funding_need', x)}*{S('availability_flag', x)},"
                    f"{src['facility_limit']}-{opening(x)})", values=zero)  # fmt: skip
    c.row("chk_gap", "  Check - need equals drawdown plus gap (USD)",
          lambda x: f"={S('funding_need', x)}-{K('debt_drawdown', x)}-{K('funding_gap', x)}", values=zero)  # fmt: skip
    c.row("chk_limit", "  Check - drawn debt stays within the commitment (USD)",
          lambda x: f"=ABS({K('debt_closing', x)}-({opening(x)}+{K('debt_drawdown', x)}))"
                    f"+MAX({K('debt_closing', x)}-{src['facility_limit']},0)+MAX(-{K('debt_drawdown', x)},0)",
          values=zero)  # fmt: skip
    c.row("chk_rows", "  Check - links and intermediate rows re-derived (USD)",
          lambda x: absum([
              B("limit", x) + "-" + src["facility_limit"], B("need", x) + "-" + S("funding_need", x),
              B("need2", x) + "-" + S("funding_need", x), B("win", x) + "-" + S("availability_flag", x),
              B("open", x) + "-" + opening(x), B("open2", x) + "-" + opening(x),
              B("headroom", x) + f"-({src['facility_limit']}-{opening(x)})",
              B("avail", x) + f"-{S('funding_need', x)}*{S('availability_flag', x)}",
          ]), values=zero)  # fmt: skip
    return {
        "draw": "Check - drawdown re-derived from the ports",
        "gap": "Check - need equals drawdown plus gap",
        "limit": "Check - drawn debt stays within the commitment",
        "rows": "Check - links and intermediate rows re-derived",
    }


DEBT_DRAW = Module(
    name="debt_draw",
    version="0.1.0",
    scope={
        "in": [
            "Drawing to meet a funding need, capped at the undrawn commitment",
            "An availability window as a flag series (no draws where it is 0)",
            "A visible funding-gap row for need the facility does not meet, never a plug",
            "A brought-forward drawn balance that counts against the commitment",
        ],
        "out": [
            "Repayment (see the repayment module) and any re-borrowing of repaid amounts",
            "IDC and fees that depend on the draw (see the IDC module)",
            "Several tranches or lenders in one module: use one instance per facility",
            "Conditions precedent, pro-rata equity first or last: the need series is the caller's",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "funding_need": [300.0, 400.0, 500.0, 200.0],
        "availability_flag": [1.0, 1.0, 1.0, 0.0],
        "facility_limit": 1000.0,
        "opening_debt": 0.0,
    },
    golden=Golden(
        inputs={
            "funding_need": [250.0, 350.0, 300.0, 150.0],
            "availability_flag": [1.0, 1.0, 1.0, 0.0],
            "facility_limit": 800.0,
            "opening_debt": 50.0,
        },
        outputs={
            "debt_drawdown": [250.0, 350.0, 150.0, 0.0],
            "funding_gap": [0.0, 0.0, 150.0, 150.0],
            "debt_closing": [300.0, 650.0, 800.0, 800.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/debt_draw.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = DEBT_DRAW
