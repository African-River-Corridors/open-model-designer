"""returns_irr (#15): XIRR for flows that change sign more than once, as a new module (returns is write-once)."""

from __future__ import annotations

import pytest

from omd import template
from omd.modules import returns, returns_irr
from omd.template import Step

ENDS_NEGATIVE = {**returns_irr.MODULE.golden.inputs}


def test_the_released_module_fails_on_flows_that_end_negative():
    with pytest.raises(ValueError, match="no sign change"):
        returns.MODULE.oracle({k: v for k, v in ENDS_NEGATIVE.items() if k != "irr_guess"})


def test_every_irr_is_found_and_the_one_nearest_the_guess_is_reported():
    flows = ENDS_NEGATIVE["project_cash_flow"]
    dates = ENDS_NEGATIVE["flow_dates"]
    found = returns_irr.irrs(flows, dates)
    assert found == pytest.approx([-0.469805004289280, 0.115335033314822], abs=1e-9)
    assert returns_irr.xirr_near(flows, dates, 0.1) == pytest.approx(0.115335033314822, abs=1e-9)
    assert returns_irr.xirr_near(flows, dates, -0.5) == pytest.approx(-0.469805004289280, abs=1e-9)


def test_a_conventional_flow_has_one_sign_change_and_a_unique_irr():
    out = returns_irr.MODULE.oracle(
        {**ENDS_NEGATIVE, "project_cash_flow": [-1000.0, 0.0, 500.0, 700.0]}
    )
    assert out["project_sign_changes"][0] == 1.0 and out["project_irr_unique"][0] == 1.0
    assert out["equity_irr_unique"][0] == 0.0


def test_the_workbook_finds_the_same_irr_from_the_same_guess():
    m = returns_irr.MODULE
    step = Step(m, {p.name: f"ext:{p.name}" for p in m.inputs})
    comp = template.compose([step], dict(ENDS_NEGATIVE), "IRR")
    assert template.evaluate_and_compare(comp) == []
