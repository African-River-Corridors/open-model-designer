"""M14: subordinated / shareholder loan."""

from dataclasses import replace

import pytest  # noqa: F401

from omd import acceptance
from omd.modules.sub_loan import MODULE as M


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
        "sub_drawdown": [0.0] * 4,
        "sub_repayment_request": [0.0] * 4,
        "sub_interest_rate": 0.1,
        "sub_pik_share": 0.0,
        "opening_sub_loan": 1000.0,
    }
    return {**base, **kw}


def test_cash_pay_interest_leaves_the_balance_unchanged():
    out = M.oracle(case())
    assert out["sub_interest"] == [100.0] * 4 and out["sub_interest_cash"] == [100.0] * 4
    assert out["sub_closing"] == [1000.0] * 4
    assert follows(case())


def test_full_pik_capitalises_interest_and_compounds():
    out = M.oracle(case(sub_pik_share=1.0))
    assert out["sub_interest_pik"][0] == pytest.approx(100.0)
    assert out["sub_closing"] == pytest.approx([1100.0, 1210.0, 1331.0, 1464.1])
    assert out["sub_interest_cash"] == pytest.approx([0.0] * 4)
    assert follows(case(sub_pik_share=1.0))


def test_part_pik_splits_interest_between_cash_and_the_balance():
    out = M.oracle(case(sub_pik_share=0.4))
    assert out["sub_interest_pik"][0] == pytest.approx(40.0) and out["sub_interest_cash"][
        0
    ] == pytest.approx(60.0)


def test_repayment_is_capped_at_the_balance_and_the_loan_can_be_cleared():
    inputs = case(sub_repayment_request=[0.0, 400.0, 5000.0, 100.0])
    out = M.oracle(inputs)
    assert out["sub_repayment"] == [0.0, 400.0, 600.0, 0.0]
    assert out["sub_closing"] == [1000.0, 600.0, 0.0, 0.0]
    assert follows(inputs)


def test_drawdowns_add_to_the_balance_and_earn_interest_from_the_next_period():
    inputs = case(sub_drawdown=[500.0, 0.0, 0.0, 0.0], opening_sub_loan=0.0)
    out = M.oracle(inputs)
    assert out["sub_interest"][0] == 0.0 and out["sub_interest"][1] == pytest.approx(50.0)
    assert follows(inputs)


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def no_pik(inputs):
        return M.oracle({**inputs, "sub_pik_share": 0.0})

    assert M.example["sub_pik_share"] > 0
    assert "2" in {f.criterion for f in acceptance.check_module(replace(M, oracle=no_pik), {"2"})}
