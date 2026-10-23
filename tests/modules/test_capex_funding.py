"""M6: capex profile and funding split."""

from dataclasses import replace

import pytest  # noqa: F401

from omd import acceptance
from omd.modules.capex_funding import MODULE as M


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
        "total_capex": 1000.0,
        "spend_profile": [0.25] * 4,
        "development_cost": [0.0] * 4,
        "debt_share": 0.5,
    }
    return {**base, **kw}


def test_spend_follows_the_profile_and_funding_splits_by_the_debt_share():
    out = M.oracle(case(spend_profile=[0.4, 0.3, 0.2, 0.1], debt_share=0.7))
    assert out["capital_additions"] == pytest.approx([400.0, 300.0, 200.0, 100.0])
    assert out["debt_funded_capex"] == pytest.approx([280.0, 210.0, 140.0, 70.0])
    assert out["equity_contribution"] == pytest.approx([120.0, 90.0, 60.0, 30.0])
    assert follows(case(spend_profile=[0.4, 0.3, 0.2, 0.1], debt_share=0.7))


def test_development_cost_is_equity_funded_and_added_to_capital_additions():
    inputs = case(development_cost=[50.0, 0.0, 20.0, 0.0])
    out = M.oracle(inputs)
    assert out["capital_additions"][0] == 300.0 and out["debt_funded_capex"][0] == 125.0
    assert out["equity_contribution"][0] == 175.0 and out["equity_contribution"][2] == 145.0
    assert follows(inputs)


def test_debt_plus_equity_equals_capital_additions():
    out = M.oracle(case(development_cost=[10.0, 20.0, 30.0, 40.0], debt_share=0.35))
    for d, e, c in zip(
        out["debt_funded_capex"], out["equity_contribution"], out["capital_additions"], strict=True
    ):
        assert d + e == pytest.approx(c)


def test_zero_and_full_debt_share():
    assert M.oracle(case(debt_share=0.0))["debt_funded_capex"] == [0.0] * 4
    assert M.oracle(case(debt_share=1.0))["equity_contribution"] == [0.0] * 4
    assert follows(case(debt_share=1.0))


def test_a_profile_that_does_not_sum_to_one_makes_the_profile_check_read_nonzero():
    import os
    import tempfile

    from omd.harness._eval import cell, evaluate_cells

    bad = case(spend_profile=[0.25, 0.25, 0.25, 0.3])
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "m.xlsx")
        calcs, ctx, spec, _ = acceptance._host(M, bad, path)
        row = next(
            r
            for r in range(1, 60)
            if str(calcs.ws.cell(row=r, column=1).value or "")
            .strip()
            .startswith("Check - spend profile")
        )
        v = evaluate_cells(path, ("Calcs",))
        assert abs(cell(v, "Calcs", f"F{row}") - 0.05) < 1e-9


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def ignores_dev(inputs):
        return M.oracle({**inputs, "development_cost": [0.0] * 4})

    assert "2" in {
        f.criterion for f in acceptance.check_module(replace(M, oracle=ignores_dev), {"2"})
    }
