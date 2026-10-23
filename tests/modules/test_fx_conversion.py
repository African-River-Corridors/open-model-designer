"""M15: FX conversion."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.fx_conversion import MODULE as M


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
        "fx_start_rate": 0.1,
        "fx_depreciation": [0.0] * 4,
        "flow_local": [100.0, 200.0, 300.0, 400.0],
        "opening_balance_local": 0.0,
    }
    return {**base, **kw}


def test_a_flat_rate_converts_flows_and_balances_at_the_same_rate_with_no_translation_difference():
    out = M.oracle(case(opening_balance_local=50.0))
    assert out["fx_closing_rate"] == pytest.approx([0.1] * 4)
    assert out["flow_reporting"] == pytest.approx([10.0, 20.0, 30.0, 40.0])
    assert out["balance_closing_reporting"] == pytest.approx([15.0, 35.0, 65.0, 105.0])
    assert out["fx_translation_difference"] == pytest.approx([0.0] * 4)
    assert follows(case(opening_balance_local=50.0))


def test_the_rate_compounds_and_the_period_rate_sits_between_opening_and_closing():
    out = M.oracle(case(fx_depreciation=[0.1, 0.1, 0.1, 0.1]))
    assert out["fx_closing_rate"] == pytest.approx([0.09, 0.081, 0.0729, 0.06561])
    assert out["fx_period_rate"][0] == pytest.approx(0.095)
    assert follows(case(fx_depreciation=[0.1, 0.1, 0.1, 0.1]))


def test_an_appreciation_raises_the_rate():
    out = M.oracle(case(fx_depreciation=[-0.1, 0.0, 0.0, 0.0]))
    assert out["fx_closing_rate"][0] == pytest.approx(0.11)
    assert follows(case(fx_depreciation=[-0.1, 0.0, 0.0, 0.0]))


def test_a_depreciating_currency_makes_a_loss_on_a_positive_local_balance():
    inputs = case(fx_depreciation=[0.1] * 4, opening_balance_local=1000.0, flow_local=[0.0] * 4)
    out = M.oracle(inputs)
    assert all(d < 0 for d in out["fx_translation_difference"])
    assert follows(inputs)


def test_the_converted_balance_reconciles_to_opening_plus_converted_flows_plus_differences():
    inputs = case(
        fx_start_rate=0.08,
        fx_depreciation=[0.1, 0.05, 0.0, -0.04],
        flow_local=[1000.0, -400.0, 600.0, 250.0],
        opening_balance_local=500.0,
    )
    out = M.oracle(inputs)
    run = 500.0 * 0.08
    for i in range(4):
        run += out["flow_reporting"][i] + out["fx_translation_difference"][i]
        assert out["balance_closing_reporting"][i] == pytest.approx(run)


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def converts_flows_at_closing(inputs):
        out = M.oracle(inputs)
        return {
            **out,
            "flow_reporting": [
                f * r for f, r in zip(inputs["flow_local"], out["fx_closing_rate"], strict=True)
            ],
        }

    bad = replace(M, oracle=converts_flows_at_closing)
    assert "2" in {f.criterion for f in acceptance.check_module(bad, {"2"})}
