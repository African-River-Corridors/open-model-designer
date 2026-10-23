"""T5: assumptions carry provenance, a missing source fails loudly, a case changes only what it names."""

import datetime as dt
from pathlib import Path

import pytest
import yaml

from omd import assumptions as A
from omd.assumptions import AssumptionsError
from omd.sheet.workbook import Workbook
from omd.timeline import Timeline, TimelineError

DATA = Path(__file__).parent / "data"
MODEL = DATA / "toy_model.yaml"


@pytest.fixture
def base():
    return A.load_assumptions(MODEL)


def doc():
    return yaml.safe_load(MODEL.read_text())


# --- provenance ------------------------------------------------------------------------------
def test_a_complete_file_loads_with_every_field(base):
    a = base["unit_price"]
    assert (a.value, a.unit, a.label, a.source, a.who, a.estimate) == (
        12.5, "USD/tonne", "Unit price", "Supplier quote Q-104", "A. Person", False
    )  # fmt: skip
    assert a.date == dt.date(2026, 9, 30)
    assert base["volume"].estimate is True


@pytest.mark.parametrize("blank", [None, "", "   "])
def test_a_missing_source_fails_the_build_and_names_the_key(blank):
    d = doc()
    d["assumptions"]["volume"]["source"] = blank
    with pytest.raises(AssumptionsError) as e:
        A.build_set(d)
    assert e.value.problems == ["volume: missing source"]


def test_a_source_key_that_is_absent_fails():
    d = doc()
    del d["assumptions"]["tax_rate"]["source"]
    with pytest.raises(AssumptionsError, match="tax_rate: missing source"):
        A.build_set(d)


def test_the_real_file_with_one_source_line_removed_fails(tmp_path):
    """Negative control on the file itself: delete one `source:` line and the build goes red."""
    text = MODEL.read_text()
    assert "    source: Operating plan v2\n" in text
    broken = tmp_path / "broken.yaml"
    broken.write_text(text.replace("    source: Operating plan v2\n", ""))
    A.load_assumptions(MODEL)  # the unbroken file passes
    with pytest.raises(AssumptionsError, match="volume: missing source"):
        A.load_assumptions(broken)


@pytest.mark.parametrize("field", A.FIELDS)
def test_every_field_is_required(field):
    d = doc()
    del d["assumptions"]["volume"][field]
    with pytest.raises(AssumptionsError, match=f"volume: missing {field}"):
        A.build_set(d)


def test_every_problem_is_reported_at_once():
    d = doc()
    del d["assumptions"]["volume"]["source"]
    d["assumptions"]["tax_rate"]["who"] = ""
    d["assumptions"]["unit_price"]["value"] = "twelve"
    with pytest.raises(AssumptionsError) as e:
        A.build_set(d)
    assert len(e.value.problems) == 3


def test_bad_types_and_unknown_fields_fail():
    d = doc()
    d["assumptions"]["volume"]["estimate"] = "yes"
    d["assumptions"]["tax_rate"]["colour"] = "red"
    d["assumptions"]["unit_price"]["date"] = "last Tuesday"
    with pytest.raises(AssumptionsError) as e:
        A.build_set(d)
    text = " | ".join(e.value.problems)
    assert "estimate must be true or false" in text
    assert "unknown field" in text and "not an ISO date" in text


def test_a_repeated_yaml_key_is_refused():
    with pytest.raises(AssumptionsError, match="duplicate key"):
        A.load_yaml("assumptions:\n  a: 1\n  a: 2\n")


def test_unknown_top_level_key_is_refused():
    d = doc()
    d["assumption"] = {}
    with pytest.raises(AssumptionsError, match="unknown top-level"):
        A.build_set(d)


# --- cases -----------------------------------------------------------------------------------
def test_a_case_delta_changes_only_the_named_value(base):
    case = A.apply_case(
        base,
        {"case": "high price", "set": {"unit_price": {"value": 14.0, "source": "Quote Q-117"}}},
    )
    assert case["unit_price"].value == 14.0
    assert case["unit_price"].source == "Quote Q-117"
    for key in ("volume", "tax_rate"):
        assert case[key] == base[key]
    assert base["unit_price"].value == 12.5  # the base is not mutated


def test_a_case_can_replace_provenance_with_the_value(base):
    case = A.apply_case(
        base,
        {"set": {"volume": {"value": 9, "source": "Revised plan", "date": "2026-10-20"}}},
    )
    v = case["volume"]
    assert (v.value, v.source, v.date, v.who) == (
        9.0,
        "Revised plan",
        dt.date(2026, 10, 20),
        "B. Person",
    )


