"""M22: three statements."""

import os
import tempfile
from dataclasses import replace

import pytest

from omd import acceptance
from omd.harness._eval import cell, evaluate_cells
from omd.modules.three_statements import MODULE as M


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


def test_a_consistent_case_balances_in_every_period():
    out = M.oracle(M.example)
    assert out["balance_difference"] == pytest.approx([0.0] * 4)
    assert out["total_assets"] == pytest.approx(out["total_liabilities_equity"])


def test_the_statements_tie_to_each_other():
    out = M.oracle(M.example)
    for i in range(4):
        assert out["net_cash_flow"][i] == pytest.approx(
            out["cash_from_operations"][i]
            + out["cash_from_investing"][i]
            + out["cash_from_financing"][i]
        )
    cash = M.example["opening_cash"]
    for i in range(4):
        cash += out["net_cash_flow"][i]
        assert out["cash_closing"][i] == pytest.approx(cash)
    assert out["net_income"][0] == pytest.approx(500 - 250 - 70 - 45 - 25)


def test_a_fixed_asset_balance_that_ignores_its_flows_unbalances_the_sheet():
    bad = {**M.example, "fa_nbv_closing": [x + 7.0 for x in M.example["fa_nbv_closing"]]}
    out = M.oracle(bad)
    assert out["balance_difference"] == pytest.approx([7.0] * 4)


def test_an_unbalanced_opening_sheet_carries_through_every_period():
    bad = {**M.example, "opening_cash": M.example["opening_cash"] + 3.0}
    assert M.oracle(bad)["balance_difference"] == pytest.approx([3.0] * 4)


def _check_row_values(inputs):
    """Build the workbook on `inputs` and read the balance check row as the sheet evaluates it."""
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "m.xlsx")
        calcs, _ctx, spec, (first, last) = acceptance._host(M, inputs, path)
        values = evaluate_cells(path, ("Calcs",))
        ws = calcs.ws
        row = next(
            r
            for r in range(first, last)
            if str(ws.cell(row=r, column=1).value or "").strip().startswith(spec["balance"].strip())
        )
        return [cell(values, "Calcs", f"{c}{row}") for c in acceptance.PERIOD_COLS]


def test_the_articulation_check_is_green_when_balanced_and_red_when_not():
    assert _check_row_values(M.example) == pytest.approx([0.0] * 4)
    bad = {**M.example, "debt_closing": [x + 5.0 for x in M.example["debt_closing"]]}
    assert _check_row_values(bad) == pytest.approx([5.0] * 4)
    assert follows(bad)  # the sheet still agrees with the oracle: both show the 5.0 difference


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def drops_the_tax_payable_movement(inputs):
        out = M.oracle(inputs)
        return {
            **out,
            "cash_from_operations": [
                x - t
                for x, t in zip(out["cash_from_operations"], inputs["tax_charge"], strict=True)
            ],
        }

    bad = replace(M, oracle=drops_the_tax_payable_movement)
    assert "2" in {f.criterion for f in acceptance.check_module(bad, {"2"})}


def test_the_golden_case_misstates_two_balances_and_the_check_reads_red_in_those_periods_only():
    assert M.golden.outputs["balance_difference"] == [0.0, -10.0, 10.0, 0.0]
    assert _check_row_values(M.golden.inputs) == pytest.approx([0.0, 10.0, 10.0, 0.0])


def test_the_first_hand_calculation_a_balanced_case_is_kept_as_an_extra_test():
    from omd.modules.three_statements import CASE_1

    out = M.oracle(CASE_1)
    assert out["balance_difference"] == pytest.approx([0.0] * 4)
    assert out["total_assets"] == pytest.approx([1510.0, 1682.0, 1816.0, 1962.0])
    assert out["cash_closing"] == pytest.approx([310.0, 522.0, 746.0, 997.0])
    assert out["retained_earnings_closing"] == pytest.approx([402.0, 596.0, 802.0, 1040.0])
    assert follows(CASE_1)
