"""M12: lock-up and default tests."""

from dataclasses import replace

import pytest  # noqa: F401

from omd import acceptance
from omd.modules.lockup import MODULE as M


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
        "dscr": [1.5, 1.5, 1.5, 1.5],
        "debt_outstanding_flag": [1.0] * 4,
        "lockup_dscr": 1.2,
        "default_dscr": 1.05,
    }
    return {**base, **kw}


def test_a_healthy_dscr_locks_nothing_and_permits_distributions():
    out = M.oracle(case())
    assert out["lockup_flag"] == [0.0] * 4 and out["distributions_permitted_flag"] == [1.0] * 4
    assert follows(case())


def test_below_the_lockup_threshold_distributions_stop_and_below_the_default_threshold_it_is_a_default():
    inputs = case(dscr=[1.5, 1.1, 1.0, 1.3])
    out = M.oracle(inputs)
    assert out["lockup_flag"] == [0.0, 1.0, 1.0, 0.0]
    assert out["default_flag"] == [0.0, 0.0, 1.0, 0.0]
    assert out["distributions_permitted_flag"] == [1.0, 0.0, 0.0, 1.0]
    assert follows(inputs)


def test_the_tests_are_off_where_no_debt_is_outstanding():
    inputs = case(dscr=[0.0, 0.0, 0.5, 0.5], debt_outstanding_flag=[0.0, 0.0, 1.0, 0.0])
    out = M.oracle(inputs)
    assert out["lockup_flag"] == [0.0, 0.0, 1.0, 0.0] and out["default_flag"] == [
        0.0,
        0.0,
        1.0,
        0.0,
    ]
    assert follows(inputs)


def test_a_dscr_exactly_at_the_threshold_passes():
    assert M.oracle(case(dscr=[1.2] * 4))["lockup_flag"] == [0.0] * 4


def test_inverted_thresholds_make_the_default_check_read_nonzero():
    import os
    import tempfile

    from omd.harness._eval import cell, evaluate_cells

    bad = case(dscr=[1.1] * 4, lockup_dscr=1.0, default_dscr=1.2)  # default above lock-up
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "m.xlsx")
        calcs, ctx, spec, _ = acceptance._host(M, bad, path)
        row = next(
            r
            for r in range(1, 80)
            if str(calcs.ws.cell(row=r, column=1).value or "")
            .strip()
            .startswith("Check - flags re-derived")
        )
        assert cell(evaluate_cells(path, ("Calcs",)), "Calcs", f"C{row}") == 1.0


def test_negative_control_a_wrong_oracle_fails_criterion_2():
    def strict(inputs):  # "at or below" instead of "below"
        return M.oracle({**inputs, "lockup_dscr": inputs["lockup_dscr"] + 0.5})

    assert "2" in {f.criterion for f in acceptance.check_module(replace(M, oracle=strict), {"2"})}


def test_the_first_hand_calculation_is_kept_as_an_extra_case():
    inputs = {
        "dscr": [1.6, 1.25, 1.15, 0.95],
        "debt_outstanding_flag": [1.0, 1.0, 1.0, 1.0],
        "lockup_dscr": 1.3,
        "default_dscr": 1.1,
    }
    assert M.oracle(inputs) == {
        "lockup_flag": [0.0, 1.0, 1.0, 1.0],
        "default_flag": [0.0, 0.0, 0.0, 1.0],
        "distributions_permitted_flag": [1.0, 0.0, 0.0, 0.0],
    }


def test_a_module_that_ignores_the_debt_flag_fails_the_golden_case():
    def ignores_flag(inputs):
        return M.oracle({**inputs, "debt_outstanding_flag": [1.0] * 4})

    assert "3" in {
        f.criterion for f in acceptance.check_module(replace(M, oracle=ignores_flag), {"3"})
    }
