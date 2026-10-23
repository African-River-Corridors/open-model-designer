"""Corporate tax engine, generic.

    taxable before losses = profit before tax + adjustments
    taxable profit        = max(taxable before losses - losses relieved, 0)
    normal charge         = rate x taxable profit
    charge                = max(normal charge, minimum tax)         <- the floor hook
    paid                  = liability brought forward + instalment share x charge
    liability carried     = brought forward + charge - paid

`minimum_tax` is the floor hook: a series port that a jurisdiction module fills (a share of
revenue, a streak rule, zero where there is none). This module holds no jurisdiction. Losses
relieved come from the losses module; adjustments are signed (add-backs positive).
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port

INPUTS = (
    Port("profit_before_tax", "USD", "series"),
    Port("tax_adjustments", "USD", "series"),
    Port("losses_relieved", "USD", "series"),
    Port("minimum_tax", "USD", "series"),
    Port("tax_rate", "ratio", "scalar"),
    Port("instalment_share", "ratio", "scalar"),
    Port("opening_tax_payable", "USD", "scalar"),
)
OUTPUTS = (
    Port("taxable_profit", "USD", "series"),
    Port("tax_charge", "USD", "series"),
    Port("tax_paid", "USD", "series"),
    Port("tax_payable_closing", "USD", "series"),
)


def oracle(inputs: dict) -> dict[str, list[float]]:
    rate, share = float(inputs["tax_rate"]), float(inputs["instalment_share"])
    payable = float(inputs["opening_tax_payable"])
    taxable, charge, paid, closing = [], [], [], []
    for pbt, adj, loss, floor in zip(
        inputs["profit_before_tax"],
        inputs["tax_adjustments"],
        inputs["losses_relieved"],
        inputs["minimum_tax"],
        strict=True,
    ):
        t = max(float(pbt) + float(adj) - float(loss), 0.0)
        c = max(rate * t, float(floor))
        p = payable + share * c
        payable = payable + c - p
        taxable.append(t)
        charge.append(c)
        paid.append(p)
        closing.append(payable)
    return {
        "taxable_profit": taxable,
        "tax_charge": charge,
        "tax_paid": paid,
        "tax_payable_closing": closing,
    }


def build(ctx: BuildContext) -> None:
    want = oracle(ctx.inputs)
    c = ctx.calcs
    opening = float(ctx.inputs["opening_tax_payable"])
    close_v = want["tax_payable_closing"]
    open_v = [opening, *close_v[:-1]]
    pbt, adj = ctx.values("profit_before_tax"), ctx.values("tax_adjustments")
    rate = float(ctx.inputs["tax_rate"])
    pre = [a + b for a, b in zip(pbt, adj, strict=True)]
    normal = [rate * t for t in want["taxable_profit"]]
    b = ctx.block("Corporate tax")
    L = lambda name, port, label: b.link(  # noqa: E731
        name, ctx.source(port), label, values=ctx.values(port)
    )
    L("pbt", "profit_before_tax", "Profit before tax (USD)")
    L("adj", "tax_adjustments", "Tax adjustments, add-backs positive (USD)")
    b.calc("pre", "Taxable profit before losses (USD)", "{pbt}+{adj}", values=pre)
    L("loss", "losses_relieved", "Losses relieved (USD)")
    b.calc("taxable", "Taxable profit (USD)", "MAX({pre}-{loss},0)",
           key=ctx.key("taxable_profit"), values=want["taxable_profit"])  # fmt: skip
    L("rate", "tax_rate", "Tax rate (ratio)")
    b.calc("normal", "Charge at the tax rate (USD)", "{rate}*{taxable}", values=normal)
    L("floor", "minimum_tax", "Minimum tax - the floor hook (USD)")
    b.calc("charge", "Tax charge (USD)", "MAX({normal},{floor})",
           key=ctx.key("tax_charge"), values=want["tax_charge"])  # fmt: skip
    L("share", "instalment_share", "Share of the charge paid in the period (ratio)")
    first = c.next_row
    close_row = first + 2
    b.link_prev("payable_open", close_row, "Tax payable, opening (USD)", values=open_v)
    b.calc("paid", "Tax paid (USD)", "{payable_open}+{share}*{charge}",
           key=ctx.key("tax_paid"), values=want["tax_paid"])  # fmt: skip
    b.calc("close", "Tax payable, closing (USD)", "{payable_open}+{charge}-{paid}",
           key=ctx.key("tax_payable_closing"), values=close_v)  # fmt: skip
    assert c.rows()[ctx.key("tax_payable_closing")] == close_row
    c.ws[f"{c.workbook.open_col}{close_row}"] = f"={ctx.source('opening_tax_payable')}"


def checks(ctx: BuildContext) -> dict[str, str]:
    """Each check re-derives rows from the raw ports (or the row's own inputs) and reads 0."""
    c = ctx.calcs
    r = c.rows()
    key = ctx.key
    cols = list(c.workbook.period_cols)
    first = cols[0]
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col)  # noqa: E731
    local = {  # block rows by registry key (links have no key): found by their sheet position
        n: r[key(n)] for n in ("taxable_profit", "tax_charge", "tax_paid", "tax_payable_closing")
    }
    cum = lambda rr, x: f"SUM(${first}{rr}:{x.col}{rr})"  # noqa: E731
    zero = [0.0] * ctx.n
    opening = src["opening_tax_payable"]
    t, ch, pd, cl = (local[k] for k in ("taxable_profit", "tax_charge", "tax_paid",
                                         "tax_payable_closing"))  # fmt: skip

    def payable_open(x):  # liability at the start of the period, from cumulative sums
        if x.i == 1:
            return opening
        prev = cols[x.i - 2]
        return f"({opening}+SUM(${first}{ch}:{prev}{ch})-SUM(${first}{pd}:{prev}{pd}))"

    blk = lambda name: r[f"_Corporate tax_{name}"]  # noqa: E731 - rows without an output key
    link_of = {
        "pbt": "profit_before_tax", "adj": "tax_adjustments", "loss": "losses_relieved",
        "floor": "minimum_tax",
    }  # fmt: skip
    scalar_of = {"rate": "tax_rate", "share": "instalment_share"}

    def links(x):
        parts = [f"{x.col}{blk(n)}-{S(p, x)}" for n, p in link_of.items()]
        parts += [f"{x.col}{blk(n)}-{src[p]}" for n, p in scalar_of.items()]
        return "=" + "+".join(f"ABS({p})" for p in parts)

    c.section("Checks")
    c.row("chk_links", "  Check - linked inputs equal their ports (USD)", links, values=zero)
    c.row("chk_stages", "  Check - intermediate rows re-derived (USD)",
          lambda x: f"=ABS({x.col}{blk('pre')}-({S('profit_before_tax', x)}"
                    f"+{S('tax_adjustments', x)}))+ABS({x.col}{blk('normal')}"
                    f"-{src['tax_rate']}*{x.col}{t})", values=zero)  # fmt: skip
    c.row("chk_taxable", "  Check - taxable profit re-derived (USD)",
          lambda x: f"={x.col}{t}-MAX({S('profit_before_tax', x)}+{S('tax_adjustments', x)}"
                    f"-{S('losses_relieved', x)},0)", values=zero)  # fmt: skip
    c.row("chk_charge", "  Check - charge re-derived (USD)",
          lambda x: f"={x.col}{ch}-MAX({src['tax_rate']}*MAX({S('profit_before_tax', x)}"
                    f"+{S('tax_adjustments', x)}-{S('losses_relieved', x)},0),"
                    f"{S('minimum_tax', x)})", values=zero)  # fmt: skip
    c.row("chk_paid", "  Check - tax paid re-derived (USD)",
          lambda x: f"={x.col}{pd}-({payable_open(x)}+{src['instalment_share']}*{x.col}{ch})",
          values=zero)  # fmt: skip
    c.row("chk_close", "  Check - tax payable re-derived (USD)",
          lambda x: f"={x.col}{cl}-({opening}+{cum(ch, x)}-{cum(pd, x)})", values=zero)  # fmt: skip
    return {
        "links": "Check - linked inputs equal their ports",
        "stages": "Check - intermediate rows re-derived",
        "taxable": "Check - taxable profit re-derived",
        "charge": "Check - charge re-derived",
        "paid": "Check - tax paid re-derived",
        "close": "Check - tax payable re-derived",
    }


