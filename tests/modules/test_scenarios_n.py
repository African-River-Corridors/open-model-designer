"""scenarios_n (#14): the scenarios logic for any horizon, as a new module (the released one is write-once)."""

from __future__ import annotations

import pytest

from omd import template
from omd.modules import scenarios, scenarios_n
from omd.template import Step


def test_the_default_instance_agrees_with_the_released_module():
    want = scenarios.MODULE.oracle(scenarios.MODULE.example)
    assert scenarios_n.MODULE.oracle(scenarios_n.MODULE.example) == want


def test_sixty_monthly_periods_build_and_reproduce_the_oracle():
    m = scenarios_n.make_scenarios_n(periods=60, example=scenarios_n.MODULE.example)
    step = Step(m, {p.name: f"ext:{p.name}" for p in m.inputs})
    comp = template.compose(
        [step], dict(m.example), "Sixty", periods=[f"M{i}" for i in range(1, 61)]
    )
    assert len(comp.wb.period_cols) == 60
    assert all(len(v) == 60 for v in comp.expected["scenarios_n"].values())
    assert template.evaluate_and_compare(comp) == []


def test_a_horizon_mismatch_is_refused():
    m = scenarios_n.make_scenarios_n(periods=12, example=scenarios_n.MODULE.example)
    step = Step(m, {p.name: f"ext:{p.name}" for p in m.inputs})
    with pytest.raises(ValueError, match="made for 12 periods; the workbook has 4"):
        template.compose([step], dict(m.example), "Mismatch")
