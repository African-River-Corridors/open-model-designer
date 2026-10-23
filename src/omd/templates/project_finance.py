"""Project finance, single SPV: a starting model composed from the library modules.

Periods 1-2 are construction and periods 3-4 operations. The chain:

    take_or_pay -> revenue                                       (contracted minimum, delivered volume, shortfall payment)
    capex_funding -> idc -> fixed_assets and tax_pool_rb         (capital additions including capitalised interest)
    glue_pl -> tax_losses -> tax_engine                          (profit before tax, losses, tax charge and paid)
    working_capital, tax_engine -> cfads                         (cash flow available for debt service)
    debt_repay_linear -> cover_ratios, dsra, lockup              (debt service, balances, distribution gate)
    cfads, debt service, dsra, sub_loan -> cash_waterfall        (operating costs, senior service, reserve, sub service)
    cash_waterfall remainder x lockup gate -> distribution_waterfall   (hurdle, promote)
    all of the above -> three_statements                         (profit and loss, cash flow, balance sheet: balances)
    cfads, distributions -> returns                              (XIRR, NPV, payback); cfads -> fx_conversion

`glue_*` are small wiring modules (`_glue`): a port reads one row, so a feed such as profit before tax is a row of its
own, built and checked like any module's. Choices a reader should know:

- The senior debt modules start from the debt left at the end of construction, so the book debt is the construction
  debt (idc) in construction and the term debt after it (`glue_book`, switched by the two flags). Interest in
  construction is capitalised (idc), so the term module's interest counts only where the repayment flag is 1.
- Cash for the waterfall is CFADS plus operating cost; operating cost is tier 1. Distributable cash is the remainder
  times the lock-up gate. The sweep is sized on the remainder but not applied: no repayment module takes a prepayment.
- Sub-loan PIK interest is expensed and drawn as debt, so the statements carry interest in full and cash interest only.
- VAT and FX stand beside the statements (no VAT or translated line is in them).
- A scalar cannot be wired from a series, so the term debt's opening balance is an input; template checks read non-zero
  if it is not the construction debt, if the flags are not complements, if the books open with other debt or assets than
  the modules, or if the waterfall leaves a claim unpaid (the statements assume it pays every claim).
"""

from __future__ import annotations

from ..modules import (
    capex_funding,
    cash_sweep_percent,
    cash_waterfall,
    cfads,
    cover_ratios,
    debt_repay_linear,
    distribution_waterfall,
    dsra,
    fixed_assets,
    fx_conversion,
    idc,
    lockup,
    returns,
    sub_loan,
    take_or_pay,
    tax_engine,
    tax_losses,
    tax_pool_rb,
    three_statements,
    vat_account,
    working_capital,
)
from ..modules.scenarios import make_scenarios, run_points
from ..template import Composed, Step, chained_oracle, compose
from ._glue import glue

CONSTRUCTION_PERIODS = 2


