"""Cash sweep, to a target leverage. See `_sweep`."""

from __future__ import annotations

from ..module import Golden
from ._sweep import SCOPE_OUT, TL, make_module

MODULE = make_module(
    method=TL,
    name="cash_sweep_target_leverage",
    scope={
        "in": [
            "Debt above a target multiple of EBITDA is swept, within the cash available",
            "Switched by a sweep flag; never more than the debt",
            "Balances after the sweep: debt and cash",
        ],
        "out": SCOPE_OUT,
    },
    example={
        "cash_available_for_sweep": [100.0, 300.0, 400.0, 400.0],
        "debt_before_sweep": [900.0, 800.0, 600.0, 300.0],
        "ebitda": [200.0, 220.0, 240.0, 260.0],
        "sweep_flag": [1.0, 1.0, 1.0, 1.0],
        "target_leverage": 3.0,
    },
    golden=Golden(
        inputs={
            "cash_available_for_sweep": [400.0, 100.0, 600.0, 600.0],
            "debt_before_sweep": [1000.0, 900.0, 800.0, 500.0],
            "ebitda": [300.0, 300.0, 320.0, 340.0],
            "sweep_flag": [1.0, 0.0, 1.0, 1.0],
            "target_leverage": 2.5,
        },
        outputs={
            "sweep_amount": [250.0, 0.0, 0.0, 0.0],
            "debt_after_sweep": [750.0, 900.0, 800.0, 500.0],
            "cash_after_sweep": [150.0, 100.0, 600.0, 600.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); the excess-debt cap, a zero flag on a positive amount, an exactly-zero excess and the zero floor all fire; working in docs/golden-cases/cash_sweep_target_leverage_3.answer.md",
        kind="hand-calculation",
    ),
)
