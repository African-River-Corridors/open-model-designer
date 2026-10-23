"""Fixed assets, book.

Gross cost rolls forward with additions. Straight-line book depreciation is cumulative gross cost
divided by the useful life, times the share of the period in use, never more than the net book
value before depreciation (so NBV never goes below nil).

    gross carried   = gross brought forward + additions
    net book value before depreciation = gross carried - accumulated depreciation brought forward
    depreciation    = share in use x min(gross carried / life, net book value before)
    NBV             = gross carried - accumulated depreciation carried
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port

INPUTS = (
    Port("capital_additions", "USD", "series"),
    Port("use_fraction", "ratio", "series"),
    Port("useful_life", "periods", "scalar"),
    Port("opening_gross", "USD", "scalar"),
    Port("opening_accum_depreciation", "USD", "scalar"),
)
OUTPUTS = (
    Port("depreciation", "USD", "series"),
    Port("fa_gross_closing", "USD", "series"),
    Port("fa_accum_depreciation_closing", "USD", "series"),
    Port("fa_nbv_closing", "USD", "series"),
)
TITLE = "Fixed assets"


def oracle(inputs: dict) -> dict[str, list[float]]:
    life = float(inputs["useful_life"])
    gross, accum = float(inputs["opening_gross"]), float(inputs["opening_accum_depreciation"])
    out: dict[str, list[float]] = {p.name: [] for p in OUTPUTS}
    for add, use in zip(inputs["capital_additions"], inputs["use_fraction"], strict=True):
        gross += float(add)
        dep = float(use) * min(gross / life, gross - accum)
        accum += dep
        for k, v in zip(
            ("depreciation", "fa_gross_closing", "fa_accum_depreciation_closing", "fa_nbv_closing"),
            (dep, gross, accum, gross - accum),
        ):
            out[k].append(v)
    return out


def build(ctx: BuildContext) -> None:
    want = oracle(ctx.inputs)
    c = ctx.calcs
    adds = ctx.values("capital_additions")
    gross_c, accum_c = want["fa_gross_closing"], want["fa_accum_depreciation_closing"]
    gross_o = [float(ctx.inputs["opening_gross"]), *gross_c[:-1]]
    accum_o = [float(ctx.inputs["opening_accum_depreciation"]), *accum_c[:-1]]
    life = float(ctx.inputs["useful_life"])
    raw = [g / life for g in gross_c]
    nbv_pre = [g - a for g, a in zip(gross_c, accum_o, strict=True)]
    capped = [min(r, p) for r, p in zip(raw, nbv_pre, strict=True)]
    b = ctx.block(TITLE)
    b.link("adds", ctx.source("capital_additions"), "Additions (USD)", values=adds)
    first = c.next_row
    gross_row, accum_row = first + 1, first + 9
    b.link_prev("gross_open", gross_row, "Gross cost, opening (USD)", values=gross_o)
    b.calc("gross", "Gross cost, closing (USD)", "{gross_open}+{adds}",
           key=ctx.key("fa_gross_closing"), values=gross_c)  # fmt: skip
    b.link("life", ctx.source("useful_life"), "Useful life (periods)",
           values=ctx.values("useful_life"))  # fmt: skip
    b.calc("raw", "Straight-line charge on gross cost (USD)", "{gross}/{life}", values=raw)
    b.link_prev("accum_open", accum_row, "Accumulated depreciation, opening (USD)", values=accum_o)
    b.calc("nbv_pre", "Net book value before depreciation (USD)", "{gross}-{accum_open}",
           values=nbv_pre)  # fmt: skip
    b.calc("capped", "Charge floored at nil NBV (USD)", "MIN({raw},{nbv_pre})", values=capped)
    b.link("use", ctx.source("use_fraction"), "Share of period in use (ratio)",
           values=ctx.values("use_fraction"))  # fmt: skip
    b.calc("dep", "Depreciation (USD)", "{use}*{capped}",
           key=ctx.key("depreciation"), values=want["depreciation"])  # fmt: skip
    b.calc("accum", "Accumulated depreciation, closing (USD)", "{accum_open}+{dep}",
           key=ctx.key("fa_accum_depreciation_closing"), values=accum_c)  # fmt: skip
    b.relink("gross2", "gross", "Gross cost, closing (USD)")
    b.calc("nbv", "Net book value, closing (USD)", "{gross2}-{accum}",
           key=ctx.key("fa_nbv_closing"), values=want["fa_nbv_closing"])  # fmt: skip
    r = c.rows()
    assert r[ctx.key("fa_gross_closing")] == gross_row
    assert r[ctx.key("fa_accum_depreciation_closing")] == accum_row
    oc = c.workbook.open_col
    c.ws[f"{oc}{gross_row}"] = f"={ctx.source('opening_gross')}"
    c.ws[f"{oc}{accum_row}"] = f"={ctx.source('opening_accum_depreciation')}"


def checks(ctx: BuildContext) -> dict[str, str]:
    """Each check re-derives rows from the raw ports or from the row's own inputs, and reads 0."""
    c = ctx.calcs
    r = c.rows()
    cols = list(c.workbook.period_cols)
    first = cols[0]
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col)  # noqa: E731
    B = lambda name, x: f"{x.col}{r[f'_{TITLE[:18]}_{name}']}"  # noqa: E731
    k = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
    kr = lambda port: r[ctx.key(port)]  # noqa: E731
    cum = lambda rr, x: f"SUM(${first}{rr}:{x.col}{rr})"  # noqa: E731
    sheet, ref = src["capital_additions"].split("!", 1)
    adds_row = ref.removeprefix("{col}")
    absum = lambda parts: "=" + "+".join(f"ABS({p})" for p in parts)  # noqa: E731
    zero = [0.0] * ctx.n

    def prior(port, opening, x):
        return src[opening] if x.i == 1 else f"{cols[x.i - 2]}{kr(port)}"

    c.section("Checks")
    c.row("chk_gross", "  Check - gross cost re-derived (USD)",
          lambda x: f"={k('fa_gross_closing', x)}-({src['opening_gross']}"
                    f"+SUM({sheet}!${first}{adds_row}:{x.col}{adds_row}))", values=zero)  # fmt: skip
    c.row("chk_accum", "  Check - accumulated depreciation re-derived (USD)",
          lambda x: f"={k('fa_accum_depreciation_closing', x)}-({src['opening_accum_depreciation']}"
                    f"+{cum(kr('depreciation'), x)})", values=zero)  # fmt: skip
    c.row("chk_nbv", "  Check - NBV is never negative and equals cost less depreciation (USD)",
          lambda x: f"=ABS({k('fa_nbv_closing', x)}-({k('fa_gross_closing', x)}"
                    f"-{k('fa_accum_depreciation_closing', x)}))+MAX(-{k('fa_nbv_closing', x)},0)",
          values=zero)  # fmt: skip
    c.row("chk_rows", "  Check - each row re-derived from its inputs (USD)",
          lambda x: absum([
              B("adds", x) + "-" + S("capital_additions", x),
              B("life", x) + "-" + src["useful_life"],
              B("use", x) + "-" + S("use_fraction", x),
              B("gross_open", x) + "-" + prior("fa_gross_closing", "opening_gross", x),
              B("accum_open", x) + "-" + prior("fa_accum_depreciation_closing",
                                               "opening_accum_depreciation", x),
              B("raw", x) + f"-{k('fa_gross_closing', x)}/{B('life', x)}",
              B("nbv_pre", x) + f"-({k('fa_gross_closing', x)}-{B('accum_open', x)})",
              B("capped", x) + f"-MIN({B('raw', x)},{B('nbv_pre', x)})",
              k("depreciation", x) + f"-{B('use', x)}*{B('capped', x)}",
              B("gross2", x) + "-" + k("fa_gross_closing", x),
              k("fa_gross_closing", x) + f"-({B('gross_open', x)}+{B('adds', x)})",
              k("fa_accum_depreciation_closing", x)
              + f"-({B('accum_open', x)}+{k('depreciation', x)})",
          ]), values=zero)  # fmt: skip
    return {
        "gross": "Check - gross cost re-derived",
        "accum": "Check - accumulated depreciation re-derived",
        "nbv": "Check - NBV is never negative",
        "rows": "Check - each row re-derived from its inputs",
    }


