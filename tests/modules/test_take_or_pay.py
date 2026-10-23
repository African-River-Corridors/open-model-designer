"""M18: take-or-pay."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.take_or_pay import MODULE as M


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
        "contracted_minimum": [100.0] * 4,
        "delivered_volume": [100.0] * 4,
        "unit_price": 10.0,
        "shortfall_payment_share": 1.0,
    }
    return {**base, **kw}


def test_delivery_at_the_minimum_pays_sales_and_no_shortfall():
    out = M.oracle(case())
    assert out["revenue"] == [1000.0] * 4 and out["shortfall_payment"] == [0.0] * 4
    assert follows(case())


def test_delivery_above_the_minimum_is_paid_at_the_price_with_no_shortfall():
    out = M.oracle(case(delivered_volume=[150.0] * 4))
    assert out["shortfall_volume"] == [0.0] * 4 and out["revenue"] == [1500.0] * 4
    assert follows(case(delivered_volume=[150.0] * 4))


def test_a_shortfall_is_paid_for_at_the_share_of_the_price():
    inputs = case(delivered_volume=[60.0, 100.0, 0.0, 90.0], shortfall_payment_share=0.5)
    out = M.oracle(inputs)
    assert out["shortfall_volume"] == [40.0, 0.0, 100.0, 10.0]
    assert out["shortfall_payment"] == pytest.approx([200.0, 0.0, 500.0, 50.0])
    assert out["revenue"] == pytest.approx([800.0, 1000.0, 500.0, 950.0])
    assert follows(inputs)


def test_a_zero_share_makes_revenue_pay_as_you_deliver():
    inputs = case(delivered_volume=[60.0] * 4, shortfall_payment_share=0.0)
    assert M.oracle(inputs)["revenue"] == [600.0] * 4
    assert follows(inputs)


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def pays_the_full_price_on_shortfall(inputs):
        return M.oracle({**inputs, "shortfall_payment_share": 1.0})

    bad = replace(M, oracle=pays_the_full_price_on_shortfall)
    assert "2" in {f.criterion for f in acceptance.check_module(bad, {"2"})}
