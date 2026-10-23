"""M2: tax depreciation pools."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.tax_pool_rb import MODULE as RB
from omd.modules.tax_pool_sl import MODULE as SL

MODULES = [RB, SL]


@pytest.mark.parametrize("m", MODULES, ids=lambda m: m.name)
def test_criterion_3_the_golden_case_comes_from_an_independent_hand_calculation(m):
    assert acceptance.check_module(m, {"3"}) == []
    assert (
        m.golden.kind == "hand-calculation"
        and "reviewer agent that did not see the code" in m.golden.source
    )


def case(adds, use, rate, opening):
    return {
        "capital_additions": adds,
        "use_fraction": use,
        "allowance_rate": rate,
        "opening_wdv": opening,
    }


def formulas_follow_oracle(m, inputs):
    return acceptance._compare(m, inputs, m.oracle(inputs), "2", "case") == []


def test_before_first_use_there_is_no_allowance_and_cost_waits_in_the_pool():
    inputs = case([100.0, 50.0, 0.0, 0.0], [0.0, 0.0, 1.0, 1.0], 0.5, 0.0)
    for m in MODULES:
        out = m.oracle(inputs)
        assert out["tax_allowance"][:2] == [0.0, 0.0]
        assert out["tax_wdv_close"][:2] == [100.0, 150.0]
        assert out["tax_allowance"][2] > 0
        assert formulas_follow_oracle(m, inputs)


def test_reducing_balance_charges_the_rate_on_the_balance():
    out = RB.oracle(case([0.0] * 4, [1.0] * 4, 0.5, 1600.0))
    assert out["tax_allowance"] == [800.0, 400.0, 200.0, 100.0]
    assert out["tax_wdv_close"] == [800.0, 400.0, 200.0, 100.0]


def test_straight_line_charges_the_rate_on_cost_until_the_pool_is_empty():
    inputs = case([0.0] * 4, [1.0] * 4, 0.4, 1000.0)
    out = SL.oracle(inputs)
    assert out["tax_allowance"] == pytest.approx([400.0, 400.0, 200.0, 0.0])  # the cap bites
    assert out["tax_wdv_close"] == pytest.approx([600.0, 200.0, 0.0, 0.0])
    assert formulas_follow_oracle(SL, inputs)  # the cap is in the formulas, not only the oracle


def test_the_pool_never_goes_negative():
    inputs = case([100.0, 0.0, 0.0, 0.0], [1.0] * 4, 1.0, 0.0)
    for m in MODULES:
        assert min(m.oracle(inputs)["tax_wdv_close"]) >= 0.0
        assert formulas_follow_oracle(m, inputs)
    # straight line also holds at a rate above 1, because it caps at the pool
    over = case([100.0, 0.0, 0.0, 0.0], [1.0] * 4, 1.5, 0.0)
    assert min(SL.oracle(over)["tax_wdv_close"]) >= 0.0 and formulas_follow_oracle(SL, over)


@pytest.mark.parametrize("m", MODULES, ids=lambda m: m.name)
def test_negative_control_a_wrong_oracle_fails_criterion_2(m):
    def off_by_one(inputs):
        out = m.oracle(inputs)
        return {**out, "tax_allowance": [v + 1.0 for v in out["tax_allowance"]]}

    assert "2" in {f.criterion for f in acceptance.check_module(replace(m, oracle=off_by_one))}


@pytest.mark.parametrize("m", MODULES, ids=lambda m: m.name)
def test_negative_control_no_checks_fails_criterion_4(m):
    broken = replace(m, checks=lambda ctx: {})
    assert "4" in {f.criterion for f in acceptance.check_module(broken, {"4"})}