FIXED_ASSETS = Module(
    name="fixed_assets",
    version="0.1.0",
    scope={
        "in": [
            "Gross cost roll-forward with additions and a brought-forward balance",
            "Straight-line book depreciation on cumulative gross cost over a useful life",
            "A share-of-period-in-use input, so cost waits before depreciating",
            "Net book value floored at nil",
        ],
        "out": [
            "Disposals, impairment and revaluation",
            "Per-asset lives: a cost layer keeps depreciating until NBV is nil, not until its "
            "own life ends. Exact while no layer reaches the end of its life",
            "Tax allowances (see the tax pool modules)",
            "Several asset classes in one module: use one instance per class",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "capital_additions": [1000.0, 0.0, 500.0, 0.0],
        "use_fraction": [0.5, 1.0, 1.0, 1.0],
        "useful_life": 4.0,
        "opening_gross": 200.0,
        "opening_accum_depreciation": 50.0,
    },
    golden=Golden(
        inputs={
            "capital_additions": [2000.0, 300.0, 0.0, 800.0],
            "use_fraction": [0.0, 0.5, 1.0, 1.0],
            "useful_life": 5.0,
            "opening_gross": 0.0,
            "opening_accum_depreciation": 0.0,
        },
        outputs={
            "depreciation": [0.0, 230.0, 460.0, 620.0],
            "fa_gross_closing": [2000.0, 2300.0, 2300.0, 3100.0],
            "fa_accum_depreciation_closing": [0.0, 230.0, 690.0, 1310.0],
            "fa_nbv_closing": [2000.0, 2070.0, 1610.0, 1790.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/fixed_assets.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = FIXED_ASSETS
