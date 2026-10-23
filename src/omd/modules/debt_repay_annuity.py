"""Senior debt repayment, annuity. See `_debt_repay`."""

from __future__ import annotations

from ..module import Golden
from ._debt_repay import ANN, SCOPE_OUT, make_module

MODULE = make_module(
    method=ANN,
    name="debt_repay_annuity",
    scope={
        "in": [
            "A level payment that clears the opening debt over a number of repayment periods",
            "Interest on the opening balance; principal is the payment less interest",
            "Repayment only in flagged periods, never more than the balance",
            "Exact when repayment starts in the first period; a later start leaves the balance and "
            "the level payment unchanged until then",
        ],
        "out": ["A rate of zero (the annuity factor is undefined)", *SCOPE_OUT],
    },
    example={
        "repayment_flag": [1.0, 1.0, 1.0, 1.0],
        "interest_rate": 0.05,
        "opening_debt": 1000.0,
        "repayment_periods": 4.0,
    },
    golden=Golden(
        inputs={
            "repayment_flag": [1.0, 1.0, 1.0, 1.0],
            "interest_rate": 0.06,
            "opening_debt": 2000.0,
            "repayment_periods": 5.0,
        },
        outputs={
            "interest": [120.0, 98.71243194825726, 76.14760981340996, 52.22889835047182],
            "debt_repayment": [
                354.79280086237895,
                376.08036891412166,
                398.64519104896897,
                422.56390251190714,
            ],
            "debt_service": [
                474.79280086237895,
                474.79280086237895,
                474.79280086237895,
                474.79280086237895,
            ],
            "debt_closing": [
                1645.207199137621,
                1269.1268302234994,
                870.4816391745304,
                447.91773666262327,
            ],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/debt_repay_annuity.answer.md",
        kind="hand-calculation",
    ),
)
