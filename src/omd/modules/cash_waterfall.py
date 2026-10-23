"""Cash waterfall: ordered claims on the cash available, each paid if cash is there.

The tiers are configured, not coded: `make_cash_waterfall(tiers)` builds the module for any ordered list
of tier names, each with a claim port `claim_<tier>`. `MODULE` is the default four-tier configuration.

    paid_k    = min(claim_k, max(cash left before tier k, 0))
    cash left after tier k = cash left before tier k - paid_k          (the first tier starts from the cash available)
    unpaid_k  = claim_k - paid_k
    remainder = cash left after the last tier                         (negative when there is a deficit)

A later tier is never paid while an earlier tier is unpaid: a check row reads non-zero if it is.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port
from ._plan_module import build_plan, plan_checks

DEFAULT_TIERS = ("operating_costs", "senior_service", "reserve_top_up", "sub_service")


def make_cash_waterfall(tiers: tuple[str, ...], *, example=None, golden=None) -> Module:
    tiers = tuple(tiers)
    assert len(tiers) >= 1 and len(set(tiers)) == len(tiers), "tiers must be distinct names"
    n_tiers = len(tiers)
    INPUTS = (
        Port("cash_available", "USD", "series"),
        *(Port(f"claim_{t}", "USD", "series") for t in tiers),
    )
    OUTPUTS = (
        *(Port(f"paid_{t}", "USD", "series") for t in tiers),
        *(Port(f"unpaid_{t}", "USD", "series") for t in tiers),
        Port("cash_remainder", "USD", "series"),
    )
    T = "Cash waterfall"
    KEYED: dict[str, str] = {}
    PLAN: list[tuple[str, str, str, str]] = [
        ("link", "cash", "Cash available (USD)", "cash_available")
    ]
    for k, t in enumerate(tiers, 1):
        before = "cash" if k == 1 else f"av{k - 1}"
        PLAN += [("link", f"c{k}", f"Claim - {t} (USD)", f"claim_{t}")]
        if k == 1:
            PLAN += [
                ("calc", f"paid{k}", f"Paid - {t} (USD)", f"MIN({{c{k}}},MAX({{{before}}},0))")
            ]
            PLAN += [("link", f"cashb{k}", "Cash available (USD)", "cash_available")]
            before2 = f"cashb{k}"
        else:
            PLAN += [("relink", f"avb{k}", f"Cash left before {t} (USD)", before)]
            PLAN += [("calc", f"paid{k}", f"Paid - {t} (USD)", f"MIN({{c{k}}},MAX({{avb{k}}},0))")]
            PLAN += [("relink", f"avc{k}", f"Cash left before {t} (USD)", before)]
            before2 = f"avc{k}"
        PLAN += [("calc", f"av{k}", f"Cash left after {t} (USD)", f"{{{before2}}}-{{paid{k}}}")]
        PLAN += [("link", f"cu{k}", f"Claim - {t} (USD)", f"claim_{t}")]
        PLAN += [("relink", f"pu{k}", f"Paid - {t} (USD)", f"paid{k}")]
        PLAN += [("calc", f"unpaid{k}", f"Unpaid - {t} (USD)", f"{{cu{k}}}-{{pu{k}}}")]
        KEYED[f"paid{k}"] = f"paid_{t}"
        KEYED[f"unpaid{k}"] = f"unpaid_{t}"
    KEYED[f"av{n_tiers}"] = "cash_remainder"

    def _run(inputs):
        V: dict[str, list[float]] = {name: [] for _k, name, _l, _s in PLAN}
        for i, cash in enumerate(inputs["cash_available"]):
            cash = float(cash)
            left, row = cash, {"cash": cash}
            for k, t in enumerate(tiers, 1):
                claim = float(inputs[f"claim_{t}"][i])
                paid = min(claim, max(left, 0.0))
                if k == 1:
                    row.update({f"c{k}": claim, f"paid{k}": paid, f"cashb{k}": cash})
                else:
                    row.update({f"c{k}": claim, f"avb{k}": left, f"paid{k}": paid, f"avc{k}": left})
                left = left - paid
                row.update(
                    {f"av{k}": left, f"cu{k}": claim, f"pu{k}": paid, f"unpaid{k}": claim - paid}
                )
            for key, v in row.items():
                V[key].append(v)
        return V

    def oracle(inputs: dict) -> dict[str, list[float]]:
        V = _run(inputs)
        return {port: V[name] for name, port in KEYED.items()}

    def build(ctx: BuildContext) -> None:
        build_plan(ctx, T, PLAN, _run(ctx.inputs), KEYED, {})

    def checks(ctx: BuildContext) -> dict[str, str]:
        c = ctx.calcs
        r = c.rows()
        src = {p.name: ctx.source(p.name) for p in INPUTS}
        S = lambda port, x: src[port].format(col=x.col)  # noqa: E731
        K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
        zero = [0.0] * ctx.n

        def cum_claims(k, x):  # sum of the claims of tiers 1..k, straight from the ports
            return "(" + "+".join(S(f"claim_{t}", x) for t in tiers[:k]) + ")" if k else "0"

        def share(
            k, x
        ):  # what the first k tiers can take from the cash, whatever the order within them
            return f"MIN(MAX({S('cash_available', x)},0),{cum_claims(k, x)})" if k else "0"

        def derived(x):
            parts = []
            for k, t in enumerate(tiers, 1):
                parts.append(f"{K(f'paid_{t}', x)}-({share(k, x)}-{share(k - 1, x)})")
                parts.append(f"{K(f'unpaid_{t}', x)}-({S(f'claim_{t}', x)}-{K(f'paid_{t}', x)})")
            paid_all = "+".join(K(f"paid_{t}", x) for t in tiers)
            parts.append(f"{K('cash_remainder', x)}-({S('cash_available', x)}-({paid_all}))")
            return "=" + "+".join(f"ABS({p})" for p in parts)

        def priority(x):
            terms = [
                f"MIN({K(f'unpaid_{tiers[k - 1]}', x)},{K(f'paid_{tiers[k]}', x)})"
                for k in range(1, n_tiers)
            ]
            terms += [f"MAX(-{K(f'paid_{t}', x)},0)" for t in tiers]
            return "=" + "+".join(terms)

        c.section("Checks")
        c.row("chk_waterfall", "  Check - each tier re-derived from the cash and the claims on the ports (USD)",
              derived, values=zero)  # fmt: skip
        c.row("chk_priority", "  Check - no tier is paid while an earlier tier is unpaid (USD)",
              priority, values=zero)  # fmt: skip
        label = plan_checks(ctx, T, PLAN, KEYED, lambda port, x: "0")
        return {
            "waterfall": "Check - each tier re-derived from the cash and the claims on the ports",
            "priority": "Check - no tier is paid while an earlier tier is unpaid",
            "rows": label,
        }

    return Module(
        name="cash_waterfall",
        version="0.1.0",
        scope={
            "in": [
                "Any number of ordered tiers, named when the module is built; each tier's claim is an input series",
                "Each tier paid in full if the cash left allows, otherwise what is left; nothing paid from a deficit",
                "The unpaid amount of each tier and the cash remaining after the last tier",
            ],
            "out": [
                "What the claims are (debt service, reserve top-ups): they come from other modules",
                "Pari passu tiers sharing a shortfall pro rata (one tier per claim, in strict order)",
                "Carrying unpaid claims forward as arrears: each period stands alone (the unpaid amount of each tier is shown on its own row)",
                "Funding a negative cash amount (from the DSRA, a standby facility or equity): it passes to the remainder as a negative number",
                "Cure and lock-up (see the lock-up module)",
                "Changing the tier order after the model is built (the order is fixed at build time)",
            ],
        },
        inputs=INPUTS,
        outputs=OUTPUTS,
        oracle=oracle,
        build=build,
        checks=checks,
        example=example,
        golden=golden,
    )


_EXAMPLE = {
    "cash_available": [900.0, 500.0, 300.0, 0.0],
    "claim_operating_costs": [150.0, 150.0, 150.0, 150.0],
    "claim_senior_service": [400.0, 400.0, 400.0, 400.0],
    "claim_reserve_top_up": [50.0, 50.0, 50.0, 50.0],
    "claim_sub_service": [200.0, 200.0, 200.0, 200.0],
}
_GOLDEN = Golden(
    inputs={
        "cash_available": [1500.0, 900.0, 250.0, -50.0],
        "claim_operating_costs": [200.0, 200.0, 200.0, 200.0],
        "claim_senior_service": [500.0, 500.0, 500.0, 500.0],
        "claim_reserve_top_up": [100.0, 100.0, 100.0, 100.0],
        "claim_sub_service": [300.0, 300.0, 300.0, 300.0],
    },
    outputs={
        "paid_operating_costs": [200.0, 200.0, 200.0, 0.0],
        "paid_senior_service": [500.0, 500.0, 50.0, 0.0],
        "paid_reserve_top_up": [100.0, 100.0, 0.0, 0.0],
        "paid_sub_service": [300.0, 100.0, 0.0, 0.0],
        "unpaid_operating_costs": [0.0, 0.0, 0.0, 200.0],
        "unpaid_senior_service": [0.0, 0.0, 450.0, 500.0],
        "unpaid_reserve_top_up": [0.0, 0.0, 100.0, 100.0],
        "unpaid_sub_service": [0.0, 200.0, 300.0, 300.0],
        "cash_remainder": [400.0, 0.0, 0.0, -50.0],
    },
    source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); pay-if-available, no arrears carried, negative cash passes to the remainder; working in docs/golden-cases/cash_waterfall.answer.md",
    kind="hand-calculation",
)
CASH_WATERFALL = make_cash_waterfall(DEFAULT_TIERS, example=_EXAMPLE, golden=_GOLDEN)
MODULE = CASH_WATERFALL