def test_a_case_may_not_name_a_key_the_base_lacks(base):
    with pytest.raises(AssumptionsError, match="'discount' is not an assumption"):
        A.apply_case(base, {"set": {"discount": 0.1}})


def test_a_case_may_not_blank_a_source(base):
    with pytest.raises(AssumptionsError, match="unit_price: missing source"):
        A.apply_case(base, {"set": {"unit_price": {"value": 14, "source": ""}}})


def test_a_case_file_loads(base, tmp_path):
    p = tmp_path / "case.yaml"
    p.write_text("case: low volume\nset:\n  volume: {value: 5, source: Revised plan}\n")
    assert A.load_case(base, p)["volume"].value == 5.0


def test_a_case_with_no_changes_is_refused(base):
    with pytest.raises(AssumptionsError):
        A.apply_case(base, {"set": {}})


# --- standard assumptions: inherit at a pinned date, show overrides --------------------------------
def test_inheritance_picks_the_value_that_held_on_the_pinned_date():
    s = A.load_assumptions(DATA / "toy_inheriting.yaml")
    assert s["inflation"].value == 0.04  # from 2026-07-01 holds on 2026-08-01
    early = A.load_yaml((DATA / "toy_inheriting.yaml").read_text())
    early["inherit"]["as_of"] = "2026-01-01"
    assert A.build_set(early, base_dir=DATA)["inflation"].value == 0.03


def test_a_pin_before_the_first_date_fails():
    d = A.load_yaml((DATA / "toy_inheriting.yaml").read_text())
    d["inherit"]["as_of"] = "2020-01-01"
    with pytest.raises(AssumptionsError, match="no value holds on 2020-01-01"):
        A.build_set(d, base_dir=DATA)


def test_an_override_is_shown_and_an_untouched_inherited_value_is_not():
    s = A.load_assumptions(DATA / "toy_inheriting.yaml")
    assert [o.key for o in s.overrides] == ["unit_price"]
    o = s.overrides[0]
    assert (o.standard_value, o.value) == (10.0, 12.5)
    assert "unit_price: standard 10 (Library price list) -> 12.5 (Supplier quote Q-104)" in (
        s.override_report()
    )
    assert "inflation" in s.inherited and "unit_price" not in s.inherited


def test_a_standard_entry_without_a_source_fails_too():
    d = yaml.safe_load((DATA / "toy_standard.yaml").read_text())
    d["standard"]["inflation"][0]["source"] = ""
    with pytest.raises(AssumptionsError, match="missing source"):
        A.StandardSet.parse(d)


def test_the_pin_is_required():
    d = A.load_yaml((DATA / "toy_inheriting.yaml").read_text())
    del d["inherit"]["as_of"]
    with pytest.raises(AssumptionsError, match="as_of"):
        A.build_set(d, base_dir=DATA)


# --- timeline --------------------------------------------------------------------------------
def test_the_timeline_block_sets_the_periods(base):
    t = base.timeline
    assert (t.periodicity, t.periods, t.start) == ("monthly", 24, dt.date(2027, 1, 1))
    assert t.labels()[0] == "2027-01" and t.labels()[-1] == "2028-12"
    assert t.period_end(0) == dt.date(2027, 1, 31) and t.period_end(23) == dt.date(2028, 12, 31)


def test_quarterly_and_annual_labels():
    q = Timeline.from_mapping(
        {"periodicity": "quarterly", "start": "2027-04-01", "horizon_years": 1}
    )
    assert q.labels() == ["2027-Q2", "2027-Q3", "2027-Q4", "2028-Q1"]
    assert q.period_end(3) == dt.date(2028, 3, 31)
    a = Timeline.from_mapping(
        {"periodicity": "annual", "start": "2027-01-01", "horizon_periods": 3}
    )
    assert a.labels() == ["2027", "2028", "2029"]


