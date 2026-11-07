"""compose: a real horizon, real period labels, a style profile, and two instances of one module (#6, #7)."""

from __future__ import annotations

import dataclasses

import pytest

from omd import template
from omd.harness import fastblock
from omd.modules import cfads, debt_repay_linear
from omd.template import Step

YEARS = ["2027", "2028", "2029", "2030", "2031", "2032"]


def _cfads_step():
    return Step(cfads.MODULE, {p.name: f"ext:{p.name}" for p in cfads.MODULE.inputs})


def _cfads_inputs():
    return {
        "revenue": [0.0, 100.0, 120.0, 130.0, 140.0, 150.0],
        "operating_cost": [0.0, 40.0, 42.0, 44.0, 46.0, 48.0],
        "working_capital_movement": [0.0, 5.0, 2.0, 1.0, 1.0, -9.0],
        "tax_paid": [0.0, 0.0, 9.0, 12.0, 13.0, 14.0],
    }


def test_compose_takes_a_horizon_labels_and_a_style():
    comp = template.compose(
        [_cfads_step()], _cfads_inputs(), "Six years", periods=YEARS, style="plain"
    )
    assert len(comp.wb.period_cols) == 6
    ws = comp.calcs.ws
    assert [ws[f"{c}2"].value for c in comp.wb.period_cols] == YEARS
    assert comp.wb.style.name == "plain"
    assert template.evaluate_and_compare(comp) == []


def test_compose_defaults_are_unchanged():
    ins = {k: v[:4] for k, v in _cfads_inputs().items()}
    comp = template.compose([_cfads_step()], ins, "Default")
    ws = comp.calcs.ws
    assert [ws[f"{c}2"].value for c in comp.wb.period_cols] == ["P1", "P2", "P3", "P4"]
    assert comp.wb.style.name == "omd-default"


def test_a_series_of_the_wrong_length_is_refused():
    with pytest.raises(ValueError, match="has 4 values; the model has 6 periods"):
        ins = {**_cfads_inputs(), "revenue": [0.0, 1.0, 2.0, 3.0]}
        template.compose([_cfads_step()], ins, "Bad", periods=YEARS)


def test_two_instances_of_one_module_build_side_by_side():
    """Two loans from one repayment module: same block titles, different module names."""
    a = dataclasses.replace(debt_repay_linear.MODULE, name="loan_a")
    b = dataclasses.replace(debt_repay_linear.MODULE, name="loan_b")
    ext = {
        "flag": [0.0, 1.0, 1.0, 1.0],
        "rate_a": 0.05,
        "debt_a": 900.0,
        "rate_b": 0.08,
        "debt_b": 300.0,
    }
    steps = [
        Step(
            a,
            {
                "repayment_flag": "ext:flag",
                "interest_rate": "ext:rate_a",
                "opening_debt": "ext:debt_a",
            },
        ),
        Step(
            b,
            {
                "repayment_flag": "ext:flag",
                "interest_rate": "ext:rate_b",
                "opening_debt": "ext:debt_b",
            },
        ),
    ]
    comp = template.compose(steps, ext, "Two loans")
    assert template.evaluate_and_compare(comp) == []
    rows = comp.calcs.rows()
    assert rows["loan_a.debt_closing"] != rows["loan_b.debt_closing"]
    nodes = [k for k in fastblock.TREE.nodes if "::" in k]
    assert any(k.startswith("loan_a/") for k in nodes) and any(
        k.startswith("loan_b/") for k in nodes
    )
