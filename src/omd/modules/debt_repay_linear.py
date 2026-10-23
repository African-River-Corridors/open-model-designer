"""Senior debt repayment, straight line. See `_debt_repay`."""

from __future__ import annotations

from ..module import Golden
from ._debt_repay import LIN, SCOPE_OUT, make_module

MODULE = make_module(
    method=LIN,
    name="debt_repay_linear",
    scope={
        "in": [
            "Equal principal instalments over the flagged repayment periods (the number is derived from the flags, so the two cannot disagree)",
            "Interest on the opening balance, paid every period",
            "Repayment only in flagged periods, never more than the balance",
        ],
        "out": [
            "At least one flagged period is needed (none leaves the instalment undefined)",
            *SCOPE_OUT,
        ],
    },
    example={
        "repayment_flag": [0.0, 1.0, 1.0, 1.0],
        "interest_rate": 0.05,
        "opening_debt": 900.0,
    },
    golden=Golden(
        inputs={
            "repayment_flag": [1.0, 1.0, 1.0, 0.0],
            "interest_rate": 0.04,
            "opening_debt": 1200.0,
        },
        outputs={
            "interest": [48.0, 32.0, 16.0, 0.0],
            "debt_repayment": [400.0, 400.0, 400.0, 0.0],
            "debt_service": [448.0, 432.0, 416.0, 0.0],
            "debt_closing": [800.0, 400.0, 0.0, 0.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); repayment spread over the flagged periods (standard reading); working in docs/golden-cases/debt_repay_linear.answer.md",
        kind="hand-calculation",
    ),
)