GLUE_PL = glue(
    "glue_pl",
    {"revenue": "USD", "operating_cost": "USD", "depreciation": "USD", "interest": "USD", "repayment_flag": "count",
     "sub_interest": "USD", "tax_adjustments": "USD"},
    [("interest_senior_expensed", "interest*repayment_flag"),
     ("interest_total", "interest_senior_expensed+sub_interest"),
     ("profit_before_tax", "revenue-operating_cost-depreciation-interest_total"),
     ("taxable_pre_loss", "profit_before_tax+tax_adjustments")],
    {"revenue": [0.0, 0.0, 10.0, 12.0], "operating_cost": [0.0, 0.0, 4.0, 5.0], "depreciation": [0.0, 0.0, 1.0, 1.0],
     "interest": [1.0, 1.0, 2.0, 2.0], "repayment_flag": [0.0, 0.0, 1.0, 1.0], "sub_interest": [0.0, 0.0, 1.0, 1.0],
     "tax_adjustments": [0.0, 0.0, 1.0, 1.0]},
)  # fmt: skip
GLUE_CASH = glue(
    "glue_cash",
    {"cfads": "USD", "operating_cost": "USD", "debt_service": "USD", "repayment_flag": "count",
     "sub_interest_cash": "USD", "sub_repayment": "USD"},
    [("cash_receipts", "cfads+operating_cost"), ("senior_claim", "debt_service*repayment_flag"),
     ("sub_claim", "sub_interest_cash+sub_repayment")],
    {"cfads": [0.0, 0.0, 9.0, 9.0], "operating_cost": [0.0, 0.0, 4.0, 5.0], "debt_service": [1.0, 1.0, 3.0, 3.0],
     "repayment_flag": [0.0, 0.0, 1.0, 1.0], "sub_interest_cash": [0.0, 0.0, 1.0, 1.0], "sub_repayment": [0.0, 0.0, 0.0, 1.0]},
)  # fmt: skip
GLUE_DIST = glue(
    "glue_dist",
    {"cash_remainder": "USD", "distributions_permitted_flag": "count"},
    [("distributable_cash", "cash_remainder*distributions_permitted_flag")],
    {"cash_remainder": [0.0, 0.0, 5.0, -2.0], "distributions_permitted_flag": [1.0, 1.0, 1.0, 0.0]},
)  # fmt: skip
GLUE_BOOK = glue(
    "glue_book",
    {"investor_distribution": "USD", "sponsor_promote": "USD", "repayment_flag": "count", "construction_flag": "count",
     "term_debt_closing": "USD", "construction_debt_closing": "USD", "sub_closing": "USD", "debt_funded_capex": "USD",
     "idc_capitalised": "USD", "sub_drawdown": "USD", "sub_interest_pik": "USD", "debt_repayment": "USD",
     "sub_repayment": "USD"},
    [("dividends", "investor_distribution+sponsor_promote"),
     ("senior_closing", "repayment_flag*term_debt_closing+construction_flag*construction_debt_closing"),
     ("debt_closing_total", "senior_closing+sub_closing"),
     ("senior_drawdown", "construction_flag*(debt_funded_capex+idc_capitalised)"),
     ("debt_drawdown_total", "senior_drawdown+sub_drawdown+sub_interest_pik"),
     ("debt_repayment_total", "debt_repayment+sub_repayment")],
    {"investor_distribution": [0.0, 0.0, 1.0, 1.0], "sponsor_promote": [0.0, 0.0, 0.0, 1.0],
     "repayment_flag": [0.0, 0.0, 1.0, 1.0], "construction_flag": [1.0, 1.0, 0.0, 0.0],
     "term_debt_closing": [9.0, 9.0, 6.0, 3.0], "construction_debt_closing": [5.0, 9.0, 9.0, 9.0],
     "sub_closing": [0.0, 3.0, 3.0, 2.0], "debt_funded_capex": [4.0, 4.0, 0.0, 0.0], "idc_capitalised": [1.0, 0.0, 0.0, 0.0],
     "sub_drawdown": [0.0, 3.0, 0.0, 0.0], "sub_interest_pik": [0.0, 0.0, 0.0, 0.0],
     "debt_repayment": [0.0, 0.0, 3.0, 3.0], "sub_repayment": [0.0, 0.0, 0.0, 1.0]},
)  # fmt: skip
GLUE_RET = glue(
    "glue_ret",
    {"cfads": "USD", "capex": "USD", "investor_distribution": "USD", "equity_contribution": "USD"},
    [("project_cash_flow", "cfads-capex"), ("equity_cash_flow", "investor_distribution-equity_contribution")],
    {"cfads": [0.0, 0.0, 9.0, 9.0], "capex": [5.0, 5.0, 0.0, 0.0], "investor_distribution": [0.0, 0.0, 6.0, 6.0],
     "equity_contribution": [2.0, 2.0, 0.0, 0.0]},
)  # fmt: skip


