"""Toy module: an output levy on revenue.

levy = revenue x rate;  revenue_gross = revenue + levy.

It exists to show the contract and to pass acceptance. It is not a library module and carries no
jurisdiction.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port

REVENUE = [1000.0, 2000.0, 3000.0, 4000.0]


def oracle(inputs: dict) -> dict[str, list[float]]:
    rate = float(inputs["levy_rate"])
    rev = [float(x) for x in inputs["revenue"]]
    levy = [r * rate for r in rev]
    return {"tax_paid": levy, "revenue_gross": [r + v for r, v in zip(rev, levy, strict=True)]}


def build(ctx: BuildContext) -> None:
    b = ctx.block("Output levy")
    n = ctx.n
    b.link("rev", ctx.source("revenue"), "Revenue (USD)", values=ctx.values("revenue"))
    b.link("rate", ctx.source("levy_rate"), "Levy rate (ratio)", values=ctx.values("levy_rate"))
    want = oracle(ctx.inputs)
    b.calc("levy", "Levy (USD)", "{rev}*{rate}", key=ctx.key("tax_paid"), values=want["tax_paid"])
    b.link("rev2", ctx.source("revenue"), "Revenue (USD), restated", values=ctx.values("revenue"))
    b.link("levy2", ctx.key("tax_paid"), "Levy (USD), restated", values=want["tax_paid"])
    b.calc("gross", "Revenue incl. levy (USD)", "{rev2}+{levy2}", key=ctx.key("revenue_gross"),
           values=want["revenue_gross"])  # fmt: skip
    assert len(want["tax_paid"]) == n


def checks(ctx: BuildContext) -> dict[str, str]:
    """Each check re-derives a row from the raw ports, by a different route, and must read 0."""
    c = ctx.calcs
    rows = c.rows()
    rate_ref, rev_src = ctx.source("levy_rate"), ctx.source("revenue")
    levy_row, gross_row = rows[ctx.key("tax_paid")], rows[ctx.key("revenue_gross")]
    c.section("Checks")
    c.row("chk_levy", "  Check - levy re-derived (USD)",
          lambda x: f"={x.col}{levy_row}-{rev_src.format(col=x.col)}*{rate_ref}",
          values=[0.0] * ctx.n)  # fmt: skip
    c.row("chk_gross", "  Check - gross re-derived (USD)",
          lambda x: f"={x.col}{gross_row}-{rev_src.format(col=x.col)}*(1+{rate_ref})",
          values=[0.0] * ctx.n)  # fmt: skip
    return {"levy": "Check - levy re-derived", "gross": "Check - gross re-derived"}


LEVY = Module(
    name="levy",
    version="0.1.0",
    scope={
        "in": [
            "A flat levy rate applied to revenue in every period",
            "The gross-up of revenue by the levy",
        ],
        "out": [
            "Rate changes over time",
            "Thresholds, exemptions or recovery of the levy",
            "Any jurisdiction",
        ],
    },
    inputs=(
        Port("revenue", "USD", "series"),
        Port("levy_rate", "ratio", "scalar"),
    ),
    outputs=(
        Port("tax_paid", "USD", "series"),
        Port("revenue_gross", "USD", "series"),
    ),
    oracle=oracle,
    build=build,
    checks=checks,
    example={"revenue": REVENUE, "levy_rate": 0.125},
    golden=Golden(
        inputs={"revenue": [800.0, 1600.0, 2400.0, 3200.0], "levy_rate": 0.2},
        outputs={
            "tax_paid": [160.0, 320.0, 480.0, 640.0],
            "revenue_gross": [960.0, 1920.0, 2880.0, 3840.0],
        },
        source="Hand calculation: 20% of 800 is 160; 800 + 160 is 960. Checked on paper, 2026-10-22.",
        kind="hand-calculation",
    ),
)
MODULE = LEVY
