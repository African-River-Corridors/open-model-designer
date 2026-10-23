"""M10: cover ratios."""

from dataclasses import replace

import pytest  # noqa: F401

from omd import acceptance
from omd.modules.cover_ratios import MODULE as M


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
        "cfads": [120.0, 120.0, 120.0, 120.0],
        "debt_service": [100.0, 100.0, 100.0, 100.0],
        "debt_closing": [300.0, 200.0, 100.0, 0.0],
        "loan_life_flag": [1.0] * 4,
        "discount_rate": 0.0,
        "opening_debt": 400.0,
    }
    return {**base, **kw}


def test_dscr_is_cfads_over_debt_service_and_a_nil_denominator_reads_zero():
    out = M.oracle(case(debt_service=[100.0, 60.0, 0.0, 100.0], cfads=[150.0, 120.0, 90.0, 80.0]))
    assert out["dscr"] == pytest.approx([1.5, 2.0, 0.0, 0.8])
    assert follows(case(debt_service=[100.0, 60.0, 0.0, 100.0]))


def test_rolling_dscr_uses_the_last_two_periods_and_a_shorter_window_at_the_start():
    out = M.oracle(
        case(cfads=[100.0, 200.0, 300.0, 400.0], debt_service=[100.0, 100.0, 100.0, 100.0])
    )
    assert out["dscr_rolling"] == pytest.approx([1.0, 1.5, 2.5, 3.5])


def test_llcr_at_a_zero_rate_is_remaining_cfads_over_debt_at_the_start_of_the_period():
    out = M.oracle(case())
    assert out["llcr"] == pytest.approx(
        [480.0 / 400.0, 360.0 / 300.0, 240.0 / 200.0, 120.0 / 100.0]
    )
    assert out["plcr"] == out["llcr"]  # loan life = project life here
    assert follows(case())


def test_llcr_discounts_each_period_at_the_period_rate():
    inputs = case(
        discount_rate=0.1, cfads=[110.0, 121.0, 0.0, 0.0], loan_life_flag=[1.0, 1.0, 0.0, 0.0]
    )
    out = M.oracle(inputs)
    assert out["llcr"][0] == pytest.approx((110.0 / 1.1 + 121.0 / 1.21) / 400.0)
    assert follows(inputs)


def test_plcr_runs_past_the_loan_life_while_llcr_stops_at_it():
    inputs = case(loan_life_flag=[1.0, 1.0, 0.0, 0.0])
    out = M.oracle(inputs)
    assert out["plcr"][0] > out["llcr"][0]
    assert out["llcr"][0] == pytest.approx(240.0 / 400.0)
    assert follows(inputs)


def test_a_repaid_loan_has_no_cover_ratio():
    out = M.oracle(case(opening_debt=0.0, debt_closing=[0.0] * 4))
    assert out["llcr"] == [0.0] * 4 and out["plcr"] == [0.0] * 4


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def undiscounted(inputs):
        return M.oracle({**inputs, "discount_rate": 0.0})

    assert "2" in {
        f.criterion for f in acceptance.check_module(replace(M, oracle=undiscounted), {"2"})
    }


GOLDEN_2 = {  # independent hand calculation, docs/golden-cases/cover_ratios_2.answer.md
    "cfads": [400.0, 380.0, 360.0, 340.0],
    "debt_service": [250.0, 250.0, 645.116, 0.0],
    "debt_closing": [810.0, 608.6, 0.0, 0.0],
    "loan_life_flag": [1.0, 1.0, 1.0, 0.0],
    "discount_rate": 0.06,
    "opening_debt": 1000.0,
}
GOLDEN_2_OUT = {
    "dscr": [1.6, 1.52, 0.5580391743500394, 0.0],
    "dscr_rolling": [
        1.6,
        1.56,
        0.8267084936477507,
        0.0,
    ],  # coordinator's ruling: 0 once no debt is outstanding
    "llcr": [1.0178200796630776, 0.8381349190652619, 0.5580391743500394, 0.0],
    "plcr": [1.2871319251640045, 1.1905677045356107, 1.0552438894417933, 0.0],
}


def test_second_golden_case_loan_life_shorter_than_project_life_and_a_repaid_loan():
    got = M.oracle(GOLDEN_2)
    for name, want in GOLDEN_2_OUT.items():
        assert got[name] == pytest.approx(want, rel=1e-12), name
    assert (
        acceptance._compare(
            M, GOLDEN_2, {k: list(v) for k, v in GOLDEN_2_OUT.items()}, "3", "golden case"
        )
        == []
    )


def test_the_rolling_dscr_reads_zero_in_a_period_with_no_debt_outstanding():
    # the literal ratio in period 4 would be 700 / 645.116 = 1.085; the module reads 0
    assert M.oracle(GOLDEN_2)["dscr_rolling"][3] == 0.0
