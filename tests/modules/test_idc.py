"""M7: interest during construction."""

from dataclasses import replace

import pytest  # noqa: F401

from omd import acceptance
from omd.modules.idc import MODULE as M


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
        "debt_funded_capex": [100.0, 0.0, 0.0, 0.0],
        "capital_additions": [100.0, 0.0, 0.0, 0.0],
        "idc_rate": 0.1,
        "idc_weight": 0.0,
        "opening_debt": 0.0,
    }
    return {**base, **kw}


def test_weight_zero_charges_interest_on_the_opening_balance_only():
    out = M.oracle(case(opening_debt=200.0))
    assert out["idc_capitalised"][0] == pytest.approx(
        20.0
    )  # 10% of 200, the draw earns nothing yet
    assert out["debt_closing"][0] == pytest.approx(320.0)
    assert follows(case(opening_debt=200.0))


def test_weight_one_charges_on_the_closing_balance_and_solves_the_circularity():
    inputs = case(idc_weight=1.0)
    i = M.oracle(inputs)["idc_capitalised"][0]
    assert i == pytest.approx(0.1 * (100.0 + i))  # i = 100 x 0.1 / 0.9
    assert i == pytest.approx(100.0 / 9.0)
    assert follows(inputs)


def test_average_balance_interest_satisfies_its_circular_definition():
    inputs = case(
        debt_funded_capex=[500.0, 1000.0, 800.0, 200.0], capital_additions=[700.0] * 4,
        idc_weight=0.5, idc_rate=0.03, opening_debt=50.0,
    )  # fmt: skip
    out = M.oracle(inputs)
    debt = 50.0
    for draw, i in zip(inputs["debt_funded_capex"], out["idc_capitalised"], strict=True):
        assert i == pytest.approx(0.03 * (debt + 0.5 * (draw + i)))
        debt += draw + i
    assert out["debt_closing"][-1] == pytest.approx(debt)
    assert follows(inputs)


def test_idc_joins_the_asset_cost_and_the_debt_balance_equally():
    inputs = case(idc_weight=0.5, capital_additions=[130.0, 0.0, 0.0, 0.0])
    out = M.oracle(inputs)
    assert out["capital_additions_incl_idc"][0] - 130.0 == pytest.approx(out["idc_capitalised"][0])
    assert out["debt_closing"][0] - 100.0 == pytest.approx(out["idc_capitalised"][0])


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def ignores_the_circularity(inputs):  # interest on the average balance, circularity not solved
        out = M.oracle({**inputs, "idc_weight": 0.0})
        return out

    bad = replace(M, oracle=ignores_the_circularity)
    assert "2" in {f.criterion for f in acceptance.check_module(bad, {"2"})}
