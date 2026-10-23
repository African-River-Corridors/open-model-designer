"""Cash sweep, percent of cash. See `_sweep`."""

from __future__ import annotations

from ..module import Golden
from ._sweep import PCT, SCOPE_OUT, make_module

MODULE = make_module(
    method=PCT,
    name="cash_sweep_percent",
    scope={
        "in": [
            "A fixed percentage of the cash available is swept",
            "Switched by a sweep flag; never more than the debt",
            "Balances after the sweep: debt and cash",
        ],
        "out": SCOPE_OUT,
    },
    example={
        "cash_available_for_sweep": [100.0, 200.0, 300.0, 400.0],
        "debt_before_sweep": [500.0, 300.0, 120.0, 0.0],
        "sweep_flag": [1.0, 1.0, 1.0, 1.0],
        "sweep_percent": 0.5,
    },
    golden=Golden(
        inputs={
            "cash_available_for_sweep": [200.0, 300.0, 100.0, 500.0],
            "debt_before_sweep": [900.0, 700.0, 600.0, 50.0],
            "sweep_flag": [1.0, 1.0, 0.0, 1.0],
            "sweep_percent": 0.75,
        },
        outputs={
            "sweep_amount": [150.0, 225.0, 0.0, 50.0],
            "debt_after_sweep": [750.0, 475.0, 600.0, 0.0],
            "cash_after_sweep": [50.0, 75.0, 100.0, 450.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/cash_sweep_percent.answer.md",
        kind="hand-calculation",
    ),
)
