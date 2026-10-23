"""Shared body of the tax depreciation pool modules.

One pool of qualifying cost. Each period: pool before allowance = opening WDV + additions; the
allowance is `use_fraction x rate x base`, never more than the pool; closing WDV = pool - allowance.

- reducing balance: base = pool before allowance.
- straight line:    base = cumulative cost (opening WDV + all additions to date).

`use_fraction` is the first-use rule: 0 before the pool's assets enter use (additions still join the
pool), 1 for a full period, between 0 and 1 for a part period. Rates come from the caller; this
module holds no jurisdiction. Public modules are `tax_pool_rb` and `tax_pool_sl`.
"""

from __future__ import annotations

from ..module import BuildContext, Module, Port

RB, SL = "reducing_balance", "straight_line"

INPUTS = (
    Port("capital_additions", "USD", "series"),
    Port("use_fraction", "ratio", "series"),
    Port("allowance_rate", "ratio", "scalar"),
    Port("opening_wdv", "USD", "scalar"),
)
OUTPUTS = (
    Port("tax_allowance", "USD", "series"),
    Port("tax_wdv_close", "USD", "series"),
)


def make_oracle(method: str):
    def oracle(inputs: dict) -> dict[str, list[float]]:
        rate, wdv = float(inputs["allowance_rate"]), float(inputs["opening_wdv"])
        cost = wdv
        allow, close = [], []
        for add, use in zip(inputs["capital_additions"], inputs["use_fraction"], strict=True):
            pool = wdv + float(add)
            cost += float(add)
            base = pool if method == RB else cost
            a = float(use) * rate * base if method == RB else min(float(use) * rate * base, pool)
            wdv = pool - a
            allow.append(a)
            close.append(wdv)
        return {"tax_allowance": allow, "tax_wdv_close": close}

    return oracle


def make_build(method: str, oracle):
    def build(ctx: BuildContext) -> None:
        want = oracle(ctx.inputs)
        opening = float(ctx.inputs["opening_wdv"])
        rate = float(ctx.inputs["allowance_rate"])
        adds = [float(x) for x in ctx.inputs["capital_additions"]]
        close_v, allow_v = want["tax_wdv_close"], want["tax_allowance"]
        wdv_open_v = [opening, *close_v[:-1]]
        pool_v = [o + a for o, a in zip(wdv_open_v, adds, strict=True)]
        c = ctx.calcs
        title = "Tax depreciation pool" + (" (straight line)" if method == SL else "")
        b = ctx.block(title)
        # Each calc sits within a few rows of its links (FAST 2.02-01), so ingredients are
        # linked again where they are used.
        link_adds = lambda name: b.link(  # noqa: E731
            name, ctx.source("capital_additions"), "Additions to the pool (USD)",
            values=ctx.values("capital_additions"))  # fmt: skip
        link_rate = lambda name: b.link(  # noqa: E731
            name, ctx.source("allowance_rate"), "Allowance rate (ratio)",
            values=ctx.values("allowance_rate"))  # fmt: skip
        link_use = lambda name: b.link(  # noqa: E731
            name, ctx.source("use_fraction"), "Share of period in use (ratio)",
            values=ctx.values("use_fraction"))  # fmt: skip
        if method == RB:
            link_adds("adds")
            first = c.next_row  # the wdv_open row; the closing row is predicted and asserted below
            close_row = first + 7
            b.link_prev("wdv_open", close_row, "Pool WDV, opening (USD)", values=wdv_open_v)
            b.calc("pool", "Pool before allowance (USD)", "{wdv_open}+{adds}", values=pool_v)
            link_rate("rate")
            raw_v = [rate * p for p in pool_v]
            b.calc("alw_raw", "Allowance before first-use rule (USD)", "{rate}*{pool}",
                   values=raw_v)  # fmt: skip
        else:
            cost_open_v, cost_v, k = [], [], opening
            for a in adds:
                cost_open_v.append(k)
                k += a
                cost_v.append(k)
            first = c.next_row  # the cost_open row
            cost_row, close_row = first + 2, first + 12
            b.link_prev("cost_open", cost_row, "Cumulative cost, opening (USD)",
                        values=cost_open_v)  # fmt: skip
            link_adds("adds")
            b.calc("cost", "Cumulative cost (USD)", "{cost_open}+{adds}", values=cost_v)
            link_rate("rate")
            raw_v = [rate * x for x in cost_v]
            b.calc("alw_raw", "Allowance before first-use rule (USD)", "{rate}*{cost}",
                   values=raw_v)  # fmt: skip
            b.link_prev("wdv_open", close_row, "Pool WDV, opening (USD)", values=wdv_open_v)
            link_adds("adds_b")
            b.calc("pool", "Pool before allowance (USD)", "{wdv_open}+{adds_b}", values=pool_v)
            b.calc("capped", "Allowance capped at the pool (USD)", "MIN({alw_raw},{pool})",
                   values=[min(r, p) for r, p in zip(raw_v, pool_v, strict=True)])  # fmt: skip
        link_use("use")
        src = "alw_raw" if method == RB else "capped"
        b.calc("allow", "Tax allowance (USD)", "{use}*{" + src + "}",
               key=ctx.key("tax_allowance"), values=allow_v)  # fmt: skip
        b.relink("pool_c", "pool", "Pool before allowance (USD)")
        b.calc("close", "Pool WDV, closing (USD)", "{pool_c}-{allow}",
               key=ctx.key("tax_wdv_close"), values=close_v)  # fmt: skip
        assert c.rows()[ctx.key("tax_wdv_close")] == close_row, "predicted closing row moved"
        # the Open cell of each corkscrew is the brought-forward input
        oc = c.workbook.open_col
        c.ws[f"{oc}{close_row}"] = f"={ctx.source('opening_wdv')}"
        if method == SL:
            c.ws[f"{oc}{cost_row}"] = f"={ctx.source('opening_wdv')}"

    return build


