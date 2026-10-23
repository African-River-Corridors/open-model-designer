"""FX conversion: flows at the period rate, balances at the closing rate.

    closing rate    = prior closing rate x (1 - depreciation)       (the first period starts from the start rate)
    period rate     = average of the opening and the closing rate
    flow, reporting = flow in local currency x period rate
    balance, local  = brought forward + flow                         (the flow is the balance's movement)
    balance, reporting = balance in local currency x closing rate
    translation difference = closing balance - (opening balance converted at the opening rate + flow converted)

Rates are units of reporting currency per unit of local currency. A positive depreciation lowers the rate.
The translation difference is what keeps the converted balance and the converted flows reconciled.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port
from ._plan_module import build_plan, plan_checks

INPUTS = (
    Port("fx_start_rate", "ratio", "scalar"),
    Port("fx_depreciation", "ratio", "series"),
    Port("flow_local", "LCU", "series"),
    Port("opening_balance_local", "LCU", "scalar"),
)
OUTPUTS = (
    Port("fx_closing_rate", "ratio", "series"),
    Port("fx_period_rate", "ratio", "series"),
    Port("flow_reporting", "USD", "series"),
    Port("balance_closing_local", "LCU", "series"),
    Port("balance_closing_reporting", "USD", "series"),
    Port("fx_translation_difference", "USD", "series"),
)
T = "FX conversion"
KEYED = {
    "rclose": "fx_closing_rate",
    "ravg": "fx_period_rate",
    "flow_rep": "flow_reporting",
    "bclose": "balance_closing_local",
    "bclose_rep": "balance_closing_reporting",
    "diff": "fx_translation_difference",
}
PLAN = [
    ("lp", "ropen", "Rate, opening (ratio)", "fx_closing_rate"),
    ("link", "dep", "Depreciation of the local currency in the period (ratio)", "fx_depreciation"),
    ("calc", "rclose", "Rate, closing (ratio)", "{ropen}*(1-{dep})"),
    ("lp", "ropen2", "Rate, opening (ratio)", "fx_closing_rate"),
    ("relink", "rclose2", "Rate, closing (ratio)", "rclose"),
    ("calc", "ravg", "Rate, period average (ratio)", "({ropen2}+{rclose2})/2"),
    ("link", "flow", "Flow in local currency (LCU)", "flow_local"),
    ("relink", "ravg2", "Rate, period average (ratio)", "ravg"),
    ("calc", "flow_rep", "Flow in reporting currency (USD)", "{flow}*{ravg2}"),
    ("lp", "bopen", "Balance, opening, local currency (LCU)", "balance_closing_local"),
    ("link", "flow2", "Flow in local currency (LCU)", "flow_local"),
    ("calc", "bclose", "Balance, closing, local currency (LCU)", "{bopen}+{flow2}"),
    ("relink", "bclose2", "Balance, closing, local currency (LCU)", "bclose"),
    ("relink", "rclose3", "Rate, closing (ratio)", "rclose"),
    ("calc", "bclose_rep", "Balance, closing, at the closing rate (USD)", "{bclose2}*{rclose3}"),
    ("lp", "bopen2", "Balance, opening, local currency (LCU)", "balance_closing_local"),
    ("lp", "ropen3", "Rate, opening (ratio)", "fx_closing_rate"),
    ("calc", "bopen_rep", "Balance, opening, at the opening rate (USD)", "{bopen2}*{ropen3}"),
    ("relink", "flow_rep2", "Flow in reporting currency (USD)", "flow_rep"),
    ("relink", "bclose_rep2", "Balance, closing, at the closing rate (USD)", "bclose_rep"),
    ("calc", "diff", "Translation difference (USD)", "{bclose_rep2}-{bopen_rep}-{flow_rep2}"),
]


def _run(inputs):
    rate, bal = float(inputs["fx_start_rate"]), float(inputs["opening_balance_local"])
    V: dict[str, list[float]] = {name: [] for _k, name, _l, _s in PLAN}
    for dep, flow in zip(inputs["fx_depreciation"], inputs["flow_local"], strict=True):
        dep, flow = float(dep), float(flow)
        rclose = rate * (1 - dep)
        ravg = (rate + rclose) / 2
        flow_rep = flow * ravg
        bclose = bal + flow
        bclose_rep = bclose * rclose
        bopen_rep = bal * rate
        row = {"ropen": rate, "dep": dep, "rclose": rclose, "ropen2": rate, "rclose2": rclose, "ravg": ravg,
               "flow": flow, "ravg2": ravg, "flow_rep": flow_rep, "bopen": bal, "flow2": flow, "bclose": bclose,
               "bclose2": bclose, "rclose3": rclose, "bclose_rep": bclose_rep, "bopen2": bal, "ropen3": rate,
               "bopen_rep": bopen_rep, "flow_rep2": flow_rep, "bclose_rep2": bclose_rep,
               "diff": bclose_rep - bopen_rep - flow_rep}  # fmt: skip
        rate, bal = rclose, bclose
        for k, v in row.items():
            V[k].append(v)
    return V


def oracle(inputs: dict) -> dict[str, list[float]]:
    V = _run(inputs)
    return {port: V[name] for name, port in KEYED.items()}


def build(ctx: BuildContext) -> None:
    build_plan(
        ctx, T, PLAN, _run(ctx.inputs), KEYED,
        {"fx_closing_rate": "fx_start_rate", "balance_closing_local": "opening_balance_local"},
    )  # fmt: skip


def checks(ctx: BuildContext) -> dict[str, str]:
    c = ctx.calcs
    r = c.rows()
    cols = list(c.workbook.period_cols)
    first = cols[0]
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col)  # noqa: E731
    K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
    kr = lambda port: r[ctx.key(port)]  # noqa: E731
    sheet, ref = src["flow_local"].split("!", 1)
    frow = ref.removeprefix("{col}")
    zero = [0.0] * ctx.n

    def upto(row, x, sheet_name=""):  # cumulative sum of a row from the first period to x
        return f"SUM({sheet_name}${first}{row}:{x.col}{row})"

    def rate_prev(x):  # closing rate of the period before, from the output row itself
        return src["fx_start_rate"] if x.i == 1 else f"{cols[x.i - 2]}{kr('fx_closing_rate')}"

    def bal_prev(x):  # local balance brought forward from the cumulative flows
        if x.i == 1:
            return src["opening_balance_local"]
        p = cols[x.i - 2]
        return f"({src['opening_balance_local']}+SUM({sheet}!${first}{frow}:{p}{frow}))"

    c.section("Checks")
    c.row("chk_fx", "  Check - rates, converted flow and balances re-derived from the ports (USD)",
          lambda x: f"=ABS({K('fx_closing_rate', x)}-{rate_prev(x)}*(1-{S('fx_depreciation', x)}))"
                    f"+ABS({K('fx_period_rate', x)}-({rate_prev(x)}+{K('fx_closing_rate', x)})/2)"
                    f"+ABS({K('flow_reporting', x)}-{S('flow_local', x)}*{K('fx_period_rate', x)})"
                    f"+ABS({K('balance_closing_local', x)}-({bal_prev(x)}+{S('flow_local', x)}))"
                    f"+ABS({K('balance_closing_reporting', x)}-{K('balance_closing_local', x)}*{K('fx_closing_rate', x)})"
                    f"+ABS({K('fx_translation_difference', x)}-({bal_prev(x)}*({K('fx_closing_rate', x)}-{rate_prev(x)})"
                    f"+{S('flow_local', x)}*({K('fx_closing_rate', x)}-{K('fx_period_rate', x)})))", values=zero)  # fmt: skip
    c.row("chk_articulate", "  Check - converted balance = opening + converted flows + translation differences (USD)",
          lambda x: f"=ABS({K('balance_closing_reporting', x)}-({src['opening_balance_local']}*{src['fx_start_rate']}"
                    f"+{upto(kr('flow_reporting'), x)}+{upto(kr('fx_translation_difference'), x)}))", values=zero)  # fmt: skip
    label = plan_checks(
        ctx,
        T,
        PLAN,
        KEYED,
        lambda port, x: rate_prev(x) if port == "fx_closing_rate" else bal_prev(x),
    )
    return {
        "fx": "Check - rates, converted flow and balances re-derived",
        "articulate": "Check - converted balance = opening + converted flows + translation differences",
        "rows": label,
    }


FX_CONVERSION = Module(
    name="fx_conversion",
    version="0.1.0",
    scope={
        "in": [
            "A closing-rate path from a start rate and a depreciation per period",
            "The period rate as the simple average of the opening and the closing rate",
            "Flows converted at the period rate, balances at the closing rate",
            "A local-currency balance rolled forward by its flow, and the translation difference that reconciles it",
        ],
        "out": [
            "Rate forecasts (the depreciation path is an input, e.g. from inflation parity)",
            "Hedging, FX gains and losses on monetary items, and hyperinflation accounting",
            "Several currencies at once (one conversion per currency)",
            "Weighted-average rates by flow timing within a period",
            "The inverse quote (local currency per reporting unit): the depreciation is applied to the rate as quoted, closing = opening x (1 - depreciation)",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "fx_start_rate": 0.1,
        "fx_depreciation": [0.05, 0.1, -0.02, 0.0],
        "flow_local": [1000.0, 500.0, -300.0, 200.0],
        "opening_balance_local": 400.0,
    },
    golden=Golden(
        inputs={
            "fx_start_rate": 0.08,
            "fx_depreciation": [0.1, 0.05, 0.0, -0.04],
            "flow_local": [1000.0, -400.0, 600.0, 250.0],
            "opening_balance_local": 500.0,
        },
        outputs={
            "fx_closing_rate": [0.072, 0.0684, 0.0684, 0.071136],
            "fx_period_rate": [0.076, 0.0702, 0.0684, 0.069768],
            "flow_reporting": [76.0, -28.08, 41.04, 17.442],
            "balance_closing_local": [1500.0, 1100.0, 1700.0, 1950.0],
            "balance_closing_reporting": [108.0, 75.24, 116.28, 138.7152],
            "fx_translation_difference": [-8.0, -4.68, 0.0, 4.9932],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/fx_conversion.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = FX_CONVERSION
