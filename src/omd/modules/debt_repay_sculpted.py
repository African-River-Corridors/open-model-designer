"""Senior debt repayment, sculpted to a DSCR. See `_debt_repay`."""

from __future__ import annotations

from ..module import Golden
from ._debt_repay import SCOPE_OUT, SCU, make_module

# the debt a 1.4x DSCR sculpt of these CFADS clears exactly at 5% (so the maturity check is quiet)
_EXAMPLE_CFADS = [200.0, 220.0, 240.0, 260.0]
_EXAMPLE_DEBT = sum(c / 1.4 / 1.05 ** (i + 1) for i, c in enumerate(_EXAMPLE_CFADS))

MODULE = make_module(
    method=SCU,
    name="debt_repay_sculpted",
    scope={
        "in": [
            "Principal = CFADS / target DSCR less interest, floored at nil, capped at the balance",
            "Interest on the opening balance (no circularity), paid every period",
            "Repayment only in flagged periods",
        ],
        "out": [
            "CFADS that depends on the repayment (tax shield on interest): the caller supplies CFADS",
            "Sizing the debt from the sculpted profile (PV of CFADS / DSCR at the loan rate): debt is an "
            "input, so a balance can remain at maturity. It shows on the 'Debt balance at maturity' row "
            "and a check goes red when it is not zero. A sizing module may follow later",
            *SCOPE_OUT,
        ],
    },
    example={
        "repayment_flag": [1.0, 1.0, 1.0, 1.0],
        "interest_rate": 0.05,
        "opening_debt": _EXAMPLE_DEBT,
        "cfads": _EXAMPLE_CFADS,
        "target_dscr": 1.4,
    },
    golden=Golden(
        inputs={
            "repayment_flag": [1.0, 1.0, 1.0, 1.0],
            "interest_rate": 0.06,
            "opening_debt": 600.0,
            "cfads": [150.0, 180.0, 210.0, 240.0],
            "target_dscr": 1.25,
        },
        outputs={
            "interest": [36.0, 30.96, 24.1776, 15.548256],
            "debt_repayment": [84.0, 113.04, 143.8224, 176.451744],
            "debt_service": [120.0, 144.0, 168.0, 192.0],
            "debt_closing": [516.0, 402.96, 259.1376, 82.685856],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); literal behaviour: debt is an input, a balance remains at maturity; working in docs/golden-cases/debt_repay_sculpted.answer.md",
        kind="hand-calculation",
    ),
)
