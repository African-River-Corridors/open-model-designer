"""Capex profile and funding split.

    capex spend      = total capex x spend profile (shares of the total per period)
    capital additions = capex spend + development cost
    debt funded      = debt share x capex spend
    equity funded    = (1 - debt share) x capex spend + development cost   (development cost is equity)

The profile must sum to 1: a check row reads non-zero in the last period if it does not.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port

INPUTS = (
    Port("total_capex", "USD", "scalar"),
    Port("spend_profile", "ratio", "series"),
    Port("development_cost", "USD", "series"),
    Port("debt_share", "ratio", "scalar"),
)
OUTPUTS = (
    Port("capital_additions", "USD", "series"),
    Port("debt_funded_capex", "USD", "series"),
    Port("equity_contribution", "USD", "series"),
)
T = "Capex funding"


def oracle(inputs: dict) -> dict[str, list[float]]:
    total, share = float(inputs["total_capex"]), float(inputs["debt_share"])
    spend = [total * float(p) for p in inputs["spend_profile"]]
    dev = [float(d) for d in inputs["development_cost"]]
    return {
        "capital_additions": [s + d for s, d in zip(spend, dev, strict=True)],
        "debt_funded_capex": [share * s for s in spend],
        "equity_contribution": [(1 - share) * s + d for s, d in zip(spend, dev, strict=True)],
    }


def build(ctx: BuildContext) -> None:
    want = oracle(ctx.inputs)
    total, share = float(ctx.inputs["total_capex"]), float(ctx.inputs["debt_share"])
    prof, dev = ctx.values("spend_profile"), ctx.values("development_cost")
    spend = [total * p for p in prof]
    core = [(1 - share) * s for s in spend]
    b = ctx.block(T)
    b.link(
        "total", ctx.source("total_capex"), "Total capex (USD)", values=ctx.values("total_capex")
    )
    b.link(
        "prof",
        ctx.source("spend_profile"),
        "Share of capex spent in the period (ratio)",
        values=prof,
    )
    b.calc("spend", "Capex spend (USD)", "{total}*{prof}", values=spend)
    b.link("dev", ctx.source("development_cost"), "Development cost (USD)", values=dev)
    b.calc("capex", "Capital additions (USD)", "{spend}+{dev}",
           key=ctx.key("capital_additions"), values=want["capital_additions"])  # fmt: skip
    b.link("share", ctx.source("debt_share"), "Debt share of capex (ratio)",
           values=ctx.values("debt_share"))  # fmt: skip
    b.calc("debt", "Debt-funded capex (USD)", "{share}*{spend}",
           key=ctx.key("debt_funded_capex"), values=want["debt_funded_capex"])  # fmt: skip
    b.calc(
        "core", "Equity-funded capex before development cost (USD)", "{spend}-{debt}", values=core
    )
    b.calc("equity", "Equity contribution (USD)", "{core}+{dev}",
           key=ctx.key("equity_contribution"), values=want["equity_contribution"])  # fmt: skip


def checks(ctx: BuildContext) -> dict[str, str]:
    c = ctx.calcs
    r = c.rows()
    cols = list(c.workbook.period_cols)
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col)  # noqa: E731
    B = lambda name, x: f"{x.col}{r[f'_{T[:18]}_{name}']}"  # noqa: E731
    K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
    absum = lambda parts: "=" + "+".join(f"ABS({p})" for p in parts)  # noqa: E731
    zero = [0.0] * ctx.n
    sheet, ref = src["spend_profile"].split("!", 1)
    prow = ref.removeprefix("{col}")
    spend = lambda x: f"{src['total_capex']}*{S('spend_profile', x)}"  # noqa: E731
    c.section("Checks")
    c.row("chk_links", "  Check - linked inputs equal their ports (USD)",
          lambda x: absum([B("total", x) + "-" + src["total_capex"], B("prof", x) + "-" + S("spend_profile", x),
                           B("dev", x) + "-" + S("development_cost", x),
                           B("share", x) + "-" + src["debt_share"]]), values=zero)  # fmt: skip
    c.row("chk_rows", "  Check - each row re-derived from the ports (USD)",
          lambda x: absum([
              B("spend", x) + "-" + spend(x),
              K("capital_additions", x) + f"-({spend(x)}+{S('development_cost', x)})",
              K("debt_funded_capex", x) + f"-{src['debt_share']}*{spend(x)}",
              B("core", x) + f"-(1-{src['debt_share']})*{spend(x)}",
              K("equity_contribution", x) + f"-((1-{src['debt_share']})*{spend(x)}+{S('development_cost', x)})",
          ]), values=zero)  # fmt: skip
    c.row("chk_sources_uses", "  Check - debt plus equity equals capital additions (USD)",
          lambda x: f"={K('debt_funded_capex', x)}+{K('equity_contribution', x)}-{K('capital_additions', x)}",
          values=zero)  # fmt: skip
    last = cols[-1]
    c.row("chk_profile", "  Check - spend profile sums to one (ratio)",
          lambda x: f"=SUM({sheet}!${cols[0]}{prow}:{last}{prow})-1" if x.col == last else "=0",
          values=zero)  # fmt: skip
    return {
        "links": "Check - linked inputs equal their ports",
        "rows": "Check - each row re-derived from the ports",
        "sources_uses": "Check - debt plus equity equals capital additions",
        "profile": "Check - spend profile sums to one",
    }


CAPEX_FUNDING = Module(
    name="capex_funding",
    version="0.1.0",
    scope={
        "in": [
            "Total capex spread over the build by a spend profile that must sum to one",
            "A debt share applied to capex spend; the rest is equity",
            "Development cost as a series, funded wholly by equity and added to capital additions",
            "A sources-and-uses check: debt plus equity equals capital additions",
        ],
        "out": [
            "Interest during construction and fees (see the IDC module)",
            "Draw-to-need and availability limits (see the senior debt modules)",
            "Contingency, escalation and FX on capex",
            "A debt share that changes over time",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "total_capex": 1000.0,
        "spend_profile": [0.25, 0.25, 0.25, 0.25],
        "development_cost": [50.0, 0.0, 20.0, 0.0],
        "debt_share": 0.6,
    },
    golden=Golden(
        inputs={
            "total_capex": 10000.0,
            "spend_profile": [0.4, 0.3, 0.2, 0.1],
            "development_cost": [200.0, 0.0, 0.0, 100.0],
            "debt_share": 0.7,
        },
        outputs={
            "capital_additions": [4200.0, 3000.0, 2000.0, 1100.0],
            "debt_funded_capex": [2800.0, 2100.0, 1400.0, 700.0],
            "equity_contribution": [1400.0, 900.0, 600.0, 400.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/capex_funding.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = CAPEX_FUNDING
