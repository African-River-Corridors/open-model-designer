"""M17: CFADS."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.cfads import MODULE as M


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
        "revenue": [1000.0] * 4,
        "operating_cost": [400.0] * 4,
        "working_capital_movement": [0.0] * 4,
        "tax_paid": [0.0] * 4,
    }
    return {**base, **kw}


def test_cfads_is_revenue_less_costs_before_tax_and_working_capital():
    out = M.oracle(case())
    assert out["cfads_pre_tax"] == [600.0] * 4 and out["cfads"] == [600.0] * 4
    assert follows(case())


def test_a_working_capital_build_uses_cash_and_a_release_adds_to_it():
    inputs = case(working_capital_movement=[100.0, 0.0, -50.0, 0.0])
    out = M.oracle(inputs)
    assert out["cfads"][:3] == [500.0, 600.0, 650.0]
    assert follows(inputs)


def test_tax_comes_off_after_the_pre_tax_figure():
    inputs = case(tax_paid=[0.0, 50.0, 120.0, 0.0])
    out = M.oracle(inputs)
    assert out["cfads_pre_tax"] == [600.0] * 4
    assert out["cfads"] == [600.0, 550.0, 480.0, 600.0]
    assert follows(inputs)


def test_cfads_can_be_negative_before_operations_start():
    inputs = case(revenue=[0.0, 0.0, 500.0, 900.0], operating_cost=[30.0, 20.0, 400.0, 400.0])
    out = M.oracle(inputs)
    assert out["cfads"][:2] == [-30.0, -20.0]
    assert follows(inputs)


def test_cumulative_cfads_reconciles_to_the_components():
    inputs = case(
        working_capital_movement=[10.0, -5.0, 0.0, 20.0], tax_paid=[0.0, 30.0, 30.0, 45.0]
    )
    out = M.oracle(inputs)
    assert sum(out["cfads"]) == pytest.approx(4000.0 - 1600.0 - 25.0 - 105.0)


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def ignores_working_capital(inputs):
        return M.oracle({**inputs, "working_capital_movement": [0.0] * 4})

    bad = replace(M, oracle=ignores_working_capital)
    assert "2" in {f.criterion for f in acceptance.check_module(bad, {"2"})}
