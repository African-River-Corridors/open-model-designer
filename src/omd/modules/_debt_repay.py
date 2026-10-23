"""Shared body of the senior debt repayment modules.

Interest is charged on the opening balance and paid each period. Principal is repaid in the periods
where the repayment flag is 1, never more than the balance:

- linear:  opening debt / number of repayment periods
- annuity: the level payment that clears the opening debt over the repayment periods, less interest
- sculpted: CFADS / target DSCR less interest, so debt service tracks the cash available

Public modules: `debt_repay_linear`, `debt_repay_annuity`, `debt_repay_sculpted`. Interest on the
opening balance keeps every method free of circularity. Rates must be above zero for the annuity.
"""

from __future__ import annotations

import re

from ..module import BuildContext, Golden, Module, Port

LIN, ANN, SCU = "linear", "annuity", "sculpted"
COMMON_IN = (
    Port("repayment_flag", "count", "series"),
    Port("interest_rate", "ratio", "scalar"),
    Port("opening_debt", "USD", "scalar"),
)
EXTRA_IN = {
    LIN: (),
    ANN: (Port("repayment_periods", "count", "scalar"),),
    SCU: (Port("cfads", "USD", "series"), Port("target_dscr", "ratio", "scalar")),
}
OUTPUTS = (
    Port("interest", "USD", "series"),
    Port("debt_repayment", "USD", "series"),
    Port("debt_service", "USD", "series"),
    Port("debt_closing", "USD", "series"),
)
KEYED = {
    "interest": "interest",
    "repay": "debt_repayment",
    "service": "debt_service",
    "close": "debt_closing",
}


def make_oracle(method):
    def oracle(inputs: dict) -> dict[str, list[float]]:
        r, bal0 = float(inputs["interest_rate"]), float(inputs["opening_debt"])
        out = {p.name: [] for p in OUTPUTS}
        bal = bal0
        for i, flag in enumerate(inputs["repayment_flag"]):
            interest = r * bal
            if method == LIN:
                raw = bal0 / sum(float(f) for f in inputs["repayment_flag"])
            elif method == ANN:
                n = float(inputs["repayment_periods"])
                raw = bal0 * r / (1 - (1 + r) ** (0 - n)) - interest
            else:
                raw = max(float(inputs["cfads"][i]) / float(inputs["target_dscr"]) - interest, 0.0)
            repay = float(flag) * min(raw, bal)
            bal -= repay
            for k, v in (("interest", interest), ("debt_repayment", repay),
                         ("debt_service", interest + repay), ("debt_closing", bal)):  # fmt: skip
                out[k].append(v)
        return out

    return oracle


def _plan(method):
    """Rows in order: (kind, name, label, spec). kind: lp (prior closing), link, calc, relink."""
    head = [
        ("lp", "open", "Debt, opening (USD)", None),
        ("link", "rate", "Interest rate per period (ratio)", "interest_rate"),
        ("calc", "interest", "Interest (USD)", "{rate}*{open}"),
    ]
    mid = {
        LIN: [
            ("link", "total", "Debt to repay (USD)", "opening_debt"),
            ("link", "n", "Repayment periods, the flagged periods (count)", "@debt_repay.count"),
            ("calc", "raw", "Straight-line principal (USD)", "{total}/{n}"),
        ],
        ANN: [
            ("link", "total", "Debt to repay (USD)", "opening_debt"),
            ("link", "r2", "Interest rate per period (ratio)", "interest_rate"),
            ("link", "n", "Repayment periods (count)", "repayment_periods"),
            ("calc", "g", "Discount factor (ratio)", "(1+{r2})^(0-{n})"),
            ("calc", "pmt", "Level payment (USD)", "{total}*{r2}/(1-{g})"),
            ("relink", "int_b", "Interest (USD)", "interest"),
            ("calc", "raw", "Annuity principal (USD)", "{pmt}-{int_b}"),
        ],
        SCU: [
            ("link", "cfads", "CFADS (USD)", "cfads"),
            ("link", "dscr", "Target DSCR (ratio)", "target_dscr"),
            ("calc", "cap", "Debt service capacity (USD)", "{cfads}/{dscr}"),
            ("relink", "int_b", "Interest (USD)", "interest"),
            ("calc", "raw", "Sculpted principal (USD)", "MAX({cap}-{int_b},0)"),
        ],
    }[method]
    tail = [
        ("lp", "open2", "Debt, opening (USD)", None),
        ("calc", "capped", "Principal within the balance (USD)", "MIN({raw},{open2})"),
        ("link", "flag", "Repayment period (flag)", "repayment_flag"),
        ("calc", "repay", "Principal repaid (USD)", "{flag}*{capped}"),
        ("lp", "open3", "Debt, opening (USD)", None),
        ("calc", "close", "Debt, closing (USD)", "{open3}-{repay}"),
        ("relink", "int_c", "Interest (USD)", "interest"),
        ("calc", "service", "Debt service (USD)", "{int_c}+{repay}"),
    ]
    return head + mid + tail


