"""M1: fixed assets, book."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.fixed_assets import MODULE as M


def case(**kw):
    base = {
        "capital_additions": [0.0] * 4,
        "use_fraction": [1.0] * 4,
        "useful_life": 4.0,
        "opening_gross": 0.0,
        "opening_accum_depreciation": 0.0,
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


def test_straight_line_charge_is_cost_over_life_and_nbv_stops_at_nil():
    inputs = case(opening_gross=1000.0, useful_life=2.0)
    out = M.oracle(inputs)
    assert out["depreciation"] == [500.0, 500.0, 0.0, 0.0]
    assert out["fa_nbv_closing"] == [500.0, 0.0, 0.0, 0.0]
    assert follows(inputs)  # the floor is in the formulas, not only the oracle


def test_cost_waits_before_first_use():
    inputs = case(capital_additions=[400.0, 0.0, 0.0, 0.0], use_fraction=[0.0, 0.0, 1.0, 1.0])
    out = M.oracle(inputs)
    assert out["depreciation"] == [0.0, 0.0, 100.0, 100.0]
    assert out["fa_gross_closing"] == [400.0] * 4
    assert follows(inputs)


def test_additions_join_the_gross_roll_forward_and_a_part_period_depreciates_part():
    inputs = case(capital_additions=[0.0, 400.0, 0.0, 0.0], use_fraction=[1.0, 0.5, 1.0, 1.0])
    out = M.oracle(inputs)
    assert out["fa_gross_closing"] == [0.0, 400.0, 400.0, 400.0]
    assert out["depreciation"][1] == pytest.approx(50.0)  # half of 400 / 4
    assert follows(inputs)


def test_nbv_equals_gross_less_accumulated_depreciation():
    out = M.oracle(M.example)
    for g, a, n in zip(
        out["fa_gross_closing"],
        out["fa_accum_depreciation_closing"],
        out["fa_nbv_closing"],
        strict=True,
    ):
        assert n == pytest.approx(g - a) and n >= 0.0


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def no_floor(inputs):
        return M.oracle({**inputs, "useful_life": 1e9})

    assert "2" in {f.criterion for f in acceptance.check_module(replace(M, oracle=no_floor), {"2"})}


def test_negative_control_without_checks_fails_criterion_4():
    bad = replace(M, checks=lambda ctx: {})
    assert "4" in {f.criterion for f in acceptance.check_module(bad, {"4"})}