DRIVERS = ("price", "volume", "opex")
SCENARIO_NAMES = ("base", "downside", "upside")
MULTIPLIERS = {
    "base": {"price": 1.0, "volume": 1.0, "opex": 1.0},
    "downside": {"price": 0.9, "volume": 0.85, "opex": 1.1},
    "upside": {"price": 1.05, "volume": 1.1, "opex": 0.95},
}
SENSITIVITY_STEP = 0.1
SCENARIOS = make_scenarios(
    DRIVERS, SCENARIO_NAMES,
    example=run_points(
        lambda i: {"r": 100.0 * i["price"] * i["volume"] - 40.0 * i["opex"]},
        {"price": 1.0, "volume": 1.0, "opex": 1.0},
        lambda base, m: {k: base[k] * m.get(k, 1.0) for k in base},
        DRIVERS, SCENARIO_NAMES, MULTIPLIERS, SENSITIVITY_STEP, lambda o: o["r"], 2,
    ),
    golden=None,
)  # fmt: skip
GLUE_DRIVERS = glue(
    "glue_drivers",
    {"unit_price": "USD:scalar", "delivered_volume": "count", "operating_cost": "USD",
     "live_multiplier__price": "ratio", "live_multiplier__volume": "ratio", "live_multiplier__opex": "ratio"},
    [("price_live", "unit_price*live_multiplier__price"), ("volume_live", "delivered_volume*live_multiplier__volume"),
     ("opex_live", "operating_cost*live_multiplier__opex")],
    {"unit_price": 2.0, "delivered_volume": [1.0, 2.0, 3.0, 4.0], "operating_cost": [1.0, 1.0, 1.0, 1.0],
     "live_multiplier__price": [1.0] * 4, "live_multiplier__volume": [0.9] * 4, "live_multiplier__opex": [1.1] * 4},
)  # fmt: skip


