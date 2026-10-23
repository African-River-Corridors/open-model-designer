"""Shared body of the cash sweep modules.

Cash above what the project needs repays debt early. Three rules for how much:

- percent:         sweep = percent x cash available
- target cash:     sweep = cash available above a cash target
- target leverage: sweep = debt above (target leverage x EBITDA)

In every rule the sweep is switched by a flag, never more than the debt, and (leverage rule) never
more than the cash available. Public modules: `cash_sweep_percent`, `cash_sweep_target_cash`,
`cash_sweep_target_leverage`.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port
from ._plan_module import build_plan, plan_checks

PCT, TC, TL = "percent", "target_cash", "target_leverage"
COMMON = (
    Port("cash_available_for_sweep", "USD", "series"),
    Port("debt_before_sweep", "USD", "series"),
    Port("sweep_flag", "count", "series"),
)
EXTRA = {
    PCT: (Port("sweep_percent", "ratio", "scalar"),),
    TC: (Port("target_cash", "USD", "scalar"),),
    TL: (Port("ebitda", "USD", "series"), Port("target_leverage", "ratio", "scalar")),
}
OUTPUTS = (
    Port("sweep_amount", "USD", "series"),
    Port("debt_after_sweep", "USD", "series"),
    Port("cash_after_sweep", "USD", "series"),
)
KEYED = {
    "sweep": "sweep_amount",
    "debt_after": "debt_after_sweep",
    "cash_after": "cash_after_sweep",
}
TAIL = [
    ("link", "flag", "Sweep switched on (flag)", "sweep_flag"),
    ("calc", "sweep", "Cash swept to debt (USD)", "{flag}*{capped}"),
    ("link", "debt2", "Debt before the sweep (USD)", "debt_before_sweep"),
    ("calc", "debt_after", "Debt after the sweep (USD)", "{debt2}-{sweep}"),
    ("link", "cash2", "Cash available for the sweep (USD)", "cash_available_for_sweep"),
    ("calc", "cash_after", "Cash after the sweep (USD)", "{cash2}-{sweep}"),
]
LINK_CASH = ("link", "cash", "Cash available for the sweep (USD)", "cash_available_for_sweep")
LINK_DEBT = ("link", "debt", "Debt before the sweep (USD)", "debt_before_sweep")
PLAN = {
    PCT: [
        LINK_CASH,
        ("link", "pct", "Share of cash swept (ratio)", "sweep_percent"),
        ("calc", "part", "Cash at the sweep percentage (USD)", "{pct}*{cash}"),
        LINK_DEBT,
        ("calc", "capped", "Sweep within the debt (USD)", "MIN({part},{debt})"),
        *TAIL,
    ],  # fmt: skip
    TC: [
        LINK_CASH,
        ("link", "tcash", "Cash target (USD)", "target_cash"),
        ("calc", "excess", "Cash above the target (USD)", "MAX({cash}-{tcash},0)"),
        LINK_DEBT,
        ("calc", "capped", "Sweep within the debt (USD)", "MIN({excess},{debt})"),
        *TAIL,
    ],  # fmt: skip
    TL: [
        ("link", "ebitda", "EBITDA (USD)", "ebitda"),
        ("link", "lev", "Target leverage (ratio)", "target_leverage"),
        ("calc", "allowed", "Debt allowed at the target leverage (USD)", "{lev}*{ebitda}"),
        LINK_DEBT,
        ("calc", "excess", "Debt above the target leverage (USD)", "MAX({debt}-{allowed},0)"),
        LINK_CASH,
        ("calc", "capped", "Sweep within the cash available (USD)", "MIN({excess},{cash})"),
        *TAIL,
    ],  # fmt: skip
}


def _raw(method, inputs, i):
    cash, debt = float(inputs["cash_available_for_sweep"][i]), float(inputs["debt_before_sweep"][i])
    if method == PCT:
        return min(float(inputs["sweep_percent"]) * cash, debt)
    if method == TC:
        return min(max(cash - float(inputs["target_cash"]), 0.0), debt)
    return min(max(debt - float(inputs["target_leverage"]) * float(inputs["ebitda"][i]), 0.0), cash)


def make_oracle(method):
    def oracle(inputs: dict) -> dict[str, list[float]]:
        out = {p.name: [] for p in OUTPUTS}
        for i, flag in enumerate(inputs["sweep_flag"]):
            s = float(flag) * _raw(method, inputs, i)
            out["sweep_amount"].append(s)
            out["debt_after_sweep"].append(float(inputs["debt_before_sweep"][i]) - s)
            out["cash_after_sweep"].append(float(inputs["cash_available_for_sweep"][i]) - s)
        return out

    return oracle


def _values(method, inputs):
    V = {
        k: [] for k in ("part", "excess", "allowed", "capped", "sweep", "debt_after", "cash_after")
    }
    for i, flag in enumerate(inputs["sweep_flag"]):
        cash, debt = (
            float(inputs["cash_available_for_sweep"][i]),
            float(inputs["debt_before_sweep"][i]),
        )
        capped = _raw(method, inputs, i)
        V["capped"].append(capped)
        if method == PCT:
            V["part"].append(float(inputs["sweep_percent"]) * cash)
        elif method == TC:
            V["excess"].append(max(cash - float(inputs["target_cash"]), 0.0))
        else:
            allowed = float(inputs["target_leverage"]) * float(inputs["ebitda"][i])
            V["allowed"].append(allowed)
            V["excess"].append(max(debt - allowed, 0.0))
        s = float(flag) * capped
        V["sweep"].append(s)
        V["debt_after"].append(debt - s)
        V["cash_after"].append(cash - s)
    return V


def make_build(method):
    def build(ctx: BuildContext) -> None:
        build_plan(
            ctx, f"Cash sweep ({method})", PLAN[method], _values(method, ctx.inputs), KEYED, {}
        )

    return build


def make_checks(method):
    def checks(ctx: BuildContext) -> dict[str, str]:
        c = ctx.calcs
        r = c.rows()
        ports = {p.name: ctx.source(p.name) for p in ctx.module.inputs}
        S = lambda port, x: ports[port].format(col=x.col) if "{col}" in ports[port] else ports[port]  # noqa: E731
        K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
        cash, debt = (
            (lambda x: S("cash_available_for_sweep", x)),
            (lambda x: S("debt_before_sweep", x)),
        )

        def raw(x):
            if method == PCT:
                return f"MIN({ports['sweep_percent']}*{cash(x)},{debt(x)})"
            if method == TC:
                return f"MIN(MAX({cash(x)}-{ports['target_cash']},0),{debt(x)})"
            return f"MIN(MAX({debt(x)}-{ports['target_leverage']}*{S('ebitda', x)},0),{cash(x)})"

        c.section("Checks")
        c.row("chk_sweep", "  Check - sweep and balances re-derived from the ports (USD)",
              lambda x: f"=ABS({K('sweep_amount', x)}-{S('sweep_flag', x)}*{raw(x)})"
                        f"+ABS({K('debt_after_sweep', x)}-({debt(x)}-{K('sweep_amount', x)}))"
                        f"+ABS({K('cash_after_sweep', x)}-({cash(x)}-{K('sweep_amount', x)}))"
                        f"+MAX(-{K('debt_after_sweep', x)},0)", values=[0.0] * ctx.n)  # fmt: skip
        label = plan_checks(ctx, f"Cash sweep ({method})", PLAN[method], KEYED, lambda port, x: "0")
        return {"sweep": "Check - sweep and balances re-derived from the ports", "rows": label}

    return checks


def make_module(*, method, name, scope, example, golden) -> Module:
    return Module(name=name, version="0.1.0", scope=scope, inputs=COMMON + EXTRA[method], outputs=OUTPUTS,
                  oracle=make_oracle(method), build=make_build(method), checks=make_checks(method),
                  example=example, golden=golden)  # fmt: skip


def pending(inputs, name):
    return Golden(inputs=inputs, outputs={}, kind="hand-calculation",
                  source=f"PENDING: independent hand calculation by a reviewer agent that did not see the code; see docs/golden-cases/{name}.md")  # fmt: skip


SCOPE_OUT = [
    "Which cash is available (the waterfall decides what reaches the sweep)",
    "Application of the sweep across tranches or to the latest instalments first",
    "Prepayment fees and make-whole",
    "A sweep that changes the repayment schedule (the caller feeds the new balance back)",
]
