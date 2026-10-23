"""Tax depreciation pool, straight line on cumulative cost. See `_tax_pool`."""

from __future__ import annotations

from ..module import Golden
from ._tax_pool import SL, make_module

MODULE = make_module(
    method=SL,
    name="tax_pool_sl",
    scope={
        "in": [
            "One pool of cost; closing WDV = opening WDV + additions - allowance",
            "Allowance = share of period in use x rate x cumulative cost, never more than the pool",
            "First-use rule: share of period in use is 0 before first use, so cost waits in the pool",
            "Brought-forward WDV as an input, treated as cost",
        ],
        "out": [
            "Per-asset lives: a cost layer keeps earning its allowance until the pool is empty "
            "(the cap), not until its own life ends. Exact while no layer reaches the end of its life",
            "Several classes in one module: build one module instance per class",
            "Disposals, balancing charges and pool-closure rules",
            "Any rate, class or jurisdiction: the rate is an input from a jurisdiction file",
        ],
    },
    example={
        "capital_additions": [1000.0, 0.0, 500.0, 0.0],
        "use_fraction": [0.5, 1.0, 1.0, 1.0],
        "allowance_rate": 0.2,
        "opening_wdv": 200.0,
    },
    golden=Golden(
        inputs={
            "capital_additions": [2000.0, 300.0, 0.0, 800.0],
            "use_fraction": [0.0, 0.5, 1.0, 1.0],
            "allowance_rate": 0.25,
            "opening_wdv": 0.0,
        },
        outputs={
            "tax_allowance": [0.0, 287.5, 575.0, 775.0],
            "tax_wdv_close": [2000.0, 2012.5, 1437.5, 1462.5],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/tax_pool_sl.answer.md",
        kind="hand-calculation",
    ),
)
