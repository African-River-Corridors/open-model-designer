"""M24: the project-finance (single SPV) template builds, agrees with the chained oracle and passes every gate."""

import os
import tempfile
from dataclasses import replace

import openpyxl
import pytest

from omd import acceptance, template
from omd.harness._eval import evaluate_cells
from omd.harness.audit_fast import audit_fast
from omd.harness.audit_hardcodes import audit_hardcodes
from omd.harness.audit_inputs import audit_inputs
from omd.harness.audit_offsheet import audit_offsheet
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
        gate_min_rows=1, shard=(i, INPUT_SHARDS), ignore_rows=comp.mirror_rows.values(), out=lambda *_: None,
    )  # fmt: skip
    assert audit.ok and not audit.inert


def test_gate_fast_audit_of_the_composed_book_has_only_the_modules_own_declared_breaches(built):
    """The composed book is audited by the same rule as each module's worked example: check rows are exempt from
    `CHECK_ROW_EXEMPT`, and a calculation-row breach must be one a module declares in `fast_declared`."""
    _ext, comp = built
    raw = audit_fast(saved(comp), first_col=4, units_col=2, out=lambda *_: None)
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


def test_the_scenario_check_reads_red_when_the_table_disagrees_with_the_live_model():
    """Negative control. The live result is picked from the table by the selector, so moving the selector cannot
    break it, and the scenarios module's own reconciliation (live less table) is then nil by construction. The guard
    is the template check that the picked result is the model's own equity NPV: a wrong table result must fail it."""
    ext = pf.external()
    ext["scenario_result__base"] += 50.0
    comp = pf.build(ext)
    lines = []
    read_zero_checks(saved(comp), "Summary", min_rows=30, out=lines.append)
    assert any("FAIL" in s and "is the model's equity NPV" in s for s in lines)


def test_gate_no_calculation_on_calcs_reads_another_sheet(built):
    """Every input is mirrored at the top of Calcs, and only the mirror reads the Inputs and Feed sheets."""
    _ext, comp = built
    assert len(comp.mirror_rows) == len(comp.ext_cells) + len(
        pf.PICKS
    )  # a pick is mirrored, not edited
    assert audit_offsheet(saved(comp), comp.calcs.ws.title, comp.mirror_rows.values()) == []


def test_gate_no_typed_number_outside_the_input_sheets(built):
    """Every output follows the inputs: the only typed numbers are on Inputs and Feed, bar declared module ones."""
    _ext, comp = built
    assert (
        audit_hardcodes(
            saved(comp), input_sheets=("Inputs", "Feed", "Stored"), declared=pf.HARDCODES_DECLARED
        )
        == []
    )


def test_the_key_figures_are_live_and_agree_with_the_oracle(built):
    _ext, comp = built
    path = saved(comp)
    vals = evaluate_cells(path, ("Key figures",))
    ws = comp.wb.sheet("Key figures")
    got = {
        ws.cell(row=r, column=2).value: vals.get(f"KEY FIGURES'!C{r}")
        for r in range(6, ws.max_row + 1)
        if isinstance(ws.cell(row=r, column=3).value, str)
    }
    e = comp.expected
    flags = _ext["repayment_flag"]
    assert got["Equity IRR"] == pytest.approx(e["returns"]["equity_xirr"][0])
    assert got["Minimum DSCR, repayment periods"] == pytest.approx(
        min(d for d, f in zip(e["cover_ratios"]["dscr"], flags) if f == 1)
    )
    assert got["Peak senior debt"] == pytest.approx(max(e["glue_book"]["senior_closing"]))
    assert got["Distributions to investors"] == pytest.approx(
        sum(e["distribution_waterfall"]["investor_distribution"])
    )
    assert all(isinstance(v, float) for v in got.values()), got


def test_a_change_to_an_unselected_scenario_is_caught_as_stale(built, tmp_path):
    """The scenarios module reconciles the selected scenario only. A change to another scenario's multiplier leaves
    that reconciliation at zero, so only the stored-results check can say the table is stale."""
    ext, comp = built
    path = saved(comp)
    wb = openpyxl.load_workbook(path)
    sheet, cell = comp.ext_cells["multiplier__price__downside"]
    wb[sheet][cell] = ext["multiplier__price__downside"] * 0.5
    moved = str(tmp_path / "moved.xlsx")
    wb.save(moved)
    lines = []
    read_zero_checks(moved, "Summary", min_rows=30, out=lambda s: lines.append(s))
    failing = [s for s in lines if s.lstrip().startswith("FAIL")]
    assert failing and all("Stored results" in s for s in failing)


def test_the_scenario_multipliers_are_a_grid_and_the_selector_keeps_every_check_at_zero(
    built, tmp_path
):
    """Pick the downside: the live model, the scenario table and every check still agree (the selector is not an
    input the stored results depend on)."""
    _ext, comp = built
    wb = openpyxl.load_workbook(saved(comp))
    sheet, cell = comp.ext_cells["scenario_selector"]
    labels = [wb[sheet].cell(row=r, column=1).value for r in range(1, wb[sheet].max_row + 1)]
    assert {"Price multiplier", "Volume multiplier", "Opex multiplier"} <= set(labels)
    wb[sheet][cell] = 2
    moved = str(tmp_path / "downside.xlsx")
    wb.save(moved)
    assert read_zero_checks(moved, "Summary", min_rows=30, out=lambda *_: None) == 0
