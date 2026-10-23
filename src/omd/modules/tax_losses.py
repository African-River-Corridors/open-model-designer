"""Tax losses, vintaged.

A loss made in a period joins a pool of its own year of origin. Each period, in this order:
1. a pool whose age is greater than `loss_life` periods expires, whole, before any relief (a
   loss is usable in the `loss_life` periods after the one it was made in);
2. profit before losses is relieved against the pools, oldest first;
3. a loss made this period joins a new pool (usable from the next period).

Brought-forward losses form the oldest pool, with age counted from period 0. The loss life is an
input; this module holds no jurisdiction.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port


def oracle(inputs: dict) -> dict[str, list[float]]:
    life = float(inputs["loss_life"])
    pools = {0: float(inputs["opening_losses"])}  # origin period -> balance
    used, expired, closing, after = [], [], [], []
    for t, p in enumerate(inputs["taxable_profit_pre_loss"], start=1):
        p = float(p)
        exp = 0.0
        for v in pools:
            if t - v > life:
                exp += pools[v]
                pools[v] = 0.0
        avail, use = max(p, 0.0), 0.0
        for v in sorted(pools):
            r = min(pools[v], avail)
            pools[v] -= r
            avail -= r
            use += r
        pools[t] = max(-p, 0.0)
        used.append(use)
        expired.append(exp)
        closing.append(sum(pools.values()))
        after.append(max(p, 0.0) - use)
    return {
        "tax_loss_used": used,
        "tax_loss_expired": expired,
        "tax_loss_closing": closing,
        "taxable_after_losses": after,
    }


def _layout(n: int) -> dict:
    """Row offsets inside the module's block, so rows can name rows written after them."""
    top = ["profit", "life", "gen", "pos"]
    off = {k: i for i, k in enumerate(top)}
    base = len(top)
    per = {0: ["age", "open", "exp", "avail", "use", "close"]}
    for v in range(1, n + 1):
        per[v] = ["age", "open", "add", "exp", "avail", "use", "close"]
    for v in range(0, n + 1):
        for k in per[v]:
            off[f"{k}{v}"] = base
            base += 1
    for k in ("t_used", "t_exp", "t_close", "after"):
        off[k] = base
        base += 1
    return off


