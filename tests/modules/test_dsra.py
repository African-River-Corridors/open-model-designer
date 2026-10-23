"""M11: DSRA."""

from dataclasses import replace

import pytest  # noqa: F401

from omd import acceptance
from omd.modules.dsra import MODULE as M


def follows(inputs):
    return acceptance._compare(M, inputs, M.oracle(inputs), "2", "case") == []


def test_criterion_3_the_golden_case_comes_from_an_independent_hand_calculation():
    assert acceptance.check_module(M, {"3"}) == []
    assert (
        M.golden.kind == "hand-calculation"
        and "reviewer agent that did not see the code" in M.golden.source
    )


def test_negative_control_without_checks_fails_criterion_4():
    bad = replace(M, checks=lambda ctx: {})
    assert "4" in {f.criterion for f in acceptance.check_module(bad, {"4"})}


def case(**kw):
    base = {
        "debt_service": [0.0, 100.0, 100.0, 100.0],
        "cash_available_for_dsra": [1000.0] * 4,
        "dsra_funding_gate": [1.0] * 4,
        "opening_dsra": 0.0,
    }
    return {**base, **kw}


def test_the_target_is_the_sum_of_the_next_two_periods_debt_service_and_falls_as_debt_is_repaid():
    inputs = case(debt_service=[0.0, 100.0, 100.0, 40.0])
    out = M.oracle(inputs)
    assert out["dsra_target"] == [200.0, 140.0, 40.0, 0.0]
    assert out["dsra_closing"] == [200.0, 140.0, 40.0, 0.0]
    assert out["dsra_release"] == [0.0, 60.0, 100.0, 40.0]
    assert follows(inputs)


def test_top_up_is_capped_by_cash_available_and_shown_as_a_shortfall_next_period():
    inputs = case(cash_available_for_dsra=[30.0, 30.0, 1000.0, 1000.0])
    out = M.oracle(inputs)
    assert out["dsra_transfer_in"][:3] == [30.0, 30.0, 40.0] and out["dsra_closing"][:2] == [
        30.0,
        60.0,
    ]
    assert follows(inputs)


def test_a_shut_funding_gate_stops_top_ups_when_one_is_needed_but_not_releases():
    inputs = case(dsra_funding_gate=[1.0, 0.0, 1.0, 1.0])
    out = M.oracle(inputs)
    assert out["dsra_transfer_in"][0] == 200.0 and out["dsra_transfer_in"][1] == 0.0
    shut = case(dsra_funding_gate=[0.0] * 4, opening_dsra=500.0)
    assert M.oracle(shut)["dsra_release"][0] == 300.0
    assert follows(inputs) and follows(shut)


def test_balance_reconciles_and_never_goes_negative():
    inputs = case(debt_service=[0.0, 80.0, 120.0, 60.0], opening_dsra=40.0)
    out = M.oracle(inputs)
    run = 40.0
    for i in range(4):
        run += out["dsra_transfer_in"][i] - out["dsra_release"][i]
        assert out["dsra_closing"][i] == pytest.approx(run) and run >= 0.0


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def never_releases(inputs):
        out = M.oracle(inputs)
        return {**out, "dsra_release": [0.0] * 4}

    assert "2" in {
        f.criterion for f in acceptance.check_module(replace(M, oracle=never_releases), {"2"})
    }


HAND_CASES = [  # independent hand calculations kept as extra tests (dsra.answer.md, dsra_2.answer.md)
    (
        {
            "debt_service": [0.0, 300.0, 300.0, 100.0],
            "cash_available_for_dsra": [400.0, 100.0, 400.0, 400.0],
            "dsra_funding_gate": [1.0, 1.0, 0.0, 1.0],
            "opening_dsra": 50.0,
        },
        {
            "dsra_target": [600.0, 400.0, 100.0, 0.0],
            "dsra_transfer_in": [400.0, 0.0, 0.0, 0.0],
            "dsra_release": [0.0, 50.0, 300.0, 100.0],
            "dsra_closing": [450.0, 400.0, 100.0, 0.0],
        },
    ),
    (
        {
            "debt_service": [0.0, 300.0, 300.0, 100.0],
            "cash_available_for_dsra": [400.0, 100.0, 400.0, 400.0],
            "dsra_funding_gate": [1.0, 0.0, 1.0, 1.0],
            "opening_dsra": 50.0,
        },
        {
            "dsra_target": [600.0, 400.0, 100.0, 0.0],
            "dsra_transfer_in": [400.0, 0.0, 0.0, 0.0],
            "dsra_release": [0.0, 50.0, 300.0, 100.0],
            "dsra_closing": [450.0, 400.0, 100.0, 0.0],
        },
    ),
]


@pytest.mark.parametrize("inputs,expected", HAND_CASES)
def test_the_oracle_matches_the_earlier_hand_calculations(inputs, expected):
    assert M.oracle(inputs) == expected


def test_a_module_that_ignores_the_gate_fails_the_golden_case():
    def ignores_gate(inputs):
        return M.oracle({**inputs, "dsra_funding_gate": [1.0] * 4})

    assert "3" in {
        f.criterion for f in acceptance.check_module(replace(M, oracle=ignores_gate), {"3"})
    }
