"""Debt service reserve account.

    target       = sum of the next WINDOW periods' debt service        (months of P&I ahead)
    top-up       = min(max(target - balance, 0), cash available) x funding gate
    release      = max(balance - target, 0)                          (target falls as debt is repaid)
    balance      = brought forward + top-up - release                 (restricted cash)

The balance is restricted cash: it is held, not available to distributions until released.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port
from ._plan_module import build_plan, plan_checks

WINDOW = 2  # periods of debt service ahead that the reserve must cover (built into the module)
INPUTS = (
    Port("debt_service", "USD", "series"),
    Port("cash_available_for_dsra", "USD", "series"),
    Port("dsra_funding_gate", "count", "series"),
    Port("opening_dsra", "USD", "scalar"),
)
OUTPUTS = (
    Port("dsra_target", "USD", "series"),
    Port("dsra_transfer_in", "USD", "series"),
    Port("dsra_release", "USD", "series"),
    Port("dsra_closing", "USD", "series"),
)
T = "DSRA"
KEYED = {
    "target": "dsra_target",
    "fund": "dsra_transfer_in",
    "release": "dsra_release",
    "close": "dsra_closing",
}
PLAN = [
    ("link", "nxt", "Debt service over the next periods (USD)", "@dsra_next_service"),
    ("calc", "target", "DSRA target (USD)", "{nxt}"),
    ("lp", "open", "DSRA, opening (USD)", "dsra_closing"),
    ("calc", "short", "Shortfall against target (USD)", "MAX({target}-{open},0)"),
    ("link", "cash", "Cash available for the DSRA (USD)", "cash_available_for_dsra"),
    ("link", "gate", "Funding allowed in the period (flag)", "dsra_funding_gate"),
    ("calc", "fund", "Top-up transferred in (USD)", "MIN({short},{cash})*{gate}"),
    ("relink", "tgt2", "DSRA target (USD)", "target"),
    ("lp", "open2", "DSRA, opening (USD)", "dsra_closing"),
    ("calc", "release", "Released to cash (USD)", "MAX({open2}-{tgt2},0)"),
    ("relink", "fund2", "Top-up transferred in (USD)", "fund"),
    ("lp", "open3", "DSRA, opening (USD)", "dsra_closing"),
    ("calc", "close", "DSRA, closing (USD)", "{open3}+{fund2}-{release}"),
]


def oracle(inputs: dict) -> dict[str, list[float]]:
    bal = float(inputs["opening_dsra"])
    ds = [float(x) for x in inputs["debt_service"]]
    out = {p.name: [] for p in OUTPUTS}
    for i in range(len(ds)):
        target = sum(ds[i + 1 : i + 1 + WINDOW])
        fund = min(max(target - bal, 0.0), float(inputs["cash_available_for_dsra"][i])) * float(
            inputs["dsra_funding_gate"][i]
        )
        release = max(bal - target, 0.0)
        bal = bal + fund - release
        for k, v in (
            ("dsra_target", target),
            ("dsra_transfer_in", fund),
            ("dsra_release", release),
            ("dsra_closing", bal),
        ):
            out[k].append(v)
    return out


def _values(inputs):
    bal = float(inputs["opening_dsra"])
    ds = [float(x) for x in inputs["debt_service"]]
    V = {
        k: []
        for k in (
            "nxt",
            "target",
            "open",
            "open2",
            "open3",
            "short",
            "fund",
            "tgt2",
            "release",
            "fund2",
            "close",
        )
    }
    for i in range(len(ds)):
        target = sum(ds[i + 1 : i + 1 + WINDOW])
        short = max(target - bal, 0.0)
        fund = min(short, float(inputs["cash_available_for_dsra"][i])) * float(
            inputs["dsra_funding_gate"][i]
        )
        release = max(bal - target, 0.0)
        row = {"nxt": target, "target": target, "open": bal, "open2": bal, "open3": bal, "short": short, "fund": fund,
               "tgt2": target, "release": release, "fund2": fund}  # fmt: skip
        bal = bal + fund - release
        row["close"] = bal
        for k, v in row.items():
            V[k].append(v)
    return V


def _next_service_row(ctx: BuildContext) -> None:
    """Debt service over the next WINDOW periods in its own row (FAST 2.02-06)."""
    c = ctx.calcs
    ds = [float(x) for x in ctx.inputs["debt_service"]]
    sheet, ref = ctx.source("debt_service").split("!", 1)
    row = ref.removeprefix("{col}")

    from openpyxl.utils import column_index_from_string, get_column_letter

    left = c.rows()["periods_left"]

    def ahead(
        x,
    ):  # each of the next WINDOW periods is added only if it exists; no cell past the last period is read
        k = column_index_from_string(x.col)
        terms = [
            f"{sheet}!{get_column_letter(k + j)}{row}*({x.col}{left}>{j - 1})"
            for j in range(1, WINDOW + 1)
        ]
        return "=" + "+".join(terms)

    c.skip_rows()
    c.section("DSRA look-ahead")
    c.row("dsra_next_service", "  Debt service over the next periods (USD)", ahead,
          values=[sum(ds[i + 1 : i + 1 + WINDOW]) for i in range(len(ds))])  # fmt: skip


def build(ctx: BuildContext) -> None:
    _next_service_row(ctx)
    build_plan(ctx, T, PLAN, _values(ctx.inputs), KEYED, {"dsra_closing": "opening_dsra"})


def checks(ctx: BuildContext) -> dict[str, str]:
    c = ctx.calcs
    r = c.rows()
    cols = list(c.workbook.period_cols)
    first = cols[0]
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col)  # noqa: E731
    K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
    krow = lambda port: r[ctx.key(port)]  # noqa: E731
    sheet, ref = src["debt_service"].split("!", 1)
    drow = ref.removeprefix("{col}")
    zero = [0.0] * ctx.n

    def bal(x):  # brought-forward balance from cumulative flows
        if x.i == 1:
            return src["opening_dsra"]
        p = cols[x.i - 2]
        return (f"({src['opening_dsra']}+SUM(${first}{krow('dsra_transfer_in')}:{p}{krow('dsra_transfer_in')})"
                f"-SUM(${first}{krow('dsra_release')}:{p}{krow('dsra_release')}))")  # fmt: skip

    def target(x):
        if x.i >= ctx.n:
            return "0"
        return f"SUM({sheet}!{cols[x.i]}{drow}:{cols[min(x.i + WINDOW, ctx.n) - 1]}{drow})"

    c.section("Checks")
    c.row("chk_flows", "  Check - target, top-up, release and balance re-derived from the ports (USD)",
          lambda x: f"=ABS({K('dsra_target', x)}-{target(x)})"
                    f"+ABS({K('dsra_transfer_in', x)}-MIN(MAX({target(x)}-{bal(x)},0),{S('cash_available_for_dsra', x)})*{S('dsra_funding_gate', x)})"
                    f"+ABS({K('dsra_release', x)}-MAX({bal(x)}-{target(x)},0))"
                    f"+ABS({K('dsra_closing', x)}-({bal(x)}+{K('dsra_transfer_in', x)}-{K('dsra_release', x)}))"
                    f"+MAX(-{K('dsra_closing', x)},0)", values=zero)  # fmt: skip
    label = plan_checks(ctx, T, PLAN, KEYED, lambda port, x: bal(x))
    return {"flows": "Check - target, top-up, release and balance re-derived", "rows": label}


DSRA = Module(
    name="dsra",
    version="0.1.0",
    scope={
        "in": [
            "A target of the sum of the next two periods' debt service (the window is built in)",
            "Top-up from cash available, never more than the shortfall, switched by a funding gate",
            "Release of any balance above the target (the target falls as the debt is repaid)",
            "The balance as restricted cash, with a brought-forward balance",
        ],
        "out": [
            "A target window other than two periods, or one given as an input",
            "Letters of credit in place of cash, and interest earned on the balance",
            "The order of cash tiers and lock-up (see the waterfall and lock-up modules)",
            "Initial funding at financial close from the sources and uses",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "debt_service": [0.0, 200.0, 200.0, 150.0],
        "cash_available_for_dsra": [500.0, 150.0, 500.0, 500.0],
        "dsra_funding_gate": [1.0, 1.0, 1.0, 1.0],
        "opening_dsra": 0.0,
    },
    golden=Golden(
        inputs={
            "debt_service": [0.0, 300.0, 300.0, 100.0],
            "cash_available_for_dsra": [200.0, 100.0, 400.0, 400.0],
            "dsra_funding_gate": [1.0, 0.0, 1.0, 1.0],
            "opening_dsra": 50.0,
        },
        outputs={
            "dsra_target": [600.0, 400.0, 100.0, 0.0],
            "dsra_transfer_in": [200.0, 0.0, 0.0, 0.0],
            "dsra_release": [0.0, 0.0, 150.0, 100.0],
            "dsra_closing": [250.0, 250.0, 100.0, 0.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); standard practice: target is the sum of the next two periods; the funding gate shuts while a top-up is needed; working in docs/golden-cases/dsra_3.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = DSRA
