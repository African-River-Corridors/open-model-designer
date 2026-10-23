"""M4: corporate tax engine."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.tax_engine import MODULE as M


def case(**kw):
    base = {
        "profit_before_tax": [100.0, 100.0, 100.0, 100.0],
        "tax_adjustments": [0.0] * 4,
        "losses_relieved": [0.0] * 4,
        "minimum_tax": [0.0] * 4,
        "tax_rate": 0.25,
        "instalment_share": 1.0,
        "opening_tax_payable": 0.0,
    }
    return {**base, **kw}


def follows(inputs):
    return acceptance._compare(M, inputs, M.oracle(inputs), "2", "case") == []


def test_criterion_3_the_golden_case_comes_from_an_independent_hand_calculation():
    assert acceptance.check_module(M, {"3"}) == []
    assert (
        M.golden.kind == "hand-calculation"
        and "reviewer agent that did not see the code" in M.golden.source
    )


def test_with_a_zero_floor_the_charge_is_rate_times_taxable_profit():
    out = M.oracle(case())
    assert out["tax_charge"] == [25.0] * 4 and out["taxable_profit"] == [100.0] * 4
    assert follows(case())


def test_the_floor_hook_lifts_the_charge_when_it_exceeds_the_normal_charge():
    inputs = case(minimum_tax=[0.0, 40.0, 0.0, 10.0])
    assert M.oracle(inputs)["tax_charge"] == [25.0, 40.0, 25.0, 25.0]
    assert follows(inputs)


def test_a_loss_year_still_pays_the_floor():
    inputs = case(profit_before_tax=[-500.0] * 4, minimum_tax=[7.0] * 4)
    out = M.oracle(inputs)
    assert out["taxable_profit"] == [0.0] * 4 and out["tax_charge"] == [7.0] * 4
    assert follows(inputs)


def test_adjustments_and_losses_move_taxable_profit():
    inputs = case(tax_adjustments=[20.0, 0.0, -30.0, 0.0], losses_relieved=[0.0, 60.0, 0.0, 200.0])
    assert M.oracle(inputs)["taxable_profit"] == [120.0, 40.0, 70.0, 0.0]
    assert follows(inputs)


def test_payment_timing_instalments_arrears_and_the_opening_liability():
    inputs = case(instalment_share=0.5, opening_tax_payable=10.0)
    out = M.oracle(inputs)
    assert out["tax_paid"] == [10.0 + 12.5, 12.5 + 12.5, 25.0, 25.0]
    assert out["tax_payable_closing"] == [12.5] * 4
    assert follows(inputs)


def test_liability_reconciles():
    inputs = case(instalment_share=0.4, opening_tax_payable=5.0, minimum_tax=[30, 0, 0, 0])
    out = M.oracle(inputs)
    run = 5.0
    for i in range(4):
        run += out["tax_charge"][i] - out["tax_paid"][i]
        assert out["tax_payable_closing"][i] == pytest.approx(run)


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def no_floor(inputs):
        return M.oracle({**inputs, "minimum_tax": [0.0] * 4})

    assert "2" in {f.criterion for f in acceptance.check_module(replace(M, oracle=no_floor), {"2"})}


def test_negative_control_without_checks_fails_criterion_4():
    bad = replace(M, checks=lambda ctx: {})
    assert "4" in {f.criterion for f in acceptance.check_module(bad, {"4"})}
