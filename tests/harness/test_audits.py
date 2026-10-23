"""The read-back audits. Each has a clean case that passes and a corrupted case that fails."""

import pytest
import toy

from omd.harness.audit_checks import corruption_audit, status_checks, value_checks
from omd.harness.audit_fast import audit_fast
from omd.harness.audit_inputs import audit_inputs
from omd.harness.readchecks import read_status_checks, read_zero_checks


@pytest.fixture(scope="module")
def model(tmp_path_factory):
    d = tmp_path_factory.mktemp("m")
    return toy.build(str(d / "toy.xlsx")), d


@pytest.fixture(scope="module")
def broken(model):
    """The model with revenue scaled +25% in its last period: the check must notice."""
    src, d = model
    r = toy.row_of(src, "Revenue ($)")
    return toy.corrupt(src, str(d / "broken.xlsx"), "Calcs", f"F{r}")


def quiet(*_a, **_k):
    pass


# --- readchecks -------------------------------------------------------------------------------
def test_status_checks_pass_on_clean(model):
    assert read_status_checks(model[0], min_rows=2, out=quiet) == 0


def test_status_checks_fail_on_corrupted(broken):
    assert read_status_checks(broken, min_rows=2, out=quiet) == 1


def test_status_checks_known_open_is_tolerated_only_by_name(broken):
    assert read_status_checks(broken, min_rows=2, known_open={"Revenue re-derived"}, out=quiet) == 0
    assert read_status_checks(broken, min_rows=2, known_open={"another"}, out=quiet) == 1


def test_zero_checks_pass_on_clean(model):
    assert read_zero_checks(model[0], min_rows=2, out=quiet) == 0


def test_zero_checks_fail_on_corrupted(broken):
    assert read_zero_checks(broken, min_rows=2, out=quiet) == 1


def test_zero_checks_refuse_a_block_that_is_too_small(model):
    with pytest.raises(AssertionError, match="almost nothing"):
        read_zero_checks(model[0], min_rows=5, out=quiet)


# --- corruption audit -------------------------------------------------------------------------
def test_corruption_audit_catches_a_watched_row_by_value_check(model):
    src = model[0]
    fired = value_checks(src, {"revenue": ("Check — revenue re-derived", lambda v: abs(v) > 1.0)})
    res = corruption_audit(src, ["Revenue ($)"], fired, out=quiet)
    assert res.caught == {"Revenue ($)": ["revenue"]} and res.ok


def test_corruption_audit_catches_a_watched_row_by_status_check(model):
    src = model[0]
    res = corruption_audit(src, ["Revenue ($)"], status_checks(src), out=quiet)
    assert res.caught == {"Revenue ($)": ["Revenue re-derived"]}


def test_corruption_audit_goes_red_on_a_row_no_check_watches(model):
    """Negative control: tax has no check, so the audit must report it uncaught."""
    src = model[0]
    fired = value_checks(src, {"revenue": ("Check — revenue re-derived", lambda v: abs(v) > 1.0)})
    res = corruption_audit(src, ["Revenue ($)", "Tax ($)"], fired, out=quiet)
    assert res.uncaught == ["Tax ($)"] and not res.ok


def test_corruption_audit_reports_a_missing_row(model):
    src = model[0]
    res = corruption_audit(src, ["No such row"], status_checks(src), out=quiet)
    assert res.missing == ["No such row"] and not res.ok


def test_corruption_audit_ignores_checks_already_firing_on_the_clean_book(broken):
    """A check that is red before the corruption is not evidence that the corruption was caught."""
    res = corruption_audit(broken, ["Tax ($)"], status_checks(broken), out=quiet)
    assert res.baseline_fired == ["Revenue re-derived"]
    assert res.uncaught == ["Tax ($)"]


# --- inputs audit -----------------------------------------------------------------------------
KW = dict(inputs_sheet="Inputs", watched_sheets=("Calcs", "Summary"), gate_label="Unit price")


def test_inputs_audit_flags_an_input_that_moves_nothing(model):
    """Negative control: 'Dead input' is read by no formula, so it is a defect until declared."""
    res = audit_inputs(model[0], **KW, gate_min_rows=2, out=quiet)
    assert [lab for _r, lab, _v in res.undeclared] == ["Dead input"] and not res.ok