def make_checks(method: str):
    def checks(ctx: BuildContext) -> dict[str, str]:
        """Each check re-derives from the raw ports by cumulative sums, a different route."""
        c = ctx.calcs
        rows = c.rows()
        allow, close = rows[ctx.key("tax_allowance")], rows[ctx.key("tax_wdv_close")]
        add_src, use_src = ctx.source("capital_additions"), ctx.source("use_fraction")
        rate, opening = ctx.source("allowance_rate"), ctx.source("opening_wdv")
        cols = c.workbook.period_cols
        first = cols[0]

        def cum_adds(col):
            sheet, ref = add_src.split("!", 1)
            row = ref.removeprefix("{col}")
            return f"SUM({sheet}!${first}{row}:{col}{row})"

        def cum_allow(col):
            return f"SUM(${first}{allow}:{col}{allow})"

        def pool(x):  # cost left in the pool before this period's allowance
            prior = "0" if x.i == 1 else cum_allow(cols[x.i - 2])
            return f"({opening}+{cum_adds(x.col)}-{prior})"

        def base(x):
            return pool(x) if method == RB else f"({opening}+{cum_adds(x.col)})"

        c.section("Checks")
        c.row("chk_roll", "  Check - closing WDV re-derived (USD)",
              lambda x: f"={x.col}{close}-({opening}+{cum_adds(x.col)}-{cum_allow(x.col)})",
              values=[0.0] * ctx.n)  # fmt: skip
        c.row("chk_allow", "  Check - allowance re-derived (USD)",
              lambda x: f"={x.col}{allow}-{use_src.format(col=x.col)}"
                        f"*MIN({rate}*{base(x)},{pool(x)})",
              values=[0.0] * ctx.n)  # fmt: skip
        return {"roll": "Check - closing WDV re-derived", "allow": "Check - allowance re-derived"}

    return checks


def make_module(*, method, name, scope, example, golden, notes="") -> Module:
    oracle = make_oracle(method)
    return Module(
        name=name,
        version="0.1.0",
        scope=scope,
        inputs=INPUTS,
        outputs=OUTPUTS,
        oracle=oracle,
        build=make_build(method, oracle),
        checks=make_checks(method),
        example=example,
        golden=golden,
        notes=notes,
    )