def steps(with_scenarios: bool = True) -> list[Step]:
    """`with_scenarios=False` is the model the scenarios are run on: the drivers read their base inputs directly."""
    OPEX, PRICE, VOLUME = (
        ("glue_drivers.opex_live", "glue_drivers.price_live", "glue_drivers.volume_live")
        if with_scenarios
        else ("ext:operating_cost", "ext:unit_price", "ext:delivered_volume")
    )
    tail = [
        Step(SCENARIOS, {p.name: f"ext:{p.name}" for p in SCENARIOS.inputs}),
        Step(GLUE_DRIVERS, {
            "unit_price": "ext:unit_price", "delivered_volume": "ext:delivered_volume",
            "operating_cost": "ext:operating_cost",
            "live_multiplier__price": "scenarios.live_multiplier__price",
            "live_multiplier__volume": "scenarios.live_multiplier__volume",
            "live_multiplier__opex": "scenarios.live_multiplier__opex"}),
    ] if with_scenarios else []  # fmt: skip
    return tail + [
        Step(take_or_pay.MODULE, {
            "contracted_minimum": "ext:contracted_minimum", "delivered_volume": VOLUME,
            "unit_price": PRICE, "shortfall_payment_share": "ext:shortfall_payment_share"}),
        Step(capex_funding.MODULE, {
            "total_capex": "ext:total_capex", "spend_profile": "ext:spend_profile",
            "development_cost": "ext:development_cost", "debt_share": "ext:debt_share"}),
        Step(idc.MODULE, {
            "debt_funded_capex": "capex_funding.debt_funded_capex", "capital_additions": "capex_funding.capital_additions",
            "idc_rate": "ext:idc_rate", "idc_weight": "ext:idc_weight", "opening_debt": "ext:construction_opening_debt"}),
        Step(fixed_assets.MODULE, {
            "capital_additions": "idc.capital_additions_incl_idc", "use_fraction": "ext:use_fraction",
            "useful_life": "ext:useful_life", "opening_gross": "ext:opening_gross",
            "opening_accum_depreciation": "ext:opening_accum_depreciation"}),
        Step(tax_pool_rb.MODULE, {
            "capital_additions": "idc.capital_additions_incl_idc", "use_fraction": "ext:use_fraction",
            "allowance_rate": "ext:allowance_rate", "opening_wdv": "ext:opening_wdv"}),
        Step(debt_repay_linear.MODULE, {
            "repayment_flag": "ext:repayment_flag", "interest_rate": "ext:term_interest_rate",
            "opening_debt": "ext:term_opening_debt"}),
        Step(sub_loan.MODULE, {
            "sub_drawdown": "ext:sub_drawdown", "sub_repayment_request": "ext:sub_repayment_request",
            "sub_interest_rate": "ext:sub_interest_rate", "sub_pik_share": "ext:sub_pik_share",
            "opening_sub_loan": "ext:opening_sub_loan"}),
        Step(GLUE_PL, {
            "revenue": "take_or_pay.revenue", "operating_cost": OPEX,
            "depreciation": "fixed_assets.depreciation", "interest": "debt_repay_linear.interest",
            "repayment_flag": "ext:repayment_flag", "sub_interest": "sub_loan.sub_interest",
            "tax_adjustments": "ext:tax_adjustments"}),
        Step(tax_losses.MODULE, {
            "taxable_profit_pre_loss": "glue_pl.taxable_pre_loss", "loss_life": "ext:loss_life",
            "opening_losses": "ext:opening_losses"}),
        Step(tax_engine.MODULE, {
            "profit_before_tax": "glue_pl.profit_before_tax", "tax_adjustments": "ext:tax_adjustments",
            "losses_relieved": "tax_losses.tax_loss_used", "minimum_tax": "ext:minimum_tax",
            "tax_rate": "ext:tax_rate", "instalment_share": "ext:instalment_share",
            "opening_tax_payable": "ext:opening_tax_payable"}),
        Step(working_capital.MODULE, {
            "revenue": "take_or_pay.revenue", "operating_cost": OPEX,
            "receivable_days": "ext:receivable_days", "payable_days": "ext:payable_days",
            "cash_buffer_days": "ext:cash_buffer_days", "days_in_period": "ext:days_in_period",
            "opening_working_capital": "ext:opening_working_capital"}),
        Step(cfads.MODULE, {
            "revenue": "take_or_pay.revenue", "operating_cost": OPEX,
            "working_capital_movement": "working_capital.working_capital_movement",
            "tax_paid": "tax_engine.tax_paid"}),
        Step(cover_ratios.MODULE, {
            "cfads": "cfads.cfads", "debt_service": "debt_repay_linear.debt_service",
            "debt_closing": "debt_repay_linear.debt_closing", "loan_life_flag": "ext:repayment_flag",
            "discount_rate": "ext:discount_rate", "opening_debt": "ext:term_opening_debt"}),
        Step(dsra.MODULE, {
            "debt_service": "debt_repay_linear.debt_service", "cash_available_for_dsra": "ext:cash_available_for_dsra",
            "dsra_funding_gate": "ext:dsra_funding_gate", "opening_dsra": "ext:opening_dsra"}),
        Step(lockup.MODULE, {
            "dscr": "cover_ratios.dscr", "debt_outstanding_flag": "ext:repayment_flag",
            "lockup_dscr": "ext:lockup_dscr", "default_dscr": "ext:default_dscr"}),
        Step(GLUE_CASH, {
            "cfads": "cfads.cfads", "operating_cost": OPEX,
            "debt_service": "debt_repay_linear.debt_service", "repayment_flag": "ext:repayment_flag",
            "sub_interest_cash": "sub_loan.sub_interest_cash", "sub_repayment": "sub_loan.sub_repayment"}),
        Step(cash_waterfall.MODULE, {
            "cash_available": "glue_cash.cash_receipts", "claim_operating_costs": OPEX,
            "claim_senior_service": "glue_cash.senior_claim", "claim_reserve_top_up": "dsra.dsra_transfer_in",
            "claim_sub_service": "glue_cash.sub_claim"}),
        Step(cash_sweep_percent.MODULE, {
            "cash_available_for_sweep": "cash_waterfall.cash_remainder",
            "debt_before_sweep": "debt_repay_linear.debt_closing", "sweep_flag": "ext:repayment_flag",
            "sweep_percent": "ext:sweep_percent"}),
        Step(GLUE_DIST, {
            "cash_remainder": "cash_waterfall.cash_remainder",
            "distributions_permitted_flag": "lockup.distributions_permitted_flag"}),
        Step(distribution_waterfall.MODULE, {
            "distributable_cash": "glue_dist.distributable_cash", "equity_contribution": "capex_funding.equity_contribution",
            "hurdle_rate": "ext:hurdle_rate", "period_years": "ext:period_years",
            "promote_share": "ext:promote_share", "opening_hurdle_balance": "ext:opening_hurdle_balance"}),
        Step(GLUE_BOOK, {
            "investor_distribution": "distribution_waterfall.investor_distribution",
            "sponsor_promote": "distribution_waterfall.sponsor_promote", "repayment_flag": "ext:repayment_flag",
            "construction_flag": "ext:construction_flag", "term_debt_closing": "debt_repay_linear.debt_closing",
            "construction_debt_closing": "idc.debt_closing", "sub_closing": "sub_loan.sub_closing",
            "debt_funded_capex": "capex_funding.debt_funded_capex", "idc_capitalised": "idc.idc_capitalised",
            "sub_drawdown": "ext:sub_drawdown", "sub_interest_pik": "sub_loan.sub_interest_pik",
            "debt_repayment": "debt_repay_linear.debt_repayment", "sub_repayment": "sub_loan.sub_repayment"}),
        Step(three_statements.MODULE, {
            "revenue": "take_or_pay.revenue", "operating_cost": OPEX,
            "depreciation": "fixed_assets.depreciation", "interest": "glue_pl.interest_total",
            "tax_charge": "tax_engine.tax_charge", "tax_paid": "tax_engine.tax_paid",
            "capital_additions": "idc.capital_additions_incl_idc",
            "working_capital_movement": "working_capital.working_capital_movement",
            "debt_drawdown": "glue_book.debt_drawdown_total", "debt_repayment": "glue_book.debt_repayment_total",
            "equity_contribution": "capex_funding.equity_contribution", "dividends": "glue_book.dividends",
            "fa_nbv_closing": "fixed_assets.fa_nbv_closing", "working_capital": "working_capital.working_capital",
            "debt_closing": "glue_book.debt_closing_total", "opening_cash": "ext:opening_cash",
            "opening_fixed_assets": "ext:opening_fixed_assets", "opening_working_capital": "ext:opening_working_capital",
            "opening_debt": "ext:opening_debt_total", "opening_tax_payable": "ext:opening_tax_payable",
            "opening_share_capital": "ext:opening_share_capital",
            "opening_retained_earnings": "ext:opening_retained_earnings"}),
        Step(GLUE_RET, {
            "cfads": "cfads.cfads", "capex": "capex_funding.capital_additions",
            "investor_distribution": "distribution_waterfall.investor_distribution",
            "equity_contribution": "capex_funding.equity_contribution"}),
        Step(returns.MODULE, {
            "project_cash_flow": "glue_ret.project_cash_flow", "equity_cash_flow": "glue_ret.equity_cash_flow",
            "flow_dates": "ext:flow_dates", "project_discount_rate": "ext:discount_rate",
            "equity_discount_rate": "ext:equity_discount_rate", "days_per_year": "ext:days_per_year"}),
        Step(fx_conversion.MODULE, {
            "fx_start_rate": "ext:fx_start_rate", "fx_depreciation": "ext:fx_depreciation",
            "flow_local": "cfads.cfads", "opening_balance_local": "ext:opening_fx_balance"}),
        Step(vat_account.MODULE, {
            "vat_input": "ext:vat_input", "vat_output": "ext:vat_output",
            "opening_vat_receivable": "ext:opening_vat_receivable", "settle_share": "ext:settle_share",
            "write_off_at_end": "ext:write_off_at_end"}),
    ]  # fmt: skip