def _values(method, inputs):
    """Python values for every row, so each row carries what verify asserts it against."""
    r, bal0 = float(inputs["interest_rate"]), float(inputs["opening_debt"])
    n_p = len(inputs["repayment_flag"])
    V = {k: [] for k in ("open", "open2", "open3", "rate", "r2", "interest", "int_b", "int_c", "total", "n", "g",
                         "pmt", "raw", "cfads", "dscr", "cap", "capped", "flag", "repay", "close", "service")}  # fmt: skip
    bal = bal0
    for i in range(n_p):
        flag = float(inputs["repayment_flag"][i])
        interest = r * bal
        row = {"open": bal, "open2": bal, "open3": bal, "rate": r, "r2": r, "interest": interest,
               "int_b": interest, "int_c": interest, "total": bal0, "flag": flag}  # fmt: skip
        if method == LIN:
            n = sum(float(f) for f in inputs["repayment_flag"])
            row["n"] = n
        elif method == ANN:
            n = float(inputs["repayment_periods"])
            row["n"] = n
        if method == LIN:
            row["raw"] = bal0 / n
        elif method == ANN:
            row["g"] = (1 + r) ** (0 - n)
            row["pmt"] = bal0 * r / (1 - row["g"])
            row["raw"] = row["pmt"] - interest
        else:
            row["cfads"], row["dscr"] = float(inputs["cfads"][i]), float(inputs["target_dscr"])
            row["cap"] = row["cfads"] / row["dscr"]
            row["raw"] = max(row["cap"] - interest, 0.0)
        row["capped"] = min(row["raw"], bal)
        row["repay"] = flag * row["capped"]
        bal -= row["repay"]
        row["close"], row["service"] = bal, interest + row["repay"]
        for k, v in row.items():
            V[k].append(v)
    return V


def make_build(method):
    plan = _plan(method)
    close_pos = next(i for i, p in enumerate(plan) if p[1] == "close")
    bykey = {
        "interest": "interest",
        "repay": "debt_repayment",
        "service": "debt_service",
        "close": "debt_closing",
    }

    def build(ctx: BuildContext) -> None:
        V = _values(method, ctx.inputs)
        c = ctx.calcs
        if (
            method == LIN
        ):  # the number of repayment periods is derived from the flags, so they cannot disagree
            fr = ctx.source("repayment_flag")
            sheet, ref = fr.split("!", 1)
            frow = ref.removeprefix("{col}")
            cols = list(c.workbook.period_cols)
            c.skip_rows()
            c.section("Repayment periods")
            c.row("debt_repay.count", "  Repayment periods, the flagged periods (count)",
                  lambda x: f"=SUM({sheet}!{cols[0]}{frow}:{cols[-1]}{frow})", values=V["n"])  # fmt: skip
        b = ctx.block("Senior debt repayment" + f" ({method})")
        first = c.next_row
        close_row = first + close_pos
        for kind, name, label, spec in plan:
            if kind == "lp":
                b.link_prev(name, close_row, label, values=V[name])
            elif kind == "link" and spec.startswith("@"):
                b.link(name, spec[1:], label, values=V[name])
            elif kind == "link":
                b.link(name, ctx.source(spec), label, values=ctx.values(spec))
            elif kind == "relink":
                b.relink(name, spec, label)
            else:
                key = ctx.key(bykey[name]) if name in bykey else None
                b.calc(name, label, spec, key=key, values=V[name])
        assert c.rows()[ctx.key("debt_closing")] == close_row
        c.ws[f"{c.workbook.open_col}{close_row}"] = f"={ctx.source('opening_debt')}"
        if method == SCU:  # the unrepaid balance at maturity, visible and checked
            last_row = c.rows()["last_period_flag"]
            c.skip_rows()
            c.section("Balance at maturity")
            c.row("debt_repay.maturity", "  Debt balance at maturity (USD)",
                  lambda x: f"={x.col}{close_row}*{x.col}{last_row}", values=[0.0] * (ctx.n - 1) + [V["close"][-1]])  # fmt: skip

    return build


