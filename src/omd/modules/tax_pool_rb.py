"""Tax depreciation pool, reducing balance. Rates come from the caller. See `_tax_pool`."""

from __future__ import annotations

from ..module import Golden
from ._tax_pool import RB, make_module

MODULE = make_module(
    method=RB,
    name="tax_pool_rb",
    scope={
        "in": [
            "One pool of cost; closing WDV = opening WDV + additions - allowance",
            "Allowance = share of period in use x rate x (opening WDV + additions)",
            "First-use rule: share of period in use is the share of the asset in service. 0 before "
            "first use, so cost waits in the pool and the unclaimed share stays there for later "
            "periods (not a private-use share, which would be lost)",
            "Brought-forward WDV as an input",
        ],
        "out": [
            "Several classes in one module: build one module instance per class",
            "A rate above 1 (the reducing-balance formulas do not cap at the pool)",
            "Disposals, balancing charges and pool-closure rules",
            "Any rate, class or jurisdiction: the rate is an input from a jurisdiction file",
            "Non-deductible spend or caps on repairs: a jurisdiction module's job",
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
            "tax_allowance": [0.0, 287.5, 503.125, 577.34375],
            "tax_wdv_close": [2000.0, 2012.5, 1509.375, 1732.03125],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); working in docs/golden-cases/tax_pool_rb.answer.md",
        kind="hand-calculation",
    ),
)
