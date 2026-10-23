"""M13: cash sweep (percent, target cash, target leverage)."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.cash_sweep_percent import MODULE as PCT
from omd.modules.cash_sweep_target_cash import MODULE as TC
from omd.modules.cash_sweep_target_leverage import MODULE as TL

MODULES = [PCT, TC, TL]
IDS = [m.name for m in MODULES]


def follows(m, inputs):
    return acceptance._compare(m, inputs, m.oracle(inputs), "2", "case") == []


def base(**kw):
    d = {"cash_available_for_sweep": [100.0, 200.0, 300.0, 400.0], "debt_before_sweep": [500.0, 500.0, 500.0, 50.0],
         "sweep_flag": [1.0] * 4}  # fmt: skip
    return {**d, **kw}


@pytest.mark.parametrize("m", MODULES, ids=IDS)
def test_criterion_3_the_golden_case_comes_from_an_independent_hand_calculation(m):
    assert acceptance.check_module(m, {"3"}) == []
    assert (
        m.golden.kind == "hand-calculation"
        and "reviewer agent that did not see the code" in m.golden.source
    )


def test_percent_sweeps_a_share_of_cash_and_never_more_than_the_debt():
    inputs = base(sweep_percent=0.5)
    out = PCT.oracle(inputs)
    assert out["sweep_amount"] == [50.0, 100.0, 150.0, 50.0]  # the last is capped at the debt
    assert out["debt_after_sweep"][-1] == 0.0 and out["cash_after_sweep"][-1] == 350.0
    assert follows(PCT, inputs)


def test_target_cash_sweeps_only_the_cash_above_the_target():
    inputs = base(target_cash=150.0)
    assert TC.oracle(inputs)["sweep_amount"] == [0.0, 50.0, 150.0, 50.0]
    assert follows(TC, inputs)


def test_target_leverage_sweeps_down_to_the_target_within_the_cash_available():
    inputs = base(
        ebitda=[100.0] * 4, target_leverage=4.0, debt_before_sweep=[500.0, 450.0, 600.0, 300.0]
    )
    out = TL.oracle(inputs)
    assert out["sweep_amount"] == [
        100.0,
        50.0,
        200.0,
        0.0,
    ]  # 100 (excess 100), 50, 200 (cash-capped), 0
    assert follows(TL, inputs)


@pytest.mark.parametrize("m,extra", [(PCT, {"sweep_percent": 1.0}), (TC, {"target_cash": 0.0}),
                                     (TL, {"ebitda": [10.0] * 4, "target_leverage": 0.0})], ids=IDS)  # fmt: skip
def test_a_switched_off_sweep_sweeps_nothing(m, extra):
    inputs = base(sweep_flag=[0.0, 1.0, 0.0, 0.0], **extra)
    out = m.oracle(inputs)
    assert (
        out["sweep_amount"][0] == 0.0
        and out["sweep_amount"][2] == 0.0
        and out["sweep_amount"][1] > 0
    )
    assert follows(m, inputs)


@pytest.mark.parametrize("m", MODULES, ids=IDS)
def test_negative_control_a_wrong_oracle_fails_criterion_2(m):
    def double(inputs):
        out = m.oracle(inputs)
        return {**out, "sweep_amount": [v + 1.0 for v in out["sweep_amount"]]}

    assert "2" in {f.criterion for f in acceptance.check_module(replace(m, oracle=double), {"2"})}


@pytest.mark.parametrize("m", MODULES, ids=IDS)
def test_negative_control_without_checks_fails_criterion_4(m):
    bad = replace(m, checks=lambda ctx: {})
    assert "4" in {f.criterion for f in acceptance.check_module(bad, {"4"})}


EARLIER_HAND_CASES = [  # independent hand calculations kept as extra tests (docs/golden-cases/cash_sweep_*.answer.md)
    (
        TC,
        {
            "cash_available_for_sweep": [300.0, 120.0, 500.0, 450.0],
            "debt_before_sweep": [800.0, 700.0, 650.0, 100.0],
            "sweep_flag": [1.0, 0.0, 1.0, 1.0],
            "target_cash": 200.0,
        },
        {
            "sweep_amount": [100.0, 0.0, 300.0, 100.0],
            "debt_after_sweep": [700.0, 700.0, 350.0, 0.0],
            "cash_after_sweep": [200.0, 120.0, 200.0, 350.0],
        },
    ),
    (
        TL,
        {
            "cash_available_for_sweep": [250.0, 100.0, 600.0, 600.0],
            "debt_before_sweep": [1000.0, 900.0, 800.0, 500.0],
            "ebitda": [300.0, 300.0, 320.0, 340.0],
            "sweep_flag": [1.0, 1.0, 1.0, 0.0],
            "target_leverage": 2.5,
        },
        {
            "sweep_amount": [250.0, 100.0, 0.0, 0.0],
            "debt_after_sweep": [750.0, 800.0, 800.0, 500.0],
            "cash_after_sweep": [0.0, 0.0, 600.0, 600.0],
        },
    ),
    (
        TL,
        {
            "cash_available_for_sweep": [400.0, 100.0, 600.0, 600.0],
            "debt_before_sweep": [1000.0, 900.0, 800.0, 500.0],
            "ebitda": [300.0, 300.0, 320.0, 340.0],
            "sweep_flag": [1.0, 1.0, 1.0, 1.0],
            "target_leverage": 2.5,
        },
        {
            "sweep_amount": [250.0, 100.0, 0.0, 0.0],
            "debt_after_sweep": [750.0, 800.0, 800.0, 500.0],
            "cash_after_sweep": [150.0, 0.0, 600.0, 600.0],
        },
    ),
]


@pytest.mark.parametrize("m,inputs,expected", EARLIER_HAND_CASES)
def test_the_oracle_matches_the_earlier_hand_calculations(m, inputs, expected):
    assert m.oracle(inputs) == expected


@pytest.mark.parametrize("m", [TC, TL])
def test_a_module_that_ignores_the_flag_fails_its_golden_case(m):
    def ignores_flag(inputs):
        return m.oracle({**inputs, "sweep_flag": [1.0] * 4})

    assert "3" in {
        f.criterion for f in acceptance.check_module(replace(m, oracle=ignores_flag), {"3"})
    }
