"""M20: distribution waterfall."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.distribution_waterfall import MODULE as M


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
        "distributable_cash": [0.0, 0.0, 0.0, 0.0],
        "equity_contribution": [1000.0, 0.0, 0.0, 0.0],
        "hurdle_rate": 0.1,
        "period_years": 1.0,
        "promote_share": 0.2,
        "opening_hurdle_balance": 0.0,
    }
    return {**base, **kw}


def test_unpaid_hurdle_compounds_at_the_hurdle_rate():
    out = M.oracle(case())
    assert out["hurdle_balance_closing"] == pytest.approx([1000.0, 1100.0, 1210.0, 1331.0])
    assert out["hurdle_accrual"] == pytest.approx([0.0, 100.0, 110.0, 121.0])
    assert follows(case())


def test_a_part_year_period_accrues_the_compounded_part_year_rate():
    inputs = case(
        hurdle_rate=0.21,
        period_years=0.5,
        opening_hurdle_balance=100.0,
        equity_contribution=[0.0] * 4,
    )
    assert M.oracle(inputs)["hurdle_accrual"] == pytest.approx([10.0, 11.0, 12.1, 13.31])
    assert follows(inputs)


def test_all_cash_goes_to_the_investor_until_the_hurdle_is_cleared_and_no_promote_is_paid():
    inputs = case(distributable_cash=[0.0, 600.0, 400.0, 0.0])
    out = M.oracle(inputs)
    assert out["tier1_distribution"] == [0.0, 600.0, 400.0, 0.0]
    assert out["sponsor_promote"] == [0.0] * 4 and out["residual_cash"] == [0.0] * 4
    assert follows(inputs)


def test_cash_above_the_hurdle_is_split_with_the_promote():
    inputs = case(distributable_cash=[0.0, 1500.0, 500.0, 0.0])
    out = M.oracle(inputs)
    assert out["tier1_distribution"][1] == pytest.approx(1100.0)
    assert out["residual_cash"][1] == pytest.approx(400.0)
    assert out["sponsor_promote"][1] == pytest.approx(80.0)
    assert out["investor_distribution"][1] == pytest.approx(1420.0)
    assert out["hurdle_balance_closing"][1] == pytest.approx(0.0)
    assert out["sponsor_promote"][2] == pytest.approx(
        100.0
    )  # hurdle cleared: all of it is residual
    assert follows(inputs)


def test_negative_distributable_cash_pays_nothing():
    inputs = case(distributable_cash=[-50.0, 0.0, 0.0, 0.0])
    out = M.oracle(inputs)
    assert out["investor_distribution"][0] == 0.0 and out["residual_cash"][0] == 0.0
    assert follows(inputs)


def test_investor_and_sponsor_receive_exactly_the_distributable_cash():
    inputs = case(
        distributable_cash=[0.0, 700.0, 900.0, 300.0], equity_contribution=[500.0, 0.0, 300.0, 0.0]
    )
    out = M.oracle(inputs)
    for i in range(4):
        assert out["investor_distribution"][i] + out["sponsor_promote"][i] == pytest.approx(
            inputs["distributable_cash"][i]
        )


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def promote_from_the_first_dollar(inputs):
        out = M.oracle(inputs)
        cash = [max(float(x), 0.0) for x in inputs["distributable_cash"]]
        promote = [0.2 * x for x in cash]
        return {**out, "sponsor_promote": promote}

    bad = replace(M, oracle=promote_from_the_first_dollar)
    assert "2" in {f.criterion for f in acceptance.check_module(bad, {"2"})}


def test_the_first_hand_calculation_is_kept_as_an_extra_case():
    inputs = {
        "distributable_cash": [0.0, 300.0, 700.0, 800.0],
        "equity_contribution": [1000.0, 0.0, 200.0, 0.0],
        "hurdle_rate": 0.21,
        "period_years": 0.5,
        "promote_share": 0.2,
        "opening_hurdle_balance": 0.0,
    }
    want = {
        "hurdle_accrual": [0.0, 100.0, 80.0, 38.0],
        "hurdle_balance_closing": [1000.0, 800.0, 380.0, 0.0],
        "tier1_distribution": [0.0, 300.0, 700.0, 418.0],
        "residual_cash": [0.0, 0.0, 0.0, 382.0],
        "sponsor_promote": [0.0, 0.0, 0.0, 76.4],
        "investor_distribution": [0.0, 300.0, 700.0, 723.6],
    }
    got = M.oracle(inputs)
    for name, values in want.items():
        assert got[name] == pytest.approx(values), name
    assert acceptance._compare(M, inputs, want, "3", "extra hand case") == []