BASE = {
    "total_capex": 1000.0, "spend_profile": [0.5, 0.5, 0.0, 0.0], "development_cost": [20.0, 0.0, 0.0, 0.0],
    "debt_share": 0.7, "idc_rate": 0.02, "idc_weight": 0.5, "construction_opening_debt": 0.0,
    "use_fraction": [0.0, 0.0, 1.0, 1.0], "useful_life": 10.0, "opening_gross": 0.0,
    "opening_accum_depreciation": 0.0, "allowance_rate": 0.2, "opening_wdv": 0.0,
    "repayment_flag": [0.0, 0.0, 1.0, 1.0], "term_interest_rate": 0.05,
    "contracted_minimum": [0.0, 0.0, 70.0, 75.0], "delivered_volume": [0.0, 0.0, 68.0, 78.0], "unit_price": 20.0,
    "shortfall_payment_share": 0.8, "construction_flag": [1.0, 1.0, 0.0, 0.0],
    "flow_dates": [0.0, 365.0, 730.0, 1095.0], "days_per_year": 365.0, "equity_discount_rate": 0.12,
    "fx_start_rate": 0.1, "fx_depreciation": [0.05, 0.05, 0.03, 0.0], "opening_fx_balance": 0.0,
    "opening_cash": 0.0, "opening_share_capital": 0.0, "opening_retained_earnings": 0.0,
    "operating_cost": [0.0, 0.0, 200.0, 220.0],
    "receivable_days": 30.0, "payable_days": 45.0, "cash_buffer_days": 10.0, "days_in_period": 90.0,
    "opening_working_capital": 0.0,
    "hurdle_rate": 0.1, "period_years": 1.0,
    "promote_share": 0.2, "opening_hurdle_balance": 0.0,
    "loss_life": 3.0, "opening_losses": 0.0,
    "tax_adjustments": [0.0, 0.0, 10.0, 10.0],
    "minimum_tax": [0.0, 0.0, 8.0, 12.0], "tax_rate": 0.25, "instalment_share": 0.5, "opening_tax_payable": 0.0,
    "sweep_percent": 0.5,
    "sub_drawdown": [0.0, 300.0, 0.0, 0.0], "sub_repayment_request": [0.0, 0.0, 0.0, 100.0],
    "sub_interest_rate": 0.08, "sub_pik_share": 0.5, "opening_sub_loan": 0.0,
    "vat_input": [40.0, 40.0, 5.0, 5.0], "vat_output": [0.0, 0.0, 90.0, 100.0],
    "opening_vat_receivable": 0.0, "settle_share": 0.5, "write_off_at_end": 0.0,
    "lockup_dscr": 1.2, "default_dscr": 1.1, "discount_rate": 0.06,
    "cash_available_for_dsra": [0.0, 0.0, 80.0, 80.0], "dsra_funding_gate": [0.0, 0.0, 1.0, 1.0],
    "opening_dsra": 0.0,
}  # fmt: skip


