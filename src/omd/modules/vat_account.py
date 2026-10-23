"""VAT account, generic.

Input VAT joins a receivable. Each period the receivable is offset against output VAT; what output
VAT is left is the net VAT due, paid with a lag (a share in the period, the rest next period).
In the last period the unrecovered receivable can be written off. No jurisdiction: rates, which
spend carries VAT and any cash refund rule are the caller's.

    available = receivable brought forward + input VAT
    offset    = min(available, output VAT)
    net due   = output VAT - offset
    written off = last-period flag x (available - offset)
    receivable carried = available - offset - written off
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port

INPUTS = (
    Port("vat_input", "USD", "series"),
    Port("vat_output", "USD", "series"),
    Port("opening_vat_receivable", "USD", "scalar"),
    Port("settle_share", "ratio", "scalar"),
    Port("write_off_at_end", "count", "scalar"),
)
OUTPUTS = (
    Port("vat_offset", "USD", "series"),
    Port("vat_net_due", "USD", "series"),
    Port("vat_paid", "USD", "series"),
    Port("vat_payable_closing", "USD", "series"),
    Port("vat_written_off", "USD", "series"),
    Port("vat_receivable_closing", "USD", "series"),
)
TITLE = "VAT account"


def oracle(inputs: dict) -> dict[str, list[float]]:
    share, wo_flag = float(inputs["settle_share"]), float(inputs["write_off_at_end"])
    recv, payable = float(inputs["opening_vat_receivable"]), 0.0
    out: dict[str, list[float]] = {p.name: [] for p in OUTPUTS}
    n = len(inputs["vat_input"])
    for i, (vin, vout) in enumerate(zip(inputs["vat_input"], inputs["vat_output"], strict=True)):
        avail = recv + float(vin)
        offset = min(avail, float(vout))
        net = float(vout) - offset
        resid = avail - offset
        wo = (wo_flag if i == n - 1 else 0.0) * resid
        recv = resid - wo
        paid = payable + share * net
        payable = payable + net - paid
        for k, v in zip(
            ("vat_offset", "vat_net_due", "vat_paid", "vat_payable_closing", "vat_written_off",
             "vat_receivable_closing"),
            (offset, net, paid, payable, wo, recv),
        ):  # fmt: skip
            out[k].append(v)
    return out


def _final_flag(ctx: BuildContext) -> None:
    """The timing flag in its own row (FAST 2.02-06): the write-off input, in the last period only."""
    c = ctx.calcs
    last_row = c.rows()["last_period_flag"]
    c.skip_rows()
    c.section("VAT timing flag")
    c.row("vat_account.final", "  Write-off applies in this period (flag)",
          lambda x: f"={ctx.source('write_off_at_end')}*{x.col}{last_row}",
          values=[0.0] * (ctx.n - 1) + [float(ctx.inputs["write_off_at_end"])])  # fmt: skip


def build(ctx: BuildContext) -> None:
    want = oracle(ctx.inputs)
    c, n = ctx.calcs, ctx.n
    _final_flag(ctx)
    flag_v = [0.0] * (n - 1) + [float(ctx.inputs["write_off_at_end"])]
    vin, vout = ctx.values("vat_input"), ctx.values("vat_output")
    recv_close, payable_close = want["vat_receivable_closing"], want["vat_payable_closing"]
    recv_open_v = [float(ctx.inputs["opening_vat_receivable"]), *recv_close[:-1]]
    pay_open_v = [0.0, *payable_close[:-1]]
    avail = [a + b for a, b in zip(recv_open_v, vin, strict=True)]
    resid = [a - o for a, o in zip(avail, want["vat_offset"], strict=True)]
    b = ctx.block(TITLE)
    b.link("vin", ctx.source("vat_input"), "Input VAT (USD)", values=vin)
    first = c.next_row
    recv_close_row = first + 8
    b.link_prev("recv_open", recv_close_row, "Receivable, opening (USD)", values=recv_open_v)
    b.link("vout", ctx.source("vat_output"), "Output VAT (USD)", values=vout)
    b.calc("avail", "Available to offset (USD)", "{recv_open}+{vin}", values=avail)
    b.calc("offset", "Offset against output VAT (USD)", "MIN({avail},{vout})",
           key=ctx.key("vat_offset"), values=want["vat_offset"])  # fmt: skip
    b.calc("net", "Net VAT due (USD)", "{vout}-{offset}",
           key=ctx.key("vat_net_due"), values=want["vat_net_due"])  # fmt: skip
    b.link("final", "vat_account.final", "Write-off applies (flag)", values=flag_v)
    b.calc("resid", "Receivable left after offset (USD)", "{avail}-{offset}", values=resid)
    b.calc("wo", "Written off (USD)", "{final}*{resid}",
           key=ctx.key("vat_written_off"), values=want["vat_written_off"])  # fmt: skip
    b.calc("recv_close", "Receivable, closing (USD)", "{resid}-{wo}",
           key=ctx.key("vat_receivable_closing"), values=recv_close)  # fmt: skip
    assert c.rows()[ctx.key("vat_receivable_closing")] == recv_close_row
    c.ws[f"{c.workbook.open_col}{recv_close_row}"] = f"={ctx.source('opening_vat_receivable')}"
    b.link("share", ctx.source("settle_share"), "Share of net VAT paid in the period (ratio)",
           values=ctx.values("settle_share"))  # fmt: skip
    first2 = c.next_row
    pay_close_row = first2 + 3
    b.link_prev("pay_open", pay_close_row, "VAT payable, opening (USD)", values=pay_open_v)
    b.relink("net2", "net", "Net VAT due (USD)")
    b.calc("paid", "VAT paid (USD)", "{pay_open}+{share}*{net2}",
           key=ctx.key("vat_paid"), values=want["vat_paid"])  # fmt: skip
    b.calc("pay_close", "VAT payable, closing (USD)", "{pay_open}+{net2}-{paid}",
           key=ctx.key("vat_payable_closing"), values=payable_close)  # fmt: skip
    assert c.rows()[ctx.key("vat_payable_closing")] == pay_close_row


def checks(ctx: BuildContext) -> dict[str, str]:
    """Each check re-derives rows from the raw ports or from the row's own inputs, and reads 0."""
    c = ctx.calcs
    r = c.rows()
    cols = list(c.workbook.period_cols)
    first = cols[0]
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col)  # noqa: E731
    blk = lambda name: r[f"_{TITLE[:18]}_{name}"]  # noqa: E731
    B = lambda name, x: f"{x.col}{blk(name)}"  # noqa: E731
    k = lambda port: r[ctx.key(port)]  # noqa: E731
    cum = lambda rr, x: f"SUM(${first}{rr}:{x.col}{rr})"  # noqa: E731
    absum = lambda parts: "=" + "+".join(f"ABS({p})" for p in parts)  # noqa: E731
    zero = [0.0] * ctx.n
    flag = r["vat_account.final"]
    last = cols[-1]

    def pay_open(x):
        if x.i == 1:
            return "0"
        prev = cols[x.i - 2]
        return f"(SUM(${first}{k('vat_net_due')}:{prev}{k('vat_net_due')})-SUM(${first}{k('vat_paid')}:{prev}{k('vat_paid')}))"

    c.section("Checks")
    c.row("chk_links", "  Check - linked inputs equal their ports (USD)",
          lambda x: absum([B("vin", x) + "-" + S("vat_input", x), B("vout", x) + "-" + S("vat_output", x),
                           B("share", x) + "-" + src["settle_share"],
                           f"{x.col}{flag}-" + (src["write_off_at_end"] if x.col == last else "0"),
                           B("final", x) + f"-{x.col}{flag}"]), values=zero)  # fmt: skip
    c.row("chk_recv", "  Check - receivable carried forward re-derived (USD)",
          lambda x: f"={x.col}{k('vat_receivable_closing')}-({src['opening_vat_receivable']}"
                    f"+{cum(blk('vin'), x)}-{cum(k('vat_offset'), x)}-{cum(k('vat_written_off'), x)})",
          values=zero)  # fmt: skip
    c.row("chk_pay", "  Check - VAT payable carried forward re-derived (USD)",
          lambda x: f"={x.col}{k('vat_payable_closing')}-({cum(k('vat_net_due'), x)}"
                    f"-{cum(k('vat_paid'), x)})", values=zero)  # fmt: skip
    c.row("chk_rows", "  Check - each row re-derived from its inputs (USD)",
          lambda x: absum([
              B("avail", x) + f"-({B('recv_open', x)}+{B('vin', x)})",
              f"{x.col}{k('vat_offset')}-MIN({B('avail', x)},{B('vout', x)})",
              f"{x.col}{k('vat_net_due')}-({B('vout', x)}-{x.col}{k('vat_offset')})",
              B("resid", x) + f"-({B('avail', x)}-{x.col}{k('vat_offset')})",
              f"{x.col}{k('vat_written_off')}-{B('final', x)}*{B('resid', x)}",
              f"{x.col}{k('vat_receivable_closing')}-({B('resid', x)}-{x.col}{k('vat_written_off')})",
              f"{x.col}{k('vat_paid')}-({pay_open(x)}+{B('share', x)}*{x.col}{k('vat_net_due')})",
              B("recv_open", x) + "-" + (src["opening_vat_receivable"] if x.i == 1
                                          else f"{cols[x.i - 2]}{k('vat_receivable_closing')}"),
              B("pay_open", x) + f"-{pay_open(x)}",
              B("net2", x) + f"-{x.col}{k('vat_net_due')}",
          ]), values=zero)  # fmt: skip
    return {
        "links": "Check - linked inputs equal their ports",
        "recv": "Check - receivable carried forward re-derived",
        "pay": "Check - VAT payable carried forward re-derived",
        "rows": "Check - each row re-derived from its inputs",
    }


