"""M24: the project-finance (single SPV) template builds, agrees with the chained oracle and passes every gate."""

import os
import tempfile
from dataclasses import replace

import pytest

from omd import acceptance, template
from omd.harness._eval import evaluate_cells
from omd.harness.audit_fast import audit_fast
from omd.harness.audit_inputs import audit_inputs
from omd.harness.readchecks import read_zero_checks
from omd.templates import project_finance as pf


@pytest.fixture(scope="module")
def built():
    ext = pf.external()
    return ext, pf.build(ext)


def saved(comp):
    d = tempfile.mkdtemp()
    path = os.path.join(d, "t.xlsx")
    comp.save(path)
    return path


def test_the_workbook_formulas_reproduce_the_chained_oracle_for_every_module_output(built):
    _ext, comp = built
    assert template.evaluate_and_compare(comp) == []
    assert {s.module.name for s in comp.steps} == {
        "capex_funding", "idc", "fixed_assets", "tax_pool_rb", "debt_repay_linear", "tax_losses", "tax_engine", "cfads", "cover_ratios", "dsra", "lockup",
        "cash_sweep_percent", "sub_loan", "vat_account", "working_capital", "distribution_waterfall",
        "take_or_pay", "cash_waterfall", "three_statements", "returns", "fx_conversion",
        "scenarios", "glue_drivers", "glue_pl", "glue_cash", "glue_dist", "glue_book", "glue_ret",
    }  # fmt: skip


def test_the_modules_are_wired_to_each_other_not_to_pasted_numbers(built):
    _ext, comp = built
    calcs = comp.calcs
    row = calcs.rows()["idc.capital_additions_incl_idc"]
    fa_gross = calcs.ws[f"D{calcs.rows()['fixed_assets.fa_gross_closing']}"].value
    assert fa_gross.startswith("=")
    feeds_fa = comp.ctxs["fixed_assets"].source("capital_additions")
    assert feeds_fa == f"Calcs!{{col}}{row}"


def test_the_balance_sheet_balances_and_every_waterfall_claim_is_paid(built):
    _ext, comp = built
    assert all(abs(x) < 1e-6 for x in comp.expected["three_statements"]["balance_difference"])
    assert all(
        abs(x) < 1e-6
        for k, v in comp.expected["cash_waterfall"].items()
        if k.startswith("unpaid")
        for x in v
    )


def test_the_statements_read_the_other_modules_not_pasted_numbers(built):
    _ext, comp = built
    rows = comp.calcs.rows()
    assert (
        comp.ctxs["three_statements"].source("tax_charge")
        == f"Calcs!{{col}}{rows['tax_engine.tax_charge']}"
    )
    assert (
        comp.ctxs["cash_waterfall"].source("cash_available")
        == f"Calcs!{{col}}{rows['glue_cash.cash_receipts']}"
    )
    assert (
        comp.ctxs["returns"].source("equity_cash_flow")
        == f"Calcs!{{col}}{rows['glue_ret.equity_cash_flow']}"
    )


def test_gate_summary_checks_all_read_zero(built):
    _ext, comp = built
    assert read_zero_checks(saved(comp), "Summary", min_rows=30, out=lambda *_: None) == 0
    assert len(comp.check_rows) >= 30


CORRUPTION_SHARDS, DRIVE_SHARDS, INPUT_SHARDS = (
    6,
    4,
    3,
)  # CI runs each shard as its own job (.github/workflows/ci.yml)


def test_the_audit_shards_together_cover_every_row_and_input_once(built):
    ext, comp = built
    rows = [(m, p) for m, outs in comp.expected.items() for p in outs]
    for n in (CORRUPTION_SHARDS, DRIVE_SHARDS, INPUT_SHARDS):
        dealt = [x for i in range(n) for x in template.shard_of(rows, i, n)]
        assert sorted(dealt) == sorted(rows)
        names = list(comp.ext_cells)
        dealt = [x for i in range(n) for x in template.shard_of(names, i, n)]
        assert sorted(dealt) == sorted(names)


@pytest.mark.parametrize(
    "i", range(CORRUPTION_SHARDS), ids=lambda i: f"corruption-{i}of{CORRUPTION_SHARDS}"
)
def test_gate_corruption_audit_is_clean_on_every_module_output(built, i):
    _ext, comp = built
    assert template.corruption_audit(comp, shard=(i, CORRUPTION_SHARDS)) == []