def external(**overrides) -> dict:
    """The template's inputs. Two are derived: the term debt opens at the construction debt left after construction,
    and the books open with the debt and fixed assets the modules open with (a template check reads them)."""
    ext = {**BASE, **overrides}
    if "term_opening_debt" not in overrides:
        out = chained_oracle(
            [
                st
                for st in steps(with_scenarios=False)
                if st.module.name in ("take_or_pay", "capex_funding", "idc")
            ],
            ext,
        )
        ext["term_opening_debt"] = out["idc"]["debt_closing"][CONSTRUCTION_PERIODS - 1]
    ext.setdefault("opening_debt_total", ext["construction_opening_debt"] + ext["opening_sub_loan"])
    ext.setdefault("opening_fixed_assets", ext["opening_gross"] - ext["opening_accum_depreciation"])
    if "scenario_selector" not in overrides:
        ext.update(scenario_points(ext))
    return ext


def scenario_points(ext: dict, selector: int = 1) -> dict:
    """The scenarios module's inputs: the model's oracle run once per scenario and per driver up and down, the result
    tracked being the equity NPV. The drivers are the unit price, the delivered volume and the operating cost."""
    model = [st for st in steps(with_scenarios=False)]

    def apply(base: dict, m: dict) -> dict:
        return {
            **base,
            "unit_price": base["unit_price"] * m.get("price", 1.0),
            "delivered_volume": [v * m.get("volume", 1.0) for v in base["delivered_volume"]],
            "operating_cost": [v * m.get("opex", 1.0) for v in base["operating_cost"]],
        }

    return run_points(
        lambda inputs: chained_oracle(model, inputs), ext, apply, DRIVERS, SCENARIO_NAMES, MULTIPLIERS,
        SENSITIVITY_STEP, lambda out: out["returns"]["equity_npv"][0], selector,
    )  # fmt: skip