TAX_ENGINE = Module(
    name="tax_engine",
    version="0.1.0",
    scope={
        "in": [
            "Profit before tax, signed adjustments and losses relieved to taxable profit",
            "Charge at one rate, with a minimum-tax floor hook (a series a jurisdiction fills)",
            "Payment timing: an instalment share paid in the period, the rest next period, "
            "and a liability brought forward paid in the first period",
        ],
        "out": [
            "Any jurisdiction: rates, floors, levies and the floor's own rule are inputs",
            "Loss relief and capital allowances (tax_losses, tax_pool_*), which feed this module",
            "Deferred tax, and interest or penalties on late payment",
            "A rate that changes over time (supply the charge in pieces, or add a rate series)",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "profit_before_tax": [500.0, 800.0, -200.0, 1200.0],
        "tax_adjustments": [50.0, 0.0, 30.0, -20.0],
        "losses_relieved": [0.0, 100.0, 0.0, 300.0],
        "minimum_tax": [20.0, 25.0, 30.0, 35.0],
        "tax_rate": 0.25,
        "instalment_share": 0.5,
        "opening_tax_payable": 40.0,
    },
    golden=Golden(
        inputs={
            "profit_before_tax": [1000.0, -300.0, 600.0, 900.0],
            "tax_adjustments": [100.0, 0.0, -50.0, 0.0],
            "losses_relieved": [0.0, 0.0, 200.0, 100.0],
            "minimum_tax": [10.0, 10.0, 10.0, 10.0],
            "tax_rate": 0.3,
            "instalment_share": 0.75,
            "opening_tax_payable": 0.0,
        },
        outputs={
            "taxable_profit": [1100.0, 0.0, 350.0, 800.0],
            "tax_charge": [330.0, 10.0, 105.0, 240.0],
            "tax_paid": [247.5, 90.0, 81.25, 206.25],
            "tax_payable_closing": [82.5, 2.5, 26.25, 60.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/tax_engine.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = TAX_ENGINE
