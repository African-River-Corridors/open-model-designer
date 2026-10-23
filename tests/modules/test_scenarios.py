"""M23: scenarios and sensitivities."""

import os
import tempfile
from dataclasses import replace

import pytest

from omd import acceptance
from omd.harness._eval import cell, evaluate_cells
from omd.modules.scenarios import (
    _MULT,
    DEFAULT_DRIVERS,
    DEFAULT_SCENARIOS,
    EXAMPLE,
    GOLDEN_INPUTS,
    _apply,
    _toy,
    make_scenarios,
    run_points,
)
from omd.modules.scenarios import (
    MODULE as M,
)


def follows(m, inputs):
    return acceptance._compare(m, inputs, m.oracle(inputs), "2", "case") == []


def test_criterion_3_the_golden_case_comes_from_an_independent_hand_calculation():
    assert acceptance.check_module(M, {"3"}) == []
    assert (
        M.golden.kind == "hand-calculation"
        and "reviewer agent that did not see the code" in M.golden.source
    )


def test_negative_control_without_checks_fails_criterion_4():
    bad = replace(M, checks=lambda ctx: {})
    assert "4" in {f.criterion for f in acceptance.check_module(bad, {"4"})}


def points(selector=2, step=0.1):
    return run_points(
        _toy, {"price": 1.0, "volume": 1.0, "capex": 1.0}, _apply, DEFAULT_DRIVERS,
        DEFAULT_SCENARIOS, _MULT, step, lambda o: o["result"], selector,
    )  # fmt: skip


def test_run_points_runs_the_model_once_per_point_and_the_live_point_is_the_selected_scenario():
    p = points(selector=2)
    assert p["base_result"] == pytest.approx(40.0)  # 100 + 30 - 90
    assert p["result_up__price"] == pytest.approx(50.0) and p[
        "result_down__capex"
    ] == pytest.approx(49.0)
    assert p["scenario_result__downside"] == pytest.approx(100 * 0.9 * 0.8 + 30 * 0.8 - 90 * 1.2)
    assert p["live_result"] == p["scenario_result__downside"]


def test_a_live_model_that_matches_the_table_reconciles_to_nil():
    out = M.oracle(points(selector=3))
    assert out["live_reconciliation"] == pytest.approx([0.0] * 4)
    assert out["live_multiplier__volume"] == pytest.approx([1.1] * 4)
    assert follows(M, points(selector=3))


def test_the_selected_scenario_drives_the_live_multipliers():
    out = M.oracle(points(selector=2))
    assert [out[f"live_multiplier__{d}"][0] for d in DEFAULT_DRIVERS] == [0.9, 0.8, 1.2]
    assert follows(M, points(selector=2))


def test_the_tornado_ranks_the_largest_swing_first_and_equal_swings_share_a_rank():
    out = M.oracle(EXAMPLE)
    swings = {d: out[f"swing__{d}"][0] for d in DEFAULT_DRIVERS}
    ranks = {d: out[f"tornado_rank__{d}"][0] for d in DEFAULT_DRIVERS}
    assert sorted(ranks.values()) == [1.0, 2.0, 3.0]
    assert max(swings, key=swings.get) == "volume" and ranks["volume"] == 1.0
    tied = {
        **EXAMPLE,
        "result_up__capex": 40.0 + 20.0,
        "result_down__capex": 40.0 - 20.0,
        "result_up__price": 60.0,
        "result_down__price": 20.0,
    }
    out2 = M.oracle(tied)
    assert out2["swing__capex"][0] == out2["swing__price"][0] == 40.0
    assert out2["tornado_rank__capex"][0] == out2["tornado_rank__price"][0] == 1.0
    assert out2["tornado_rank__volume"][0] == 3.0
    assert follows(M, tied)


def test_breakeven_is_where_the_straight_line_through_up_and_down_crosses_nil():
    out = M.oracle(EXAMPLE)
    # price: result 40 at 1.0, slope 100 per unit of multiplier -> nil at 1 - 40/100
    assert out["breakeven_multiplier__price"][0] == pytest.approx(0.6)
    assert out["breakeven_multiplier__capex"][0] == pytest.approx(
        1 + 40 / 90
    )  # falling line: capex up lowers the result


def test_a_driver_with_no_swing_has_breakeven_zero_not_an_error():
    flat = {**EXAMPLE, "result_up__capex": 40.0, "result_down__capex": 40.0}
    out = M.oracle(flat)
    assert out["swing__capex"][0] == 0.0 and out["breakeven_multiplier__capex"][0] == 0.0
    assert follows(M, flat)


def _check_value(inputs, name):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "m.xlsx")
        calcs, _ctx, spec, (first, last) = acceptance._host(M, inputs, path)
        values = evaluate_cells(path, ("Calcs",))
        ws = calcs.ws
        row = next(
            r
            for r in range(first, last)
            if str(ws.cell(row=r, column=1).value or "").strip().startswith(spec[name].strip())
        )
        return cell(values, "Calcs", f"C{row}")


