"""M3: vintaged tax losses."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.tax_losses import MODULE as M


def case(profit, life, opening=0.0):
    return {"taxable_profit_pre_loss": profit, "loss_life": life, "opening_losses": opening}


def follows(inputs):
    return acceptance._compare(M, inputs, M.oracle(inputs), "2", "case") == []


def test_criterion_3_the_golden_case_comes_from_an_independent_hand_calculation():
    assert acceptance.check_module(M, {"3"}) == []
    assert (
        M.golden.kind == "hand-calculation"
        and "reviewer agent that did not see the code" in M.golden.source
    )


def test_relief_is_oldest_first():
    inputs = case([-100.0, -50.0, 120.0, 0.0], 10.0)
    out = M.oracle(inputs)
    assert out["tax_loss_used"][2] == 120.0 and out["taxable_after_losses"][2] == 0.0
    assert out["tax_loss_closing"][2] == 30.0  # 100 + 50 - 120
    assert follows(inputs)


def test_a_loss_is_usable_in_the_life_periods_after_it_was_made_then_expires():
    # loss of 100 in period 1, life 2: usable in periods 2 and 3, expires in period 4 (age 3 > 2)
    inputs = case([-100.0, 0.0, 80.0, 90.0], 2.0)
    out = M.oracle(inputs)
    assert out["tax_loss_used"] == [0.0, 0.0, 80.0, 0.0]  # period 3 is still inside the life
    assert out["tax_loss_expired"] == [0.0, 0.0, 0.0, 20.0]
    assert out["taxable_after_losses"][3] == 90.0
    assert follows(inputs)


def test_a_loss_made_this_period_cannot_relieve_this_period():
    inputs = case([-40.0, 25.0, 0.0, 0.0], 5.0)
    assert M.oracle(inputs)["tax_loss_used"] == [0.0, 25.0, 0.0, 0.0]
    assert follows(inputs)


def test_brought_forward_losses_are_the_oldest_pool_and_age_from_period_zero():
    inputs = case([0.0, 0.0, 50.0, 0.0], 2.0, 70.0)
    out = M.oracle(inputs)
    assert out["tax_loss_expired"][2] == 70.0  # age 3 > 2 in period 3, before relief
    assert out["tax_loss_used"][2] == 0.0
    assert M.oracle(case([0.0, 50.0, 0.0, 0.0], 2.0, 70.0))["tax_loss_used"][1] == 50.0
    assert follows(inputs)


def test_closing_balance_reconciles_over_a_longer_run():
    inputs = case([-80.0, 30.0, -20.0, 90.0], 3.0, 10.0)
    out = M.oracle(inputs)
    gen = [80.0, 0.0, 20.0, 0.0]
    run = 10.0
    for t in range(4):
        run += gen[t] - out["tax_loss_used"][t] - out["tax_loss_expired"][t]
        assert out["tax_loss_closing"][t] == pytest.approx(run)
    assert follows(inputs)


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def off_by_one_life(inputs):  # the ">=" reading: expires one period early
        return M.oracle({**inputs, "loss_life": inputs["loss_life"] - 1.0})

    bad = replace(M, oracle=off_by_one_life)
    assert "2" in {f.criterion for f in acceptance.check_module(bad, {"2"})}


def test_negative_control_without_checks_fails_criterion_4():
    bad = replace(M, checks=lambda ctx: {})
    assert "4" in {f.criterion for f in acceptance.check_module(bad, {"4"})}
