"""Lock-up and default tests.

    lock-up  = 1 where DSCR is below the lock-up threshold and debt is outstanding
    default  = 1 where DSCR is below the default threshold and debt is outstanding
    distributions permitted = 1 - lock-up

The tests read the DSCR from the cover-ratio module. Where no debt is outstanding the tests are off.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port
from ._plan_module import build_plan, plan_checks

INPUTS = (
    Port("dscr", "ratio", "series"),
    Port("debt_outstanding_flag", "count", "series"),
    Port("lockup_dscr", "ratio", "scalar"),
    Port("default_dscr", "ratio", "scalar"),
)
OUTPUTS = (
    Port("lockup_flag", "count", "series"),
    Port("default_flag", "count", "series"),
    Port("distributions_permitted_flag", "count", "series"),
)
T = "Lock-up and default"
KEYED = {"lock": "lockup_flag", "dflt": "default_flag", "permit": "distributions_permitted_flag"}
PLAN = [
    ("link", "dscr", "DSCR (ratio)", "dscr"),
    ("link", "lthr", "Lock-up threshold (ratio)", "lockup_dscr"),
    ("calc", "lock_raw", "DSCR below the lock-up threshold (flag)", "({dscr}<{lthr})*1"),
    ("link", "debt", "Debt outstanding (flag)", "debt_outstanding_flag"),
    ("calc", "lock", "Lock-up (flag)", "{lock_raw}*{debt}"),
    ("link", "dthr", "Default threshold (ratio)", "default_dscr"),
    ("link", "dscr2", "DSCR (ratio)", "dscr"),
    ("calc", "dflt_raw", "DSCR below the default threshold (flag)", "({dscr2}<{dthr})*1"),
    ("link", "debt2", "Debt outstanding (flag)", "debt_outstanding_flag"),
    ("calc", "dflt", "Default (flag)", "{dflt_raw}*{debt2}"),
    ("relink", "lock2", "Lock-up (flag)", "lock"),
    ("calc", "permit", "Distributions permitted (flag)", "1-{lock2}"),
]


def oracle(inputs: dict) -> dict[str, list[float]]:
    lt, dt = float(inputs["lockup_dscr"]), float(inputs["default_dscr"])
    lock, dflt = [], []
    for d, f in zip(inputs["dscr"], inputs["debt_outstanding_flag"], strict=True):
        lock.append((1.0 if float(d) < lt else 0.0) * float(f))
        dflt.append((1.0 if float(d) < dt else 0.0) * float(f))
    return {
        "lockup_flag": lock,
        "default_flag": dflt,
        "distributions_permitted_flag": [1.0 - x for x in lock],
    }


def _values(ctx_inputs):
    out = oracle(ctx_inputs)
    lt, dt = float(ctx_inputs["lockup_dscr"]), float(ctx_inputs["default_dscr"])
    d = [float(x) for x in ctx_inputs["dscr"]]
    return {
        "lock_raw": [1.0 if x < lt else 0.0 for x in d], "lock": out["lockup_flag"],
        "dflt_raw": [1.0 if x < dt else 0.0 for x in d], "dflt": out["default_flag"],
        "lock2": out["lockup_flag"], "permit": out["distributions_permitted_flag"],
    }  # fmt: skip


def build(ctx: BuildContext) -> None:
    build_plan(ctx, T, PLAN, _values(ctx.inputs), KEYED, {})


def checks(ctx: BuildContext) -> dict[str, str]:
    c = ctx.calcs
    r = c.rows()
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col) if "{col}" in src[port] else src[port]  # noqa: E731
    K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
    zero = [0.0] * ctx.n
    c.section("Checks")
    c.row("chk_tests", "  Check - flags re-derived from the ports (flag)",
          lambda x: f"=ABS({K('lockup_flag', x)}-({S('dscr', x)}<{S('lockup_dscr', x)})*{S('debt_outstanding_flag', x)})"
                    f"+ABS({K('default_flag', x)}-({S('dscr', x)}<{S('default_dscr', x)})*{S('debt_outstanding_flag', x)})"
                    f"+ABS({K('distributions_permitted_flag', x)}-(1-{K('lockup_flag', x)}))"
                    f"+MAX({K('default_flag', x)}-{K('lockup_flag', x)},0)", values=zero)  # fmt: skip
    label = plan_checks(ctx, T, PLAN, KEYED, lambda port, x: "0")
    return {"tests": "Check - flags re-derived from the ports", "rows": label}


LOCKUP = Module(
    name="lockup",
    version="0.1.0",
    scope={
        "in": [
            "A lock-up flag where DSCR is below the lock-up threshold and debt is outstanding",
            "A default flag where DSCR is below the default threshold and debt is outstanding",
            "A distributions-permitted flag (1 minus lock-up)",
            "A check that a default never occurs without a lock-up (default threshold below lock-up)",
        ],
        "out": [
            "Cure periods, consecutive-period tests and release conditions",
            "Other triggers (LLCR, reserve shortfall, completion tests)",
            "What happens in a default (acceleration, cash trap): the waterfall's job",
            "Reading DSCR: the ratio comes from the cover-ratio module",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example={
        "dscr": [1.5, 1.1, 1.0, 0.0],
        "debt_outstanding_flag": [1.0, 1.0, 1.0, 0.0],
        "lockup_dscr": 1.2,
        "default_dscr": 1.05,
    },
    golden=Golden(
        inputs={
            "dscr": [1.3, 1.1, 0.95, 0.95],
            "debt_outstanding_flag": [1.0, 1.0, 1.0, 0.0],
            "lockup_dscr": 1.3,
            "default_dscr": 1.1,
        },
        outputs={
            "lockup_flag": [0.0, 1.0, 1.0, 0.0],
            "default_flag": [0.0, 0.0, 1.0, 0.0],
            "distributions_permitted_flag": [1.0, 0.0, 0.0, 1.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); equal-to-threshold passes and a zero debt flag overrides both tests; working in docs/golden-cases/lockup_2.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = LOCKUP