def build(ext: dict | None = None) -> Composed:
    ext = external() if ext is None else ext

    def src(comp: Composed, module: str, port: str, col: str) -> str:
        return comp.ctxs[module].source(port).format(col=col)

    def construction_debt_is_term_opening(comp: Composed, col: str) -> str:
        last = comp.wb.period_cols[CONSTRUCTION_PERIODS - 1]
        row = comp.calcs.rows()["idc.debt_closing"]
        scalar = comp.ctxs["debt_repay_linear"].source("opening_debt")
        return f"ABS({scalar}-{comp.calcs.ws.title}!${last}${row})"

    def flags_are_complements(comp: Composed, col: str) -> str:
        return (
            f"ABS({src(comp, 'debt_repay_linear', 'repayment_flag', col)}"
            f"+{src(comp, 'glue_book', 'construction_flag', col)}-1)"
        )

    def books_open_with_the_modules_debt(comp: Composed, col: str) -> str:
        return (
            f"ABS({src(comp, 'three_statements', 'opening_debt', col)}"
            f"-{src(comp, 'idc', 'opening_debt', col)}-{src(comp, 'sub_loan', 'opening_sub_loan', col)})"
        )

    def books_open_with_the_modules_assets(comp: Composed, col: str) -> str:
        return (
            f"ABS({src(comp, 'three_statements', 'opening_fixed_assets', col)}"
            f"-{src(comp, 'fixed_assets', 'opening_gross', col)}+{src(comp, 'fixed_assets', 'opening_accum_depreciation', col)})"
        )

    def live_result_is_the_models(comp: Composed, col: str) -> str:
        row = comp.calcs.rows()["returns.equity_npv"]
        return f"ABS({src(comp, 'scenarios', 'live_result', col)}-{comp.calcs.ws.title}!{col}{row})"

    def every_claim_is_paid(comp: Composed, col: str) -> str:
        rows = comp.calcs.rows()
        sheet = comp.calcs.ws.title
        tiers = ("operating_costs", "senior_service", "reserve_top_up", "sub_service")
        return "+".join(f"ABS({sheet}!{col}{rows[f'cash_waterfall.unpaid_{t}']})" for t in tiers)

    return compose(
        steps(), ext, "Project finance (single SPV)",
        link_checks=[
            ("Check - term debt opens at the construction debt left at the end of construction",
             construction_debt_is_term_opening),
            ("Check - the repayment flag and the construction flag are complements", flags_are_complements),
            ("Check - the books open with the senior and subordinated debt the modules open with",
             books_open_with_the_modules_debt),
            ("Check - the books open with the fixed assets the fixed-asset module opens with",
             books_open_with_the_modules_assets),
            ("Check - the live result the scenarios reconcile is the model's equity NPV", live_result_is_the_models),
            ("Check - the cash waterfall pays every claim (the statements assume it does)", every_claim_is_paid),
        ],
    )  # fmt: skip
