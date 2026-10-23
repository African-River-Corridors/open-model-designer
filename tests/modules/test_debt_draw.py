"""M8: senior debt, draw to need."""

from dataclasses import replace

import pytest  # noqa: F401

from omd import acceptance
from omd.modules.debt_draw import MODULE as M


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
        "funding_need": [100.0, 100.0, 100.0, 100.0],
        "availability_flag": [1.0] * 4,
        "facility_limit": 1000.0,
        "opening_debt": 0.0,
    }
    return {**base, **kw}


def test_draws_meet_the_need_when_there_is_headroom():
    out = M.oracle(case())
    assert out["debt_drawdown"] == [100.0] * 4 and out["funding_gap"] == [0.0] * 4
    assert follows(case())


def test_the_commitment_caps_the_draw_and_the_shortfall_shows_as_a_gap():
    inputs = case(facility_limit=250.0)
    out = M.oracle(inputs)
    assert out["debt_drawdown"] == [100.0, 100.0, 50.0, 0.0]
    assert out["funding_gap"] == [0.0, 0.0, 50.0, 100.0]
    assert out["debt_closing"] == [100.0, 200.0, 250.0, 250.0]
    assert follows(inputs)


def test_a_shut_window_draws_nothing_and_the_whole_need_is_a_gap():
    inputs = case(availability_flag=[1.0, 0.0, 0.0, 1.0])
    out = M.oracle(inputs)
    assert out["debt_drawdown"] == [100.0, 0.0, 0.0, 100.0]
    assert out["funding_gap"] == [0.0, 100.0, 100.0, 0.0]
    assert follows(inputs)


def test_opening_debt_counts_against_the_commitment():
    inputs = case(opening_debt=950.0)
    out = M.oracle(inputs)
    assert out["debt_drawdown"] == [50.0, 0.0, 0.0, 0.0] and out["debt_closing"][0] == 1000.0
    assert follows(inputs)


def test_drawn_debt_never_exceeds_the_commitment_and_need_equals_draw_plus_gap():
    inputs = case(funding_need=[400.0, 700.0, 50.0, 900.0], facility_limit=900.0)
    out = M.oracle(inputs)
    assert max(out["debt_closing"]) <= 900.0
    for n, d, g in zip(
        inputs["funding_need"], out["debt_drawdown"], out["funding_gap"], strict=True
    ):
        assert n == pytest.approx(d + g)


def test_negative_control_a_plug_instead_of_a_gap_fails_criterion_2():
    def plugs(inputs):  # a model that lets the draw exceed the commitment hides the gap
        return M.oracle({**inputs, "facility_limit": 1e12})

    bad = replace(M, oracle=plugs)
    assert "2" in {f.criterion for f in acceptance.check_module(bad, {"2"})}
