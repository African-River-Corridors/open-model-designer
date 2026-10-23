"""M9: senior debt repayment (linear, annuity, sculpted)."""

from dataclasses import replace

import pytest

from omd import acceptance
from omd.modules.debt_repay_annuity import MODULE as ANN
from omd.modules.debt_repay_linear import MODULE as LIN
from omd.modules.debt_repay_sculpted import MODULE as SCU

MODULES = [LIN, ANN, SCU]
IDS = [m.name for m in MODULES]


def follows(m, inputs):
    return acceptance._compare(m, inputs, m.oracle(inputs), "2", "case") == []


@pytest.mark.parametrize("m", MODULES, ids=IDS)
def test_criterion_3_the_golden_case_comes_from_an_independent_hand_calculation(m):
    assert acceptance.check_module(m, {"3"}) == []
    assert (
        m.golden.kind == "hand-calculation"
        and "reviewer agent that did not see the code" in m.golden.source
    )


def test_linear_repays_equal_instalments_and_interest_falls_with_the_balance():
    inputs = {
        "repayment_flag": [1.0] * 4,
        "interest_rate": 0.1,
        "opening_debt": 400.0,
        "repayment_periods": 4.0,
    }
    out = LIN.oracle(inputs)
    assert out["debt_repayment"] == [100.0] * 4 and out["debt_closing"] == [
        300.0,
        200.0,
        100.0,
        0.0,
    ]
    assert out["interest"] == pytest.approx([40.0, 30.0, 20.0, 10.0])
    assert follows(LIN, inputs)


def test_annuity_service_is_level_and_clears_the_debt():
    inputs = {
        "repayment_flag": [1.0] * 4,
        "interest_rate": 0.1,
        "opening_debt": 1000.0,
        "repayment_periods": 4.0,
    }
    out = ANN.oracle(inputs)
    assert max(out["debt_service"]) - min(out["debt_service"]) < 1e-9
    assert out["debt_closing"][-1] == pytest.approx(0.0, abs=1e-9)
    assert follows(ANN, inputs)


def test_sculpted_debt_service_is_cfads_over_the_target_dscr():
    inputs = {"repayment_flag": [1.0] * 4, "interest_rate": 0.05, "opening_debt": 300.0,
              "cfads": [100.0, 110.0, 120.0, 130.0], "target_dscr": 1.25}  # fmt: skip
    out = SCU.oracle(inputs)
    for cf, ds in zip(inputs["cfads"], out["debt_service"], strict=True):
        assert ds == pytest.approx(cf / 1.25) or ds < cf / 1.25  # equals, or capped by the balance
    assert out["debt_service"][0] == pytest.approx(80.0)
    assert follows(SCU, inputs)


def test_sculpted_cfads_below_interest_repays_nothing_not_a_negative():
    inputs = {"repayment_flag": [1.0] * 4, "interest_rate": 0.2, "opening_debt": 500.0,
              "cfads": [50.0, 50.0, 50.0, 50.0], "target_dscr": 1.0}  # fmt: skip
    out = SCU.oracle(inputs)
    assert out["debt_repayment"] == [0.0] * 4
    assert follows(SCU, inputs)


@pytest.mark.parametrize("m", [LIN, ANN], ids=["linear", "annuity"])
def test_no_repayment_where_the_flag_is_zero_and_never_more_than_the_balance(m):
    inputs = {
        "repayment_flag": [0.0, 1.0, 1.0, 1.0],
        "interest_rate": 0.05,
        "opening_debt": 90.0,
        "repayment_periods": 1.0,
    }
    out = m.oracle(inputs)
    assert out["debt_repayment"][0] == 0.0 and min(out["debt_closing"]) >= 0.0
    assert follows(m, inputs)


@pytest.mark.parametrize("m", MODULES, ids=IDS)
def test_negative_control_a_wrong_oracle_fails_criterion_2(m):
    def off(inputs):
        out = m.oracle(inputs)
        return {**out, "debt_repayment": [v + 1.0 for v in out["debt_repayment"]]}

    assert "2" in {f.criterion for f in acceptance.check_module(replace(m, oracle=off), {"2"})}


@pytest.mark.parametrize("m", MODULES, ids=IDS)
def test_negative_control_without_checks_fails_criterion_4(m):
    bad = replace(m, checks=lambda ctx: {})
    assert "4" in {f.criterion for f in acceptance.check_module(bad, {"4"})}