def build(ctx: BuildContext) -> None:
    c = ctx.calcs
    n = ctx.n
    cols = list(c.workbook.period_cols)
    oc = c.workbook.open_col
    c.skip_rows()
    c.section("Tax losses by year of origin")
    start = c.next_row
    off = _layout(n)
    R = lambda k: start + off[k]  # noqa: E731
    prof_src, life_src = ctx.source("taxable_profit_pre_loss"), ctx.source("loss_life")
    open_src = ctx.source("opening_losses")
    prev = lambda x: oc if x.i == 1 else cols[x.i - 2]  # noqa: E731

    def row(k, label, f, **kw):
        assert c.next_row == R(k), (k, c.next_row, R(k))
        c.row(kw.pop("key", k), label, f, **kw)

    row("profit", "    Profit before losses (USD)", lambda x: "=" + prof_src.format(col=x.col))
    row("life", "    Loss life (periods)", lambda x: f"={life_src}")
    row("gen", "  Loss made in the period (USD)",
        lambda x: f"=MAX(-{x.col}{R('profit')},0)")  # fmt: skip
    row("pos", "  Profit available for relief (USD)",
        lambda x: f"=MAX({x.col}{R('profit')},0)")  # fmt: skip
    for v in range(0, n + 1):
        tag = "brought forward" if v == 0 else f"period {v}"
        row(f"age{v}", f"  Pool {tag}: age in periods (periods)",
            lambda x, v=v: f"={prev(x)}{R(f'age{v}')}+1", open_value=float(-v))  # fmt: skip
        row(f"open{v}", f"  Pool {tag}: opening (USD)",
            lambda x, v=v: f"={prev(x)}{R(f'close{v}')}")  # fmt: skip
        if v:
            row(f"add{v}", f"  Pool {tag}: loss added (USD)",
                lambda x, v=v: f"=({x.col}{R(f'age{v}')}=0)*{x.col}{R('gen')}")  # fmt: skip
        row(
            f"exp{v}",
            f"  Pool {tag}: expired (USD)",
            lambda x, v=v: f"=({x.col}{R(f'age{v}')}>{x.col}{R('life')})*{x.col}{R(f'open{v}')}",
        )
        row(f"avail{v}", f"  Pool {tag}: profit still available (USD)",
            lambda x, v=v: f"={x.col}{R('pos')}" if v == 0 else
            f"={x.col}{R(f'avail{v - 1}')}-{x.col}{R(f'use{v - 1}')}")  # fmt: skip
        row(
            f"use{v}",
            f"  Pool {tag}: relieved (USD)",
            lambda x, v=v: (
                f"=MIN({x.col}{R(f'open{v}')}-{x.col}{R(f'exp{v}')},{x.col}{R(f'avail{v}')})"
            ),
        )
        row(f"close{v}", f"  Pool {tag}: closing (USD)",
            lambda x, v=v: f"={x.col}{R(f'open{v}')}"
            + (f"+{x.col}{R(f'add{v}')}" if v else "")
            + f"-{x.col}{R(f'exp{v}')}-{x.col}{R(f'use{v}')}",
            open_formula=f"={open_src}" if v == 0 else None)  # fmt: skip
    vs = range(0, n + 1)
    row("t_used", "  Losses relieved (USD)",
        lambda x: "=" + "+".join(f"{x.col}{R(f'use{v}')}" for v in vs),
        key=ctx.key("tax_loss_used"))  # fmt: skip
    row("t_exp", "  Losses expired (USD)",
        lambda x: "=" + "+".join(f"{x.col}{R(f'exp{v}')}" for v in vs),
        key=ctx.key("tax_loss_expired"))  # fmt: skip
    row("t_close", "  Losses carried forward (USD)",
        lambda x: "=" + "+".join(f"{x.col}{R(f'close{v}')}" for v in vs),
        key=ctx.key("tax_loss_closing"))  # fmt: skip
    row("after", "  Profit after losses (USD)",
        lambda x: f"={x.col}{R('pos')}-{x.col}{R('t_used')}",
        key=ctx.key("taxable_after_losses"))  # fmt: skip
    ctx.registry["tax_losses.start"] = start