def test_the_reconciliation_check_is_green_when_the_live_model_agrees_and_red_when_it_does_not():
    ok = points(selector=2)
    assert _check_value(ok, "reconciled") == pytest.approx(0.0)
    off = {**ok, "live_result": ok["live_result"] + 3.5}
    assert _check_value(off, "reconciled") == pytest.approx(3.5)


def test_scenarios_and_drivers_are_configured_not_coded():
    two = make_scenarios(("a", "b"), ("lo", "hi"))
    inputs = {
        "scenario_selector": 2.0, "sensitivity_step": 0.1, "base_result": 10.0, "live_result": 12.0,
        "multiplier__a__lo": 0.9, "multiplier__a__hi": 1.1, "multiplier__b__lo": 0.8, "multiplier__b__hi": 1.2,
        "scenario_result__lo": 5.0, "scenario_result__hi": 12.0,
        "result_down__a": 8.0, "result_up__a": 12.0, "result_down__b": 9.0, "result_up__b": 10.0,
    }  # fmt: skip
    out = two.oracle(inputs)
    assert (
        out["live_multiplier__b"][0] == 1.2
        and out["tornado_rank__a"][0] == 1.0
        and out["tornado_rank__b"][0] == 2.0
    )
    assert follows(two, inputs)


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def ranks_smallest_first(inputs):
        out = M.oracle(inputs)
        return {**out, "tornado_rank__volume": [4.0 - r for r in out["tornado_rank__volume"]]}

    bad = replace(M, oracle=ranks_smallest_first)
    assert "2" in {f.criterion for f in acceptance.check_module(bad, {"2"})}


CASE_1 = {  # scenarios.answer.md: upside live, the live model reads 70 against the table's 74.25
    **GOLDEN_INPUTS, "scenario_selector": 3.0, "live_result": 70.0,
}  # fmt: skip
CASE_2 = {  # scenarios_2.answer.md: downside live, zero swing on price, tied swings on volume and capex
    **GOLDEN_INPUTS, "scenario_selector": 2.0, "live_result": -5.0,
    "result_down__price": 40.0, "result_up__price": 40.0, "result_down__volume": 30.0,
    "result_up__volume": 50.0, "result_down__capex": 50.0, "result_up__capex": 30.0,
}  # fmt: skip


def test_case_1_hand_calculation_the_reconciliation_is_red_at_minus_4_25():
    out = M.oracle(CASE_1)
    assert out["live_multiplier__price"][0] == 1.05 and out["live_scenario_result"][0] == 74.25
    assert out["live_reconciliation"] == pytest.approx([-4.25] * 4)
    assert [out[f"tornado_rank__{d}"][0] for d in DEFAULT_DRIVERS] == [2.0, 1.0, 3.0]
    assert out["breakeven_multiplier__volume"][0] == pytest.approx(9 / 13)
    assert _check_value(CASE_1, "reconciled") == pytest.approx(4.25)  # the check reads red


def test_case_2_hand_calculation_zero_swing_tied_ranks_and_the_reconciliation_red_at_4():
    out = M.oracle(CASE_2)
    assert [out[f"live_multiplier__{d}"][0] for d in DEFAULT_DRIVERS] == [0.85, 0.9, 1.25]
    assert out["live_scenario_result"][0] == -9.0 and out["live_reconciliation"][
        0
    ] == pytest.approx(4.0)
    assert [out[f"swing__{d}"][0] for d in DEFAULT_DRIVERS] == [0.0, 20.0, 20.0]
    assert [out[f"tornado_rank__{d}"][0] for d in DEFAULT_DRIVERS] == [
        3.0,
        1.0,
        1.0,
    ]  # competition ranking
    assert [out[f"breakeven_multiplier__{d}"][0] for d in DEFAULT_DRIVERS] == pytest.approx(
        [0.0, 0.6, 1.4]
    )
    assert [out[f"no_sensitivity__{d}"][0] for d in DEFAULT_DRIVERS] == [1.0, 0.0, 0.0]
    assert _check_value(CASE_2, "reconciled") == pytest.approx(4.0)
    assert follows(M, CASE_1) and follows(M, CASE_2)


def test_a_zero_breakeven_can_be_told_from_a_real_one_by_the_no_sensitivity_flag():
    out = M.oracle(CASE_2)
    assert out["breakeven_multiplier__price"][0] == 0.0 and out["no_sensitivity__price"][0] == 1.0
    real = M.oracle(GOLDEN_INPUTS)
    assert all(real[f"no_sensitivity__{d}"][0] == 0.0 for d in DEFAULT_DRIVERS)