@pytest.mark.parametrize(
    "block, message",
    [
        ({"periodicity": "weekly", "start": "2027-01-01", "horizon_periods": 4}, "weekly"),
        ({"periodicity": "monthly", "start": "2027-01-15", "horizon_periods": 4}, "first day"),
        ({"periodicity": "quarterly", "start": "2027-02-01", "horizon_periods": 4}, "quarter"),
        ({"periodicity": "annual", "start": "2027-03-01", "horizon_periods": 4}, "1 January"),
        ({"periodicity": "monthly", "start": "2027-01-01"}, "exactly one"),
        (
            {
                "periodicity": "monthly",
                "start": "2027-01-01",
                "horizon_periods": 4,
                "horizon_years": 1,
            },
            "exactly one",
        ),
        ({"periodicity": "monthly", "start": "2027-01-01", "horizon_periods": 0}, ">= 1"),
        ({"periodicity": "monthly", "start": "soon", "horizon_periods": 4}, "ISO date"),
        ({"periodicity": "monthly", "horizon_periods": 4}, "needs 'start'"),
        (
            {"periodicity": "monthly", "start": "2027-01-01", "horizon_periods": 4, "x": 1},
            "unknown",
        ),
    ],
)
def test_a_bad_timeline_fails(block, message):
    with pytest.raises(TimelineError, match=message):
        Timeline.from_mapping(block)


# --- into a workbook -------------------------------------------------------------------------
def test_the_assumptions_land_on_the_inputs_sheet_with_provenance(base):
    wb = Workbook("T", base.timeline.labels(), opening=True)
    refs = A.write_inputs(wb, base)
    ws = wb.inputs_sheet
    row = int(refs["volume"].rsplit("$", 1)[1])
    assert ws.cell(row=row, column=1).value == "Volume (tonne/month)"
    assert ws.cell(row=row, column=2).value == 8.0
    assert [ws.cell(row=row, column=c).value for c in (3, 4, 5, 6, 7)] == [
        "tonne/month", "Operating plan v2", "2026-10-01", "B. Person", "ESTIMATE",
    ]  # fmt: skip
    row = int(refs["tax_rate"].rsplit("$", 1)[1])
    assert ws.cell(row=row, column=7).value is None  # not an estimate
    assert len(wb.period_cols) == 24


# --- review F3: a case may not keep a source that never said the new number -------------------------
def test_a_changed_value_with_no_new_source_is_refused(base):
    with pytest.raises(AssumptionsError, match="must give its own source"):
        A.apply_case(base, {"set": {"unit_price": 14.0}})
    with pytest.raises(AssumptionsError, match="must give its own source"):
        A.apply_case(base, {"set": {"unit_price": {"value": 14.0}}})


def test_a_case_may_repeat_the_old_source_only_if_the_value_is_unchanged(base):
    same = A.apply_case(base, {"set": {"unit_price": {"value": 12.5, "who": "E. Person"}}})
    assert same["unit_price"].who == "E. Person" and same["unit_price"].value == 12.5


def test_a_case_over_an_inherited_key_is_shown_as_an_override():
    inh = A.load_assumptions(DATA / "toy_inheriting.yaml")
    assert "inflation" in inh.inherited and [o.key for o in inh.overrides] == ["unit_price"]
    case = A.apply_case(inh, {"set": {"inflation": {"value": 0.25, "source": "Stress test"}}})
    assert case["inflation"].source == "Stress test"
    assert [o.key for o in case.overrides] == ["unit_price", "inflation"]
    o = case.overrides[1]
    assert (o.standard_value, o.value, o.source) == (0.04, 0.25, "Stress test")
    assert "inflation: standard 0.04 (Central bank outlook 2026) -> 0.25 (Stress test)" in (
        case.override_report()
    )
    assert "inflation" not in case.inherited
    assert "inflation" in inh.inherited  # the base is not changed


def test_a_case_over_an_existing_override_keeps_the_standard_value():
    inh = A.load_assumptions(DATA / "toy_inheriting.yaml")
    case = A.apply_case(inh, {"set": {"unit_price": {"value": 15.0, "source": "Stress test"}}})
    (o,) = case.overrides
    assert (o.standard_value, o.standard_source, o.value) == (10.0, "Library price list", 15.0)


@pytest.mark.parametrize("junk", ["TBC", "-", "n/a", "  tbd "])
def test_a_placeholder_is_not_a_source(junk):
    d = doc()
    d["assumptions"]["volume"]["source"] = junk
    with pytest.raises(AssumptionsError, match="volume: missing source"):
        A.build_set(d)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf")])
def test_nan_and_infinity_are_not_values(bad):
    d = doc()
    d["assumptions"]["volume"]["value"] = bad
    with pytest.raises(AssumptionsError, match="finite number"):
        A.build_set(d)