def make_checks(method):
    plan = _plan(method)
    title = "Senior debt repayment" + f" ({method})"

    def checks(ctx: BuildContext) -> dict[str, str]:
        c = ctx.calcs
        r = c.rows()
        cols = list(c.workbook.period_cols)
        first = cols[0]
        ports = {p.name: ctx.source(p.name) for p in ctx.module.inputs}
        S = lambda port, x: ports[port].format(col=x.col) if "{col}" in ports[port] else ports[port]  # noqa: E731
        K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731

        def B(name, x):  # keyed rows live under their output key
            if name in KEYED:
                return K(KEYED[name], x)
            return f"{x.col}{r[f'_{title[:18]}_{name}']}"

        rrow = r[ctx.key("debt_repayment")]
        fsheet, fref = ports["repayment_flag"].split("!", 1)
        frow = fref.removeprefix("{col}")
        flagsum = f"SUM({fsheet}!{cols[0]}{frow}:{cols[-1]}{frow})"
        absum = lambda parts: "=" + "+".join(f"ABS({p})" for p in parts)  # noqa: E731
        zero = [0.0] * ctx.n

        def bal(x):  # balance at the start of the period, from cumulative repayments
            if x.i == 1:
                return ports["opening_debt"]
            return f"({ports['opening_debt']}-SUM(${first}{rrow}:{cols[x.i - 2]}{rrow}))"

        def raw(x):
            if method == LIN:
                return f"{ports['opening_debt']}/{flagsum}"
            if method == ANN:
                rt, n = ports["interest_rate"], ports["repayment_periods"]
                return f"{ports['opening_debt']}*{rt}/(1-(1+{rt})^(0-{n}))-{K('interest', x)}"
            return f"MAX({S('cfads', x)}/{ports['target_dscr']}-{K('interest', x)},0)"

        def row_identity(x):
            parts = []
            for kind, name, _label, spec in plan:
                if kind == "lp":
                    parts.append(f"{B(name, x)}-{bal(x)}")
                elif kind == "link" and spec.startswith("@"):
                    parts.append(f"{B(name, x)}-{x.col}{r[spec[1:]]}")
                elif kind == "link":
                    parts.append(f"{B(name, x)}-{S(spec, x)}")
                elif kind == "relink":
                    parts.append(f"{B(name, x)}-{K(spec, x)}")
                else:
                    ex = re.sub(r"\{(\w+)\}", lambda m: B(m.group(1), x), spec)
                    cell = K(KEYED[name], x) if name in KEYED else B(name, x)
                    parts.append(f"{cell}-({ex})")
            return absum(parts)

        c.section("Checks")
        c.row("chk_interest", "  Check - interest on the opening balance re-derived (USD)",
              lambda x: f"={K('interest', x)}-{ports['interest_rate']}*{bal(x)}", values=zero)  # fmt: skip
        c.row("chk_repay", "  Check - principal re-derived from the ports (USD)",
              lambda x: f"={K('debt_repayment', x)}-{S('repayment_flag', x)}*MIN({raw(x)},{bal(x)})",
              values=zero)  # fmt: skip
        c.row("chk_close", "  Check - closing debt and service re-derived (USD)",
              lambda x: f"=ABS({K('debt_closing', x)}-({bal(x)}-{K('debt_repayment', x)}))"
                        f"+ABS({K('debt_service', x)}-({K('interest', x)}+{K('debt_repayment', x)}))"
                        f"+MAX(-{K('debt_closing', x)},0)", values=zero)  # fmt: skip
        c.row(
            "chk_rows",
            "  Check - every row re-derived from its inputs (USD)",
            row_identity,
            values=zero,
        )
        extra = {}
        if method == LIN:
            c.row("chk_count", "  Check - repayment periods equal the flagged periods (count)",
                  lambda x: f"=ABS({x.col}{r['debt_repay.count']}-{flagsum})", values=zero)  # fmt: skip
            extra["count"] = "Check - repayment periods equal the flagged periods"
        if method == SCU:
            mrow, last = r["debt_repay.maturity"], cols[-1]
            c.row("chk_maturity", "  Check - debt is repaid by maturity (USD)",
                  lambda x: f"=ABS({x.col}{mrow})+ABS({x.col}{mrow}-"
                            + (f"{K('debt_closing', x)})" if x.col == last else "0)"), values=zero)  # fmt: skip
            extra["maturity"] = "Check - debt is repaid by maturity"
        return {
            **extra,
            "interest": "Check - interest on the opening balance re-derived",
            "repay": "Check - principal re-derived from the ports",
            "close": "Check - closing debt and service re-derived",
            "rows": "Check - every row re-derived from its inputs",
        }

    return checks


def make_module(*, method, name, scope, example, golden) -> Module:
    oracle = make_oracle(method)
    return Module(
        name=name, version="0.1.0", scope=scope, inputs=COMMON_IN + EXTRA_IN[method], outputs=OUTPUTS,
        oracle=oracle, build=make_build(method), checks=make_checks(method), example=example, golden=golden,
    )  # fmt: skip


def pending(inputs, request):
    return Golden(inputs=inputs, outputs={}, kind="hand-calculation",
                  source=f"PENDING: independent hand calculation by a reviewer agent that did not see the code; see docs/golden-cases/{request}.md")  # fmt: skip


SCOPE_OUT = [
    "Fees, IDC and draw-to-need (see the draw modules)",
    "Floating rates, hedging and rate changes over time",
    "Balloon or bullet repayments and cash sweeps (see the sweep module)",
    "Several facilities in one module: use one instance per facility",
]
