"""M16: working capital."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.working_capital import MODULE as M


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
        "revenue": [900.0, 900.0, 900.0, 900.0],
        "operating_cost": [450.0, 450.0, 450.0, 450.0],
        "receivable_days": 30.0,
        "payable_days": 0.0,
        "cash_buffer_days": 0.0,
        "days_in_period": 90.0,
        "opening_working_capital": 0.0,
    }
    return {**base, **kw}


def test_receivables_are_days_of_revenue_and_use_cash_when_they_build():
    out = M.oracle(case())
    assert out["receivables"] == pytest.approx([300.0] * 4)
    assert out["working_capital_movement"] == pytest.approx([300.0, 0.0, 0.0, 0.0])
    assert follows(case())


def test_payables_fund_working_capital_and_make_it_negative():
    out = M.oracle(case(receivable_days=0.0, payable_days=45.0))
    assert out["payables"] == pytest.approx([225.0] * 4)
    assert out["working_capital"] == pytest.approx([-225.0] * 4)
    assert out["working_capital_movement"][0] == pytest.approx(-225.0)
    assert follows(case(receivable_days=0.0, payable_days=45.0))


def test_a_cash_buffer_is_days_of_cost_and_is_not_part_of_working_capital():
    inputs = case(receivable_days=0.0, cash_buffer_days=18.0)
    out = M.oracle(inputs)
    assert out["cash_buffer"] == pytest.approx([90.0] * 4)
    assert out["working_capital"] == pytest.approx([0.0] * 4)
    assert out["working_capital_movement"] == pytest.approx([0.0] * 4)
    assert follows(inputs)


def test_falling_revenue_releases_cash_and_the_opening_balance_sets_the_first_movement():
    inputs = case(revenue=[900.0, 600.0, 300.0, 0.0], opening_working_capital=100.0)
    out = M.oracle(inputs)
    assert out["working_capital_movement"] == pytest.approx([200.0, -100.0, -100.0, -100.0])
    assert follows(inputs)


def test_movements_sum_to_the_change_in_working_capital():
    inputs = case(
        revenue=[900.0, 1300.0, 700.0, 1100.0],
        payable_days=20.0,
        cash_buffer_days=5.0,
        opening_working_capital=40.0,
    )
    out = M.oracle(inputs)
    assert 40.0 + sum(out["working_capital_movement"]) == pytest.approx(out["working_capital"][-1])


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def forgets_the_buffer(inputs):
        return M.oracle({**inputs, "cash_buffer_days": 0.0})

    bad = replace(M, oracle=forgets_the_buffer)
    assert "2" in {f.criterion for f in acceptance.check_module(bad, {"2"})}
