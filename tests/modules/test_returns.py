"""M21: returns and valuation."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.returns import MODULE as M
from omd.modules.returns import xirr


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
        "project_cash_flow": [-1000.0, 0.0, 0.0, 1331.0],
        "equity_cash_flow": [-100.0, 50.0, 50.0, 50.0],
        "flow_dates": [0.0, 365.0, 730.0, 1095.0],
        "project_discount_rate": 0.1,
        "equity_discount_rate": 0.1,
        "days_per_year": 365.0,
    }
    return {**base, **kw}


def test_xirr_of_a_flow_that_compounds_at_ten_percent_is_ten_percent():
    assert xirr([-1000.0, 0.0, 0.0, 1331.0], [0.0, 365.0, 730.0, 1095.0]) == pytest.approx(0.1)
    assert M.oracle(case())["project_xirr"] == pytest.approx([0.1] * 4)
    assert follows(case())


def test_npv_at_the_xirr_is_nil_and_below_it_is_positive():
    out = M.oracle(case())
    assert out["project_npv"] == pytest.approx([0.0] * 4, abs=1e-9)  # discount rate = XIRR
    lower = M.oracle(case(project_discount_rate=0.05))
    assert lower["project_npv"][0] > 0
    assert follows(case(project_discount_rate=0.05))


def test_xirr_follows_the_dates_not_just_the_order():
    quick = M.oracle(case(flow_dates=[0.0, 100.0, 200.0, 300.0]))
    assert quick["project_xirr"][0] > M.oracle(case())["project_xirr"][0]
    assert follows(case(flow_dates=[0.0, 100.0, 200.0, 300.0]))


def test_payback_is_the_first_period_cumulative_equity_cash_is_non_negative():
    out = M.oracle(case(equity_cash_flow=[-100.0, 60.0, 60.0, 60.0]))
    assert out["equity_cumulative_cash"] == pytest.approx([-100.0, -40.0, 20.0, 80.0])
    assert out["equity_payback_period"] == [3.0] * 4
    assert follows(case(equity_cash_flow=[-100.0, 60.0, 60.0, 60.0]))


def test_payback_is_zero_when_equity_is_never_repaid():
    inputs = case(
        equity_cash_flow=[-100.0, 30.0, 30.0, 30.0],
        project_cash_flow=[-1000.0, 400.0, 400.0, 400.0],
    )
    out = M.oracle(inputs)
    assert out["equity_payback_period"] == [0.0] * 4
    assert follows(inputs)


def test_flows_with_no_sign_change_have_no_xirr():
    with pytest.raises(ValueError):
        M.oracle(case(project_cash_flow=[100.0, 100.0, 100.0, 100.0]))


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def uses_the_project_rate_for_equity(inputs):
        return M.oracle({**inputs, "equity_discount_rate": inputs["project_discount_rate"]})

    bad = replace(M, oracle=uses_the_project_rate_for_equity)
    assert "2" in {f.criterion for f in acceptance.check_module(bad, {"2"})}


EXTRA_HAND_CASES = [  # independent hand calculations kept as extra tests (docs/golden-cases/returns_{2,3}.answer.md)
    (
        [-500.0, 200.0, 300.0, 100.0],
        {
            "equity_xirr": 0.10587176417269295,
            "equity_npv": -33.61799724365798,
            "equity_cumulative_cash": [-500.0, -300.0, 0.0, 100.0],
            "equity_payback_period": 3.0,  # cumulative exactly 0 counts as paid back
        },
    ),
    (
        [-500.0, 100.0, 100.0, 100.0],
        {
            "equity_xirr": -0.21712003427321935,
            "equity_npv": -271.8032524421458,
            "equity_cumulative_cash": [-500.0, -400.0, -300.0, -200.0],
            "equity_payback_period": 0.0,  # never paid back
        },
    ),
]


@pytest.mark.parametrize("equity,want", EXTRA_HAND_CASES)
def test_the_oracle_matches_the_extra_hand_calculations(equity, want):
    inputs = {**M.golden.inputs, "equity_cash_flow": equity}
    got = M.oracle(inputs)
    for name, value in want.items():
        expected = value if isinstance(value, list) else [value] * 4
        assert got[name] == pytest.approx(expected, rel=1e-7), name
    assert got["project_xirr"] == pytest.approx(M.golden.outputs["project_xirr"])


def test_the_sheet_agrees_on_the_exactly_zero_payback_case():
    assert follows({**M.golden.inputs, "equity_cash_flow": [-500.0, 200.0, 300.0, 100.0]})