VAT_ACCOUNT = Module(
    name="vat_account",
    version="0.1.0",
    scope={
        "in": [
            "An input VAT receivable, with a brought-forward balance, offset against output VAT",
            "Net VAT due, paid with a lag: a share in the period and the rest in the next",
            "Write-off of the unrecovered receivable in the last period, switched by an input",
        ],
        "out": [
            "Any jurisdiction: VAT rates, exempt or zero-rated supplies and levies on top",
            "Cash refunds of excess input VAT (the receivable simply carries forward)",
            "A recovery lag on input VAT (offset is immediate, in the period incurred)",
            "A VAT payable brought forward",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "vat_input": [100.0, 50.0, 0.0, 30.0],
        "vat_output": [0.0, 100.0, 300.0, 20.0],
        "opening_vat_receivable": 20.0,
        "settle_share": 0.5,
        "write_off_at_end": 1.0,
    },
    golden=Golden(
        inputs={
            "vat_input": [200.0, 0.0, 100.0, 50.0],
            "vat_output": [50.0, 150.0, 100.0, 90.0],
            "opening_vat_receivable": 30.0,
            "settle_share": 0.6,
            "write_off_at_end": 1.0,
        },
        outputs={
            "vat_offset": [50.0, 150.0, 100.0, 80.0],
            "vat_net_due": [0.0, 0.0, 0.0, 10.0],
            "vat_paid": [0.0, 0.0, 0.0, 6.0],
            "vat_payable_closing": [0.0, 0.0, 0.0, 4.0],
            "vat_written_off": [0.0, 0.0, 0.0, 0.0],
            "vat_receivable_closing": [180.0, 30.0, 30.0, 0.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/vat_account.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = VAT_ACCOUNT
