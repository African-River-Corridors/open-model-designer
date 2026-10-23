"""Cash sweep, cash above a target. See `_sweep`."""

from __future__ import annotations

from ..module import Golden
from ._sweep import SCOPE_OUT, TC, make_module

MODULE = make_module(
    method=TC,
    name="cash_sweep_target_cash",
    scope={
        "in": [
            "Cash above a target balance is swept",
            "Switched by a sweep flag; never more than the debt",
            "Balances after the sweep: debt and cash",
        ],
        "out": SCOPE_OUT,
    },
    example={
        "cash_available_for_sweep": [100.0, 250.0, 400.0, 300.0],
        "debt_before_sweep": [500.0, 450.0, 300.0, 50.0],
        "sweep_flag": [1.0, 1.0, 1.0, 1.0],
        "target_cash": 150.0,
    },
    golden=Golden(
        inputs={
            "cash_available_for_sweep": [300.0, 120.0, 500.0, 450.0],
            "debt_before_sweep": [800.0, 700.0, 650.0, 100.0],
            "sweep_flag": [1.0, 1.0, 1.0, 0.0],
            "target_cash": 200.0,
        },
        outputs={
            "sweep_amount": [100.0, 0.0, 300.0, 0.0],
            "debt_after_sweep": [700.0, 700.0, 350.0, 100.0],
            "cash_after_sweep": [200.0, 120.0, 200.0, 450.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); the zero floor fires in a flagged period and a zero flag cancels a positive amount; working in docs/golden-cases/cash_sweep_target_cash_2.answer.md",
        kind="hand-calculation",
    ),
)
