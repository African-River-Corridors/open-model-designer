"""Take-or-pay revenue: contracted minimum against delivered volume, and the shortfall payment.

    sales            = delivered volume x price
    shortfall volume = max(contracted minimum - delivered volume, 0)
    shortfall payment = shortfall volume x price x share of the price payable on a shortfall
    revenue          = sales + shortfall payment

Delivered volume above the minimum is paid at the price; volume below it is paid for at the shortfall share.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port
from ._plan_module import build_plan, plan_checks

INPUTS = (
    Port("contracted_minimum", "units", "series"),
    Port("delivered_volume", "units", "series"),
    Port("unit_price", "USD/unit", "scalar"),
    Port("shortfall_payment_share", "ratio", "scalar"),
)
OUTPUTS = (
    Port("sales_revenue", "USD", "series"),
    Port("shortfall_volume", "units", "series"),
    Port("shortfall_payment", "USD", "series"),
    Port("revenue", "USD", "series"),
)
T = "Take-or-pay"
KEYED = {
    "sales": "sales_revenue",
    "short": "shortfall_volume",
    "top": "shortfall_payment",
    "rev": "revenue",
}
PLAN = [
    ("link", "vol", "Delivered volume (units)", "delivered_volume"),
    ("link", "price", "Price (USD/unit)", "unit_price"),
    ("calc", "sales", "Sales at the price (USD)", "{vol}*{price}"),
    ("link", "min", "Contracted minimum (units)", "contracted_minimum"),
    ("link", "vol2", "Delivered volume (units)", "delivered_volume"),
    ("calc", "short", "Shortfall against the minimum (units)", "MAX({min}-{vol2},0)"),
    ("relink", "short2", "Shortfall against the minimum (units)", "short"),
    ("link", "price2", "Price (USD/unit)", "unit_price"),
    (
        "link",
        "share",
        "Share of the price payable on a shortfall (ratio)",
        "shortfall_payment_share",
    ),
    ("calc", "top", "Shortfall payment (USD)", "{short2}*{price2}*{share}"),
    ("relink", "sales2", "Sales at the price (USD)", "sales"),
    ("relink", "top2", "Shortfall payment (USD)", "top"),
    ("calc", "rev", "Revenue (USD)", "{sales2}+{top2}"),
]


def _run(inputs):
    price, share = float(inputs["unit_price"]), float(inputs["shortfall_payment_share"])
    V: dict[str, list[float]] = {name: [] for _k, name, _l, _s in PLAN}
    for mn, vol in zip(inputs["contracted_minimum"], inputs["delivered_volume"], strict=True):
        mn, vol = float(mn), float(vol)
        sales, short = vol * price, max(mn - vol, 0.0)
        top = short * price * share
        row = {"vol": vol, "price": price, "sales": sales, "min": mn, "vol2": vol, "short": short,
               "short2": short, "price2": price, "share": share, "top": top, "sales2": sales,
               "top2": top, "rev": sales + top}  # fmt: skip
        for k, v in row.items():
            V[k].append(v)
    return V


def oracle(inputs: dict) -> dict[str, list[float]]:
    V = _run(inputs)
    return {port: V[name] for name, port in KEYED.items()}


def build(ctx: BuildContext) -> None:
    build_plan(ctx, T, PLAN, _run(ctx.inputs), KEYED, {})


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

    def vol_total(port, x):
        sheet, ref = src[port].split("!", 1)
        row = ref.removeprefix("{col}")
        return f"SUM({sheet}!${first}{row}:{x.col}{row})"

    c.section("Checks")
    c.row("chk_top", "  Check - sales, shortfall and revenue re-derived from the ports (USD)",
          lambda x: f"=ABS({K('sales_revenue', x)}-{S('delivered_volume', x)}*{S('unit_price', x)})"
                    f"+ABS({K('shortfall_volume', x)}-MAX({S('contracted_minimum', x)}-{S('delivered_volume', x)},0))"
                    f"+ABS({K('shortfall_payment', x)}-MAX({S('contracted_minimum', x)}-{S('delivered_volume', x)},0)*{S('unit_price', x)}*{S('shortfall_payment_share', x)})"
                    f"+ABS({K('revenue', x)}-({K('sales_revenue', x)}+{K('shortfall_payment', x)}))", values=zero)  # fmt: skip
    c.row("chk_paid_volume", "  Check - revenue never falls below the shortfall share of the minimum at the price (USD)",
          lambda x: f"=MAX({S('contracted_minimum', x)}*{S('unit_price', x)}*{S('shortfall_payment_share', x)}-{K('revenue', x)},0)", values=zero)  # fmt: skip
    c.row("chk_cumulative", "  Check - cumulative revenue equals cumulative sales plus shortfall payments (USD)",
          lambda x: f"=ABS(SUM(${first}{kr('revenue')}:{x.col}{kr('revenue')})-({vol_total('delivered_volume', x)}*{src['unit_price']}"
                    f"+SUM(${first}{kr('shortfall_payment')}:{x.col}{kr('shortfall_payment')})))", values=zero)  # fmt: skip
    label = plan_checks(ctx, T, PLAN, KEYED, lambda port, x: "0")
    return {
        "top": "Check - sales, shortfall and revenue re-derived",
        "paid_volume": "Check - revenue never falls below the shortfall share of the minimum at the price",
        "cumulative": "Check - cumulative revenue equals cumulative sales plus shortfall payments",
        "rows": label,
    }


TAKE_OR_PAY = Module(
    name="take_or_pay",
    version="0.1.0",
    scope={
        "in": [
            "Sales of delivered volume at one price",
            "A shortfall against a contracted minimum paid for at a share of the price",
            "Revenue as sales plus shortfall payment",
        ],
        "out": [
            "An annual (contract-year) minimum test and make-up rights: the minimum is tested in every period with no carry-over (a later optional module)",
            "Excusing events, force majeure and make-up (carry-forward) rights",
            "Availability payments split into capacity and energy charges",
            "A price that varies by period or indexation (the price is one value)",
            "Deemed delivery and the offtaker's credit risk",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "contracted_minimum": [80.0, 100.0, 100.0, 100.0],
        "delivered_volume": [90.0, 70.0, 100.0, 120.0],
        "unit_price": 40.0,
        "shortfall_payment_share": 0.9,
    },
    golden=Golden(
        inputs={
            "contracted_minimum": [100.0, 100.0, 100.0, 100.0],
            "delivered_volume": [120.0, 80.0, 100.0, 0.0],
            "unit_price": 50.0,
            "shortfall_payment_share": 0.8,
        },
        outputs={
            "sales_revenue": [6000.0, 4000.0, 5000.0, 0.0],
            "shortfall_volume": [0.0, 20.0, 0.0, 100.0],
            "shortfall_payment": [0.0, 800.0, 0.0, 4000.0],
            "revenue": [6000.0, 4800.0, 5000.0, 4000.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/take_or_pay.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = TAKE_OR_PAY