@pytest.mark.parametrize("i", range(DRIVE_SHARDS), ids=lambda i: f"drive-{i}of{DRIVE_SHARDS}")
def test_gate_every_external_input_drives_the_outputs(built, i):
    ext, comp = built
    problems = template.inputs_drive_outputs(
        comp, ext, moves={"spend_profile": lambda v: [x * 1.1 for x in v]}, shard=(i, DRIVE_SHARDS)
    )
    assert problems == []


@pytest.mark.parametrize("i", range(INPUT_SHARDS), ids=lambda i: f"inputs-{i}of{INPUT_SHARDS}")
def test_gate_inputs_audit_finds_no_inert_scalar_input(built, i):
    _ext, comp = built
    audit = audit_inputs(
        saved(comp), inputs_sheet="Inputs", watched_sheets=("Calcs",), gate_label="total_capex",
        gate_min_rows=1, shard=(i, INPUT_SHARDS), out=lambda *_: None,
    )  # fmt: skip
    assert audit.ok and not audit.inert


def test_gate_fast_audit_of_the_composed_book_has_only_the_modules_own_declared_breaches(built):
    """The composed book is audited by the same rule as each module's worked example: check rows are exempt from
    `CHECK_ROW_EXEMPT`, and a calculation-row breach must be one a module declares in `fast_declared`."""
    _ext, comp = built
    raw = audit_fast(saved(comp), first_col=3, out=lambda *_: None)
    declared = [
        tuple(key.partition(" ")[::2]) for st in comp.steps for key in st.module.fast_declared
    ]
    undeclared = []
    for rule, hits in raw.findings.items():
        code = rule.split()[0].split("/")[0]
        for _row, label, _note in hits:
            label = label.strip()
            if label.startswith(acceptance.CHECK_PREFIX) and code in acceptance.CHECK_ROW_EXEMPT:
                continue
            if any(c == code and label.startswith(prefix.strip()) for c, prefix in declared):
                continue
            undeclared.append((rule, label))
    assert undeclared == []
    assert declared  # the modules do declare edge-period rows


def test_the_link_check_reads_red_when_the_term_debt_does_not_open_at_the_construction_debt():
    wrong = pf.external(term_opening_debt=1.0)
    comp = pf.build(wrong)
    path = saved(comp)
    values = evaluate_cells(path, ("Calcs",))
    row = next(r for m, lab, r in comp.check_rows if m == "template")
    assert values[f"CALCS'!D{row}"] > 1.0
    assert read_zero_checks(path, "Summary", min_rows=30, out=lambda *_: None) == 1


def test_negative_control_a_module_with_no_checks_leaves_its_rows_uncovered_and_the_audit_says_so():
    steps = pf.steps()
    ext = pf.external()
    stripped = [
        replace(st, module=replace(st.module, checks=lambda ctx: {}))
        if st.module.name == "dsra"
        else st
        for st in steps
    ]
    comp = template.compose(stripped, ext, "negative control")
    problems = template.corruption_audit(comp, modules={"dsra"})
    assert problems and all(p.startswith("dsra.") for p in problems)


def test_negative_control_a_wrong_oracle_in_one_module_fails_the_comparison():
    steps = pf.steps()
    ext = pf.external()

    def no_idc(inputs):
        return idc_oracle({**inputs, "idc_rate": 0.0})

    idc_oracle = next(st.module.oracle for st in steps if st.module.name == "idc")
    broken = [
        replace(st, module=replace(st.module, oracle=no_idc)) if st.module.name == "idc" else st
        for st in steps
    ]
    comp = template.compose(broken, ext, "negative control")
    problems = template.evaluate_and_compare(comp)
    assert any(p.startswith("idc.") for p in problems)


def test_a_live_scenario_flows_through_the_model_and_reconciles_to_the_table():
    ext = pf.external()
    ext.update(pf.scenario_points(ext, selector=2))
    comp = pf.build(ext)
    path = saved(comp)
    assert template.evaluate_and_compare(comp) == []
    assert read_zero_checks(path, "Summary", min_rows=30, out=lambda *_: None) == 0
    base = pf.external()
    assert comp.expected["returns"]["equity_npv"][0] != base["live_result"]
    assert comp.expected["returns"]["equity_npv"][0] == pytest.approx(ext["live_result"])


def test_the_scenario_check_reads_red_when_the_live_model_is_not_the_selected_scenario():
    ext = pf.external()
    ext["scenario_selector"] = (
        2.0  # the multipliers flow into the model, the table's live result still says base
    )
    comp = pf.build(ext)
    assert read_zero_checks(saved(comp), "Summary", min_rows=30, out=lambda *_: None) >= 1
