"""M19: cash waterfall."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.cash_waterfall import MODULE as M
from omd.modules.cash_waterfall import make_cash_waterfall

TIERS = ("operating_costs", "senior_service", "reserve_top_up", "sub_service")


def follows(m, inputs):
    return acceptance._compare(m, inputs, m.oracle(inputs), "2", "case") == []


def test_criterion_3_the_golden_case_comes_from_an_independent_hand_calculation():
    assert acceptance.check_module(M, {"3"}) == []
    assert (
        M.golden.kind == "hand-calculation"
        and "reviewer agent that did not see the code" in M.golden.source
    )


def test_negative_control_without_checks_fails_criterion_4():
    bad = replace(M, checks=lambda ctx: {})
    assert "4" in {f.criterion for f in acceptance.check_module(bad, {"4"})}


def case(cash, **claims):
    base = {f"claim_{t}": [100.0] * 4 for t in TIERS}
    return {"cash_available": cash, **base, **claims}


def test_with_enough_cash_every_tier_is_paid_and_the_rest_remains():
    inputs = case([1000.0] * 4)
    out = M.oracle(inputs)
    assert all(out[f"unpaid_{t}"] == [0.0] * 4 for t in TIERS)
    assert out["cash_remainder"] == [600.0] * 4
    assert follows(M, inputs)


def test_cash_runs_out_in_tier_order_and_a_later_tier_is_not_paid_over_an_earlier_one():
    inputs = case([250.0, 100.0, 0.0, 400.0])
    out = M.oracle(inputs)
    assert [out[f"paid_{t}"][0] for t in TIERS] == [100.0, 100.0, 50.0, 0.0]
    assert [out[f"paid_{t}"][1] for t in TIERS] == [100.0, 0.0, 0.0, 0.0]
    assert out["unpaid_senior_service"] == [0.0, 100.0, 100.0, 0.0]
    assert out["cash_remainder"] == [0.0, 0.0, 0.0, 0.0]
    assert follows(M, inputs)


def test_nothing_is_paid_from_a_deficit_and_the_remainder_shows_it():
    inputs = case([-30.0, 0.0, 10.0, 0.0])
    out = M.oracle(inputs)
    assert out["paid_operating_costs"] == [0.0, 0.0, 10.0, 0.0]
    assert out["cash_remainder"][0] == pytest.approx(-30.0)
    assert follows(M, inputs)


def test_paid_amounts_and_the_remainder_sum_to_the_cash_available():
    inputs = case([380.0, 1000.0, 20.0, -5.0])
    out = M.oracle(inputs)
    for i in range(4):
        total = sum(out[f"paid_{t}"][i] for t in TIERS) + out["cash_remainder"][i]
        assert total == pytest.approx(inputs["cash_available"][i])


def test_tiers_are_configured_not_coded():
    two = make_cash_waterfall(("a", "b"))
    inputs = {
        "cash_available": [50.0, 150.0, 400.0, 0.0],
        "claim_a": [100.0] * 4,
        "claim_b": [200.0] * 4,
    }
    out = two.oracle(inputs)
    assert out["paid_a"] == [50.0, 100.0, 100.0, 0.0] and out["paid_b"] == [0.0, 50.0, 200.0, 0.0]
    assert [p.name for p in two.inputs] == ["cash_available", "claim_a", "claim_b"]
    assert follows(two, inputs)


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def pays_pro_rata(inputs):
        out = M.oracle(inputs)
        return {**out, "paid_senior_service": [p / 2 for p in out["paid_senior_service"]]}

    bad = replace(M, oracle=pays_pro_rata)
    assert "2" in {f.criterion for f in acceptance.check_module(bad, {"2"})}