def test_inputs_audit_passes_when_the_dead_input_is_declared(model):
    res = audit_inputs(model[0], **KW, declared={"Dead input"}, gate_min_rows=2, out=quiet)
    assert res.ok and len(res.inert) == 1 and res.n_inputs == 3


def test_inputs_audit_stops_when_the_sanity_gate_cannot_see_a_known_change(model):
    with pytest.raises(AssertionError, match="ORACLE BROKEN"):
        audit_inputs(model[0], **KW, gate_min_rows=500, out=quiet)


def test_inputs_audit_refuses_a_misnamed_inputs_sheet(model):
    with pytest.raises(AssertionError, match="no 'Assumptions' tab"):
        audit_inputs(model[0], **{**KW, "inputs_sheet": "Assumptions"}, out=quiet)


# --- FAST audit -------------------------------------------------------------------------------
def test_fast_audit_is_clean_on_the_toy_model(model):
    res = audit_fast(model[0], first_col=3, out=quiet)
    assert res.findings == {} and res.ok
    assert res.n_periods == 4


def test_fast_audit_goes_red_on_an_npv_and_an_embedded_constant(model):
    src, d = model
    r = toy.row_of(src, "Revenue ($)")
    import openpyxl

    path = str(d / "npv.xlsx")
    w = openpyxl.load_workbook(src)
    w["Calcs"][f"D{r}"] = f"=NPV(0.1,C{r}:F{r})*37"
    w.save(path)
    res = audit_fast(path, first_col=3, out=quiet)
    assert "4.01-02 NPV function used (never allowed)" in res.findings
    assert "3.04-01 embedded constants" in res.findings
    assert not res.ok


def test_fast_audit_accepts_a_declared_breach_but_still_lists_it(model):
    src, d = model
    r = toy.row_of(src, "Revenue ($)")
    import openpyxl

    path = str(d / "npv2.xlsx")
    w = openpyxl.load_workbook(src)
    w["Calcs"][f"D{r}"] = f"=NPV(0.1,C{r}:F{r})"
    w.save(path)
    lines = []
    plain = audit_fast(path, first_col=3, out=quiet)
    res = audit_fast(
        path,
        first_col=3,
        declared={("4.01-02", "Revenue ($)"): "checked by hand 2026-10-22"},
        out=lines.append,
    )
    assert "4.01-02 NPV function used (never allowed)" in res.findings
    assert any("[DECLARED]" in line for line in lines)
    assert plain.undeclared - res.undeclared == 1


# --- F2: an audit that tested nothing is not a pass --------------------------------------------------
def test_an_audit_that_skipped_every_target_is_not_ok(model):
    """A wrong first column reads empty cells, so every row looks zero and is skipped."""
    src = model[0]
    fired = value_checks(src, {"revenue": ("Check — revenue re-derived", lambda v: abs(v) > 1.0)})
    res = corruption_audit(src, ["Revenue ($)"], fired, first_col=8, n_periods=4, out=quiet)
    assert res.skipped == ["Revenue ($)"] and res.caught == {} and not res.ok


def test_an_audit_with_a_huge_magnitude_floor_is_not_ok(model):
    src = model[0]
    res = corruption_audit(src, ["Revenue ($)"], status_checks(src), min_magnitude=1e9, out=quiet)
    assert not res.ok


def test_an_audit_with_no_targets_is_not_ok(model):
    src = model[0]
    assert not corruption_audit(src, [], status_checks(src), out=quiet).ok


def test_an_audit_is_not_ok_when_a_check_is_already_red_on_the_clean_book(broken):
    res = corruption_audit(broken, ["Revenue ($)"], status_checks(broken), out=quiet)
    assert res.baseline_fired and not res.ok


def test_a_good_audit_is_still_ok(model):
    src = model[0]
    res = corruption_audit(src, ["Revenue ($)"], status_checks(src), out=quiet)
    assert res.ok and res.caught


def test_the_gates_still_fire_without_assert(model):
    """The gates raise; they are not `assert` statements that python -O removes."""
    import inspect

    from omd.harness import audit_checks, audit_inputs, readchecks

    for mod in (audit_checks, audit_inputs, readchecks):
        lines = [x for x in inspect.getsource(mod).splitlines() if x.strip().startswith("assert ")]
        assert lines == [], mod.__name__
