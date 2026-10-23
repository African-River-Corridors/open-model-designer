"""Interest during construction.

Interest accrues on the debt drawn so far and is capitalised: it is added to the debt balance and to
the asset's cost. That is a circularity, because interest on the balance includes interest. This
module SOLVES it algebraically and names it (the capitalised-interest circularity, Bodmer):

    interest = rate x (opening debt + weight x (draw + interest))
    =>  interest = rate x (opening debt + weight x draw) / (1 - weight x rate)

`weight` is how much of the period's draw (and its own interest) bears interest: 0 charges on the
opening balance only, 0.5 on the average balance, 1 on the closing balance. No iterative calculation
and no circular reference in the workbook; a check row re-derives the circular definition.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port

INPUTS = (
    Port("debt_funded_capex", "USD", "series"),
    Port("capital_additions", "USD", "series"),
    Port("idc_rate", "ratio", "scalar"),
    Port("idc_weight", "ratio", "scalar"),
    Port("opening_debt", "USD", "scalar"),
)
OUTPUTS = (
    Port("idc_capitalised", "USD", "series"),
    Port("debt_closing", "USD", "series"),
    Port("capital_additions_incl_idc", "USD", "series"),
)
T = "Interest during construction"


def oracle(inputs: dict) -> dict[str, list[float]]:
    r, w = float(inputs["idc_rate"]), float(inputs["idc_weight"])
    debt = float(inputs["opening_debt"])
    idc, close, asset = [], [], []
    for draw, capex in zip(inputs["debt_funded_capex"], inputs["capital_additions"], strict=True):
        i = r * (debt + w * float(draw)) / (1 - w * r)
        debt = debt + float(draw) + i
        idc.append(i)
        close.append(debt)
        asset.append(float(capex) + i)
    return {"idc_capitalised": idc, "debt_closing": close, "capital_additions_incl_idc": asset}


def build(ctx: BuildContext) -> None:
    want = oracle(ctx.inputs)
    c = ctx.calcs
    r, w = float(ctx.inputs["idc_rate"]), float(ctx.inputs["idc_weight"])
    draw, capex = ctx.values("debt_funded_capex"), ctx.values("capital_additions")
    close = want["debt_closing"]
    idc = want["idc_capitalised"]
    open_v = [float(ctx.inputs["opening_debt"]), *close[:-1]]
    wd = [w * d for d in draw]
    base = [o + x for o, x in zip(open_v, wd, strict=True)]
    gross = [r * x for x in base]
    denom = [1 - w * r] * ctx.n
    b = ctx.block(T)
    first = c.next_row
    close_row = first + 12
    b.link_prev("open", close_row, "Debt, opening (USD)", values=open_v)
    b.link("draw", ctx.source("debt_funded_capex"), "Debt-funded capex drawn (USD)", values=draw)
    b.link("w", ctx.source("idc_weight"), "Share of the period's draw that bears interest (ratio)",
           values=ctx.values("idc_weight"))  # fmt: skip
    b.calc("wd", "Draw bearing interest (USD)", "{w}*{draw}", values=wd)
    b.calc("base", "Balance bearing interest before IDC (USD)", "{open}+{wd}", values=base)
    b.link(
        "rate",
        ctx.source("idc_rate"),
        "Interest rate per period (ratio)",
        values=ctx.values("idc_rate"),
    )
    b.calc(
        "gross", "Interest before the circularity is solved (USD)", "{rate}*{base}", values=gross
    )
    b.link("w2", ctx.source("idc_weight"), "Share of the period's draw that bears interest (ratio)",
           values=ctx.values("idc_weight"))  # fmt: skip
    b.calc("denom", "Circularity factor, 1 - weight x rate (ratio)", "1-{w2}*{rate}", values=denom)
    b.calc("idc", "Interest capitalised, circularity solved (USD)", "{gross}/{denom}",
           key=ctx.key("idc_capitalised"), values=idc)  # fmt: skip
    b.link("draw2", ctx.source("debt_funded_capex"), "Debt-funded capex drawn (USD)", values=draw)
    b.link_prev("open2", close_row, "Debt, opening (USD)", values=open_v)
    b.calc("close", "Debt, closing (USD)", "{open2}+{draw2}+{idc}",
           key=ctx.key("debt_closing"), values=close)  # fmt: skip
    assert c.rows()[ctx.key("debt_closing")] == close_row
    c.ws[f"{c.workbook.open_col}{close_row}"] = f"={ctx.source('opening_debt')}"
    b.link(
        "capex", ctx.source("capital_additions"), "Capital additions before IDC (USD)", values=capex
    )
    b.calc("asset", "Capital additions including IDC (USD)", "{capex}+{idc}",
           key=ctx.key("capital_additions_incl_idc"), values=want["capital_additions_incl_idc"])  # fmt: skip


def checks(ctx: BuildContext) -> dict[str, str]:
    c = ctx.calcs
    r = c.rows()
    cols = list(c.workbook.period_cols)
    first = cols[0]
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col)  # noqa: E731
    B = lambda name, x: f"{x.col}{r[f'_{T[:18]}_{name}']}"  # noqa: E731
    K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
    krow = lambda port: r[ctx.key(port)]  # noqa: E731
    sheet, ref = src["debt_funded_capex"].split("!", 1)
    drow = ref.removeprefix("{col}")
    absum = lambda parts: "=" + "+".join(f"ABS({p})" for p in parts)  # noqa: E731
    zero = [0.0] * ctx.n

    def opening(
        x,
    ):  # debt at the start of the period, from cumulative sums of the ports and results
        if x.i == 1:
            return src["opening_debt"]
        p = cols[x.i - 2]
        return (f"({src['opening_debt']}+SUM({sheet}!${first}{drow}:{p}{drow})"
                f"+SUM(${first}{krow('idc_capitalised')}:{p}{krow('idc_capitalised')}))")  # fmt: skip

    c.section("Checks")
    c.row("chk_circularity", "  Check - interest satisfies its circular definition (USD)",
          lambda x: f"={K('idc_capitalised', x)}-{src['idc_rate']}*({opening(x)}"
                    f"+{src['idc_weight']}*({S('debt_funded_capex', x)}+{K('idc_capitalised', x)}))",
          values=zero)  # fmt: skip
    c.row("chk_debt", "  Check - closing debt re-derived (USD)",
          lambda x: f"={K('debt_closing', x)}-({opening(x)}+{S('debt_funded_capex', x)}"
                    f"+{K('idc_capitalised', x)})", values=zero)  # fmt: skip
    c.row("chk_rows", "  Check - links and intermediate rows re-derived (USD)",
          lambda x: absum([
              B("draw", x) + "-" + S("debt_funded_capex", x), B("draw2", x) + "-" + S("debt_funded_capex", x),
              B("w", x) + "-" + src["idc_weight"], B("w2", x) + "-" + src["idc_weight"],
              B("rate", x) + "-" + src["idc_rate"], B("capex", x) + "-" + S("capital_additions", x),
              B("open", x) + "-" + opening(x), B("open2", x) + "-" + opening(x),
              B("wd", x) + f"-{src['idc_weight']}*{S('debt_funded_capex', x)}",
              B("base", x) + f"-({opening(x)}+{src['idc_weight']}*{S('debt_funded_capex', x)})",
              B("gross", x) + f"-{src['idc_rate']}*{B('base', x)}",
              B("denom", x) + f"-(1-{src['idc_weight']}*{src['idc_rate']})",
              K("capital_additions_incl_idc", x) + f"-({S('capital_additions', x)}+{K('idc_capitalised', x)})",
          ]), values=zero)  # fmt: skip
    return {
        "circularity": "Check - interest satisfies its circular definition",
        "debt": "Check - closing debt re-derived",
        "rows": "Check - links and intermediate rows re-derived",
    }


IDC = Module(
    name="idc",
    version="0.1.0",
    scope={
        "in": [
            "Interest on debt drawn during construction at one rate per period",
            "The capitalised-interest circularity solved in closed form, with a weight: 0 opening "
            "balance, 0.5 average balance, 1 closing balance",
            "Capitalisation to the debt balance and to the asset's cost",
            "A check that the interest satisfies its own circular definition",
        ],
        "out": [
            "Commitment and arrangement fees, and any fee financed by the debt",
            "Draws that depend on IDC (draw-to-need: see the senior debt module)",
            "A rate that changes over time, floating rates and hedging",
            "Tax treatment of IDC (it joins the asset base through the capital additions output)",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "debt_funded_capex": [500.0, 1000.0, 1000.0, 500.0],
        "capital_additions": [700.0, 1400.0, 1400.0, 700.0],
        "idc_rate": 0.02,
        "idc_weight": 0.5,
        "opening_debt": 100.0,
    },
    golden=Golden(
        inputs={
            "debt_funded_capex": [300.0, 600.0, 600.0, 300.0],
            "capital_additions": [450.0, 900.0, 900.0, 450.0],
            "idc_rate": 0.015,
            "idc_weight": 0.5,
            "opening_debt": 0.0,
        },
        outputs={
            "idc_capitalised": [
                2.2670025188916876,
                9.102272078371158,
                18.30784797879994,
                25.38554845203117,
            ],
            "debt_closing": [
                302.2670025188917,
                911.3692745972628,
                1529.6771225760626,
                1855.0626710280937,
            ],
            "capital_additions_incl_idc": [
                452.2670025188917,
                909.1022720783711,
                918.3078479787999,
                475.3855484520312,
            ],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/idc.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = IDC