def checks(ctx: BuildContext) -> dict[str, str]:
    """Each check re-derives rows from the raw ports or from their own inputs, and reads 0."""
    c = ctx.calcs
    n = ctx.n
    cols = list(c.workbook.period_cols)
    oc = c.workbook.open_col
    first = cols[0]
    start = ctx.registry["tax_losses.start"]
    off = _layout(n)
    R = lambda k: start + off[k]  # noqa: E731
    prof_src, life_src = ctx.source("taxable_profit_pre_loss"), ctx.source("loss_life")
    open_src = ctx.source("opening_losses")
    prev = lambda x: oc if x.i == 1 else cols[x.i - 2]  # noqa: E731
    vs = range(0, n + 1)
    S = lambda k, x: f"{x.col}{R(k)}"  # noqa: E731
    cum = lambda k, x: f"SUM(${first}{R(k)}:{x.col}{R(k)})"  # noqa: E731
    zero = [0.0] * n

    def absum(parts):
        return "+".join(f"ABS({p})" for p in parts)

    c.section("Checks")
    c.row("chk_recon", "  Check - carried forward re-derived (USD)",
          lambda x: f"={S('t_close', x)}-({open_src}+{cum('gen', x)}-{cum('t_used', x)}"
                    f"-{cum('t_exp', x)})", values=zero)  # fmt: skip
    c.row("chk_inputs", "  Check - links, loss made and profit re-derived (USD)",
          lambda x: f"={absum([S('profit', x) + '-' + prof_src.format(col=x.col),
                               S('life', x) + '-' + life_src,
                               S('gen', x) + f'-MAX(-{prof_src.format(col=x.col)},0)',
                               S('pos', x) + f'-MAX({prof_src.format(col=x.col)},0)'])}", values=zero)  # fmt: skip
    c.row("chk_pools", "  Check - pool arithmetic re-derived (USD)",
          lambda x: "=" + absum(
              [S(f"open{v}", x) + f"-{prev(x)}{R(f'close{v}')}" for v in vs]
              + [S(f"age{v}", x) + f"-({x.i}-{v})" for v in vs]
              + [S(f"add{v}", x) + (f"-{S('gen', x)}" if x.i == v else "")
                 for v in range(1, n + 1)]
              + [S(f"exp{v}", x) + f"-({x.i}-{v}>{life_src})*{S(f'open{v}', x)}" for v in vs]
              + [S(f"avail{v}", x) + (f"-{S('pos', x)}" if v == 0 else
                 f"-({S(f'avail{v - 1}', x)}-{S(f'use{v - 1}', x)})") for v in vs]
              + [S(f"use{v}", x)
                 + f"-MIN({S(f'open{v}', x)}-{S(f'exp{v}', x)},{S(f'avail{v}', x)})" for v in vs]
              + [S(f"close{v}", x) + f"-({S(f'open{v}', x)}"
                 + (f"+{S(f'add{v}', x)}" if v else "")
                 + f"-{S(f'exp{v}', x)}-{S(f'use{v}', x)})" for v in vs]),
          values=zero)  # fmt: skip
    c.row("chk_after", "  Check - profit after losses re-derived (USD)",
          lambda x: f"={S('after', x)}-(MAX({prof_src.format(col=x.col)},0)-{S('t_used', x)})",
          values=zero)  # fmt: skip
    return {
        "recon": "Check - carried forward re-derived",
        "inputs": "Check - links, loss made and profit re-derived",
        "pools": "Check - pool arithmetic re-derived",
        "after": "Check - profit after losses re-derived",
    }


TAX_LOSSES = Module(
    name="tax_losses",
    version="0.1.0",
    scope={
        "in": [
            "Loss pools by period of origin; a loss made in a period is usable from the next",
            "Expiry: a pool expires whole once its age is greater than the loss life (an input), so a loss is usable in the loss-life periods after it was made",
            "Relief against profit before losses, oldest pool first",
            "Brought-forward losses as the oldest pool, aged from period 0",
            "A reconciliation check: opening + made - relieved - expired = carried forward",
        ],
        "out": [
            "Any jurisdiction's loss period, restrictions or ring-fencing: inputs and "
            "jurisdiction modules supply those",
            "Caps on how much profit a loss may relieve in a period",
            "Change-of-ownership or other anti-avoidance limits",
            "Loss carry-back",
            "Sub-annual periods: age is counted in model periods",
        ],
    },
    fast_declared={
        "3.04-01 Check - pool arithmetic": "the independent re-derivation names the period and the pool's period of origin",
    },
    inputs=(
        Port("taxable_profit_pre_loss", "USD", "series"),
        Port("loss_life", "periods", "scalar"),
        Port("opening_losses", "USD", "scalar"),
    ),
    outputs=(
        Port("tax_loss_used", "USD", "series"),
        Port("tax_loss_expired", "USD", "series"),
        Port("tax_loss_closing", "USD", "series"),
        Port("taxable_after_losses", "USD", "series"),
    ),
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "taxable_profit_pre_loss": [-100.0, -50.0, 60.0, 200.0],
        "loss_life": 2.0,
        "opening_losses": 30.0,
    },
    golden=Golden(
        inputs={
            "taxable_profit_pre_loss": [-300.0, 100.0, -50.0, 400.0],
            "loss_life": 2.0,
            "opening_losses": 80.0,
        },
        outputs={
            "tax_loss_used": [0.0, 100.0, 0.0, 50.0],
            "tax_loss_expired": [0.0, 0.0, 0.0, 280.0],
            "tax_loss_closing": [380.0, 280.0, 330.0, 0.0],
            "taxable_after_losses": [0.0, 0.0, 0.0, 350.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); expiry "
        "when age > loss_life; working in docs/golden-cases/tax_losses.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = TAX_LOSSES
