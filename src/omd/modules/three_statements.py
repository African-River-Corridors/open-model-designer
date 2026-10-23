"""Three statements: profit and loss, cash flow and balance sheet, with an articulation check.

Profit and loss:      EBITDA = revenue - operating cost;  EBIT = EBITDA - depreciation;
                      profit before tax = EBIT - interest;  net income = profit before tax - tax charge
Cash flow:            from operations = net income + depreciation - working capital movement
                                        + tax charge - tax paid  (the rise in tax payable)
                      from investing  = - capital additions
                      from financing  = debt drawn - debt repaid + equity contributed - dividends
                      cash, closing   = cash, opening + the three together
Balance sheet:        assets = cash + fixed assets (net book value) + working capital
                      liabilities and equity = debt + tax payable + share capital + retained earnings
                      tax payable, share capital and retained earnings roll forward from the flows here;
                      fixed assets, working capital and debt come from the modules that own them.

The balance difference (assets - liabilities and equity) is zero only if those modules agree with the
flows: a fixed-asset, working-capital or debt balance that does not follow its flows turns the check red.
Interest is the interest charged and paid in the period; accrued interest and deferred tax are out of scope.
"""

from __future__ import annotations

from ..module import BuildContext, Golden, Module, Port
from ._plan_module import build_plan, plan_checks

SERIES = (
    "revenue", "operating_cost", "depreciation", "interest", "tax_charge", "tax_paid", "capital_additions",
    "working_capital_movement", "debt_drawdown", "debt_repayment", "equity_contribution", "dividends",
    "fa_nbv_closing", "working_capital", "debt_closing",
)  # fmt: skip
OPENINGS = (
    "opening_cash", "opening_fixed_assets", "opening_working_capital", "opening_debt",
    "opening_tax_payable", "opening_share_capital", "opening_retained_earnings",
)  # fmt: skip
INPUTS = (
    *(Port(n, "USD", "series") for n in SERIES),
    *(Port(n, "USD", "scalar") for n in OPENINGS),
)
OUTPUTS = tuple(
    Port(n, "USD", "series")
    for n in (
        "ebitda", "ebit", "profit_before_tax", "net_income", "cash_from_operations", "cash_from_investing",
        "cash_from_financing", "net_cash_flow", "cash_closing", "tax_payable_closing", "share_capital_closing",
        "retained_earnings_closing", "total_assets", "total_liabilities_equity", "balance_difference",
    )
)  # fmt: skip
T = "Three statements"
KEYED = {
    "ebitda": "ebitda", "ebit": "ebit", "pbt": "profit_before_tax", "ni": "net_income",
    "cfo": "cash_from_operations", "cfi": "cash_from_investing", "cff": "cash_from_financing",
    "ncf": "net_cash_flow", "cash": "cash_closing", "tp": "tax_payable_closing",
    "sc": "share_capital_closing", "re": "retained_earnings_closing", "assets": "total_assets",
    "le": "total_liabilities_equity", "diff": "balance_difference",
}  # fmt: skip
PLAN = [
    # profit and loss
    ("link", "rev", "Revenue (USD)", "revenue"),
    ("link", "cost", "Operating cost (USD)", "operating_cost"),
    ("calc", "ebitda", "EBITDA (USD)", "{rev}-{cost}"),
    ("relink", "ebitda2", "EBITDA (USD)", "ebitda"),
    ("link", "dep", "Depreciation (USD)", "depreciation"),
    ("calc", "ebit", "EBIT (USD)", "{ebitda2}-{dep}"),
    ("relink", "ebit2", "EBIT (USD)", "ebit"),
    ("link", "int", "Interest (USD)", "interest"),
    ("calc", "pbt", "Profit before tax (USD)", "{ebit2}-{int}"),
    ("relink", "pbt2", "Profit before tax (USD)", "pbt"),
    ("link", "taxc", "Tax charge (USD)", "tax_charge"),
    ("calc", "ni", "Net income (USD)", "{pbt2}-{taxc}"),
    # cash flow
    ("relink", "ni2", "Net income (USD)", "ni"),
    ("link", "dep2", "Depreciation (USD)", "depreciation"),
    ("link", "wcm", "Working capital movement (USD)", "working_capital_movement"),
    ("link", "taxc2", "Tax charge (USD)", "tax_charge"),
    ("link", "taxp", "Tax paid (USD)", "tax_paid"),
    ("calc", "cfo", "Cash from operations (USD)", "{ni2}+{dep2}-{wcm}+{taxc2}-{taxp}"),
    ("link", "capex", "Capital additions (USD)", "capital_additions"),
    ("calc", "cfi", "Cash from investing (USD)", "0-{capex}"),
    ("link", "draw", "Debt drawn (USD)", "debt_drawdown"),
    ("link", "rep", "Debt repaid (USD)", "debt_repayment"),
    ("link", "eq", "Equity contributed (USD)", "equity_contribution"),
    ("link", "div", "Dividends paid (USD)", "dividends"),
    ("calc", "cff", "Cash from financing (USD)", "{draw}-{rep}+{eq}-{div}"),
    ("relink", "cfo2", "Cash from operations (USD)", "cfo"),
    ("relink", "cfi2", "Cash from investing (USD)", "cfi"),
    ("relink", "cff2", "Cash from financing (USD)", "cff"),
    ("calc", "ncf", "Net cash flow (USD)", "{cfo2}+{cfi2}+{cff2}"),
    ("lp", "cash_open", "Cash, opening (USD)", "cash_closing"),
    ("relink", "ncf2", "Net cash flow (USD)", "ncf"),
    ("calc", "cash", "Cash, closing (USD)", "{cash_open}+{ncf2}"),
    # balance sheet
    ("lp", "tp_open", "Tax payable, opening (USD)", "tax_payable_closing"),
    ("link", "taxc3", "Tax charge (USD)", "tax_charge"),
    ("link", "taxp2", "Tax paid (USD)", "tax_paid"),
    ("calc", "tp", "Tax payable, closing (USD)", "{tp_open}+{taxc3}-{taxp2}"),
    ("lp", "sc_open", "Share capital, opening (USD)", "share_capital_closing"),
    ("link", "eq2", "Equity contributed (USD)", "equity_contribution"),
    ("calc", "sc", "Share capital, closing (USD)", "{sc_open}+{eq2}"),
    ("lp", "re_open", "Retained earnings, opening (USD)", "retained_earnings_closing"),
    ("relink", "ni3", "Net income (USD)", "ni"),
    ("link", "div2", "Dividends paid (USD)", "dividends"),
    ("calc", "re", "Retained earnings, closing (USD)", "{re_open}+{ni3}-{div2}"),
    ("relink", "cash2", "Cash, closing (USD)", "cash"),
    ("link", "fa", "Fixed assets, net book value (USD)", "fa_nbv_closing"),
    ("link", "wc", "Working capital (USD)", "working_capital"),
    ("calc", "assets", "Total assets (USD)", "{cash2}+{fa}+{wc}"),
    ("link", "debt", "Debt, closing (USD)", "debt_closing"),
    ("relink", "tp2", "Tax payable, closing (USD)", "tp"),
    ("relink", "sc2", "Share capital, closing (USD)", "sc"),
    ("relink", "re2", "Retained earnings, closing (USD)", "re"),
    ("calc", "le", "Total liabilities and equity (USD)", "{debt}+{tp2}+{sc2}+{re2}"),
    ("relink", "assets2", "Total assets (USD)", "assets"),
    ("relink", "le2", "Total liabilities and equity (USD)", "le"),
    (
        "calc",
        "diff",
        "Balance difference: assets less liabilities and equity (USD)",
        "{assets2}-{le2}",
    ),
]


def _run(inputs):
    f = lambda k, i: float(inputs[k][i])  # noqa: E731
    o = {k: float(inputs[k]) for k in OPENINGS}
    cash, tp, sc, re_ = (
        o["opening_cash"],
        o["opening_tax_payable"],
        o["opening_share_capital"],
        o["opening_retained_earnings"],
    )
    V: dict[str, list[float]] = {name: [] for _k, name, _l, _s in PLAN}
    for i in range(len(inputs["revenue"])):
        rev, cost, dep, intr = (
            f("revenue", i),
            f("operating_cost", i),
            f("depreciation", i),
            f("interest", i),
        )
        taxc, taxp, capex, wcm = (
            f("tax_charge", i),
            f("tax_paid", i),
            f("capital_additions", i),
            f("working_capital_movement", i),
        )
        draw, rep, eq, div = (
            f("debt_drawdown", i),
            f("debt_repayment", i),
            f("equity_contribution", i),
            f("dividends", i),
        )
        fa, wc, debt = f("fa_nbv_closing", i), f("working_capital", i), f("debt_closing", i)
        ebitda = rev - cost
        ebit = ebitda - dep
        pbt = ebit - intr
        ni = pbt - taxc
        cfo = ni + dep - wcm + taxc - taxp
        cfi = 0 - capex
        cff = draw - rep + eq - div
        ncf = cfo + cfi + cff
        cash_new, tp_new, sc_new, re_new = cash + ncf, tp + taxc - taxp, sc + eq, re_ + ni - div
        assets = cash_new + fa + wc
        le = debt + tp_new + sc_new + re_new
        row = {"rev": rev, "cost": cost, "ebitda": ebitda, "ebitda2": ebitda, "dep": dep, "ebit": ebit, "ebit2": ebit,
               "int": intr, "pbt": pbt, "pbt2": pbt, "taxc": taxc, "ni": ni, "ni2": ni, "dep2": dep, "wcm": wcm,
               "taxc2": taxc, "taxp": taxp, "cfo": cfo, "capex": capex, "cfi": cfi, "draw": draw, "rep": rep,
               "eq": eq, "div": div, "cff": cff, "cfo2": cfo, "cfi2": cfi, "cff2": cff, "ncf": ncf,
               "cash_open": cash, "ncf2": ncf, "cash": cash_new, "tp_open": tp, "taxc3": taxc, "taxp2": taxp,
               "tp": tp_new, "sc_open": sc, "eq2": eq, "sc": sc_new, "re_open": re_, "ni3": ni, "div2": div,
               "re": re_new, "cash2": cash_new, "fa": fa, "wc": wc, "assets": assets, "debt": debt, "tp2": tp_new,
               "sc2": sc_new, "re2": re_new, "le": le, "assets2": assets, "le2": le, "diff": assets - le}  # fmt: skip
        cash, tp, sc, re_ = cash_new, tp_new, sc_new, re_new
        for k, v in row.items():
            V[k].append(v)
    return V


def oracle(inputs: dict) -> dict[str, list[float]]:
    V = _run(inputs)
    return {port: V[name] for name, port in KEYED.items()}


def build(ctx: BuildContext) -> None:
    build_plan(ctx, T, PLAN, _run(ctx.inputs), KEYED, {
        "cash_closing": "opening_cash", "tax_payable_closing": "opening_tax_payable",
        "share_capital_closing": "opening_share_capital", "retained_earnings_closing": "opening_retained_earnings",
    })  # fmt: skip


def checks(ctx: BuildContext) -> dict[str, str]:
    c = ctx.calcs
    r = c.rows()
    cols = list(c.workbook.period_cols)
    first = cols[0]
    src = {p.name: ctx.source(p.name) for p in INPUTS}
    S = lambda port, x: src[port].format(col=x.col) if "{col}" in src[port] else src[port]  # noqa: E731
    K = lambda port, x: f"{x.col}{r[ctx.key(port)]}"  # noqa: E731
    kr = lambda port: r[ctx.key(port)]  # noqa: E731
    zero = [0.0] * ctx.n

    def upto(
        port, x, through_prev=False
    ):  # cumulative sum of a series port, to this period or to the one before
        if through_prev and x.i == 1:
            return "0"
        end = cols[x.i - 2] if through_prev else x.col
        sheet, ref = src[port].split("!", 1)
        row = ref.removeprefix("{col}")
        return f"SUM({sheet}!${first}{row}:{end}{row})"

    def prev(
        port, x
    ):  # the previous period's closing of an output row, or the opening input in period 1
        opening = {"cash_closing": "opening_cash", "tax_payable_closing": "opening_tax_payable",
                   "share_capital_closing": "opening_share_capital", "retained_earnings_closing": "opening_retained_earnings"}  # fmt: skip
        return src[opening[port]] if x.i == 1 else f"{cols[x.i - 2]}{kr(port)}"

    absum = lambda parts: "=" + "+".join(f"ABS({p})" for p in parts)  # noqa: E731

    def ni(x):
        return f"({S('revenue', x)}-{S('operating_cost', x)}-{S('depreciation', x)}-{S('interest', x)}-{S('tax_charge', x)})"

    c.section("Checks")
    c.row("chk_pl", "  Check - the profit and loss re-derived from the ports (USD)",
          lambda x: absum([K("ebitda", x) + f"-({S('revenue', x)}-{S('operating_cost', x)})",
                           K("ebit", x) + f"-({S('revenue', x)}-{S('operating_cost', x)}-{S('depreciation', x)})",
                           K("profit_before_tax", x) + f"-({S('revenue', x)}-{S('operating_cost', x)}-{S('depreciation', x)}-{S('interest', x)})",
                           K("net_income", x) + "-" + ni(x)]), values=zero)  # fmt: skip
    c.row("chk_cf", "  Check - the cash flow statement re-derived from the ports (USD)",
          lambda x: absum([K("cash_from_operations", x) + f"-({ni(x)}+{S('depreciation', x)}-{S('working_capital_movement', x)}+{S('tax_charge', x)}-{S('tax_paid', x)})",
                           K("cash_from_investing", x) + f"+{S('capital_additions', x)}",
                           K("cash_from_financing", x) + f"-({S('debt_drawdown', x)}-{S('debt_repayment', x)}+{S('equity_contribution', x)}-{S('dividends', x)})",
                           K("net_cash_flow", x) + f"-({K('cash_from_operations', x)}+{K('cash_from_investing', x)}+{K('cash_from_financing', x)})"]), values=zero)  # fmt: skip
    c.row("chk_roll", "  Check - cash, tax payable, share capital and retained earnings re-derived from cumulative flows (USD)",
          lambda x: absum([
              K("cash_closing", x) + f"-({src['opening_cash']}+{upto('revenue', x)}-{upto('operating_cost', x)}-{upto('interest', x)}-{upto('tax_paid', x)}"
              f"-{upto('working_capital_movement', x)}-{upto('capital_additions', x)}+{upto('debt_drawdown', x)}-{upto('debt_repayment', x)}"
              f"+{upto('equity_contribution', x)}-{upto('dividends', x)})",
              K("tax_payable_closing", x) + f"-({src['opening_tax_payable']}+{upto('tax_charge', x)}-{upto('tax_paid', x)})",
              K("share_capital_closing", x) + f"-({src['opening_share_capital']}+{upto('equity_contribution', x)})",
              K("retained_earnings_closing", x) + f"-({src['opening_retained_earnings']}+{upto('revenue', x)}-{upto('operating_cost', x)}"
              f"-{upto('depreciation', x)}-{upto('interest', x)}-{upto('tax_charge', x)}-{upto('dividends', x)})"]), values=zero)  # fmt: skip
    c.row("chk_totals", "  Check - the totals and the balance difference re-derived from the ports (USD)",
          lambda x: absum([K("total_assets", x) + f"-({K('cash_closing', x)}+{S('fa_nbv_closing', x)}+{S('working_capital', x)})",
                           K("total_liabilities_equity", x) + f"-({S('debt_closing', x)}+{K('tax_payable_closing', x)}+{K('share_capital_closing', x)}+{K('retained_earnings_closing', x)})",
                           K("balance_difference", x) + f"-({K('total_assets', x)}-{K('total_liabilities_equity', x)})"]), values=zero)  # fmt: skip
    c.row("chk_balance", "  Check - the balance sheet balances (USD)",
          lambda x: f"=ABS({K('total_assets', x)}-{K('total_liabilities_equity', x)})", values=zero)  # fmt: skip
    label = plan_checks(ctx, T, PLAN, KEYED, lambda port, x: prev(port, x))
    return {
        "pl": "Check - the profit and loss re-derived",
        "cf": "Check - the cash flow statement re-derived",
        "roll": "Check - cash, tax payable, share capital and retained earnings re-derived",
        "totals": "Check - the totals and the balance difference re-derived",
        "balance": "Check - the balance sheet balances",
        "rows": label,
    }


def _case(openings, flows):
    """Inputs for a consistent case: the fixed-asset, working-capital and debt balances follow their flows."""
    inputs: dict = {**openings, **flows}
    fa, wc, debt = (
        float(openings["opening_fixed_assets"]),
        float(openings["opening_working_capital"]),
        float(openings["opening_debt"]),
    )
    fa_c, wc_c, debt_c = [], [], []
    for i in range(len(flows["revenue"])):
        fa += flows["capital_additions"][i] - flows["depreciation"][i]
        wc += flows["working_capital_movement"][i]
        debt += flows["debt_drawdown"][i] - flows["debt_repayment"][i]
        fa_c.append(fa)
        wc_c.append(wc)
        debt_c.append(debt)
    return {**inputs, "fa_nbv_closing": fa_c, "working_capital": wc_c, "debt_closing": debt_c}


_OPEN = {"opening_cash": 100.0, "opening_fixed_assets": 800.0, "opening_working_capital": 50.0, "opening_debt": 500.0,
         "opening_tax_payable": 10.0, "opening_share_capital": 300.0, "opening_retained_earnings": 140.0}  # fmt: skip
EXAMPLE = _case(_OPEN, {
    "revenue": [500.0, 650.0, 700.0, 720.0], "operating_cost": [250.0, 290.0, 300.0, 310.0],
    "depreciation": [70.0, 70.0, 70.0, 70.0], "interest": [45.0, 42.0, 38.0, 33.0],
    "tax_charge": [25.0, 50.0, 60.0, 65.0], "tax_paid": [10.0, 35.0, 55.0, 65.0],
    "capital_additions": [90.0, 20.0, 0.0, 0.0], "working_capital_movement": [15.0, 5.0, -5.0, 0.0],
    "debt_drawdown": [60.0, 0.0, 0.0, 0.0], "debt_repayment": [25.0, 45.0, 55.0, 60.0],
    "equity_contribution": [0.0, 0.0, 0.0, 0.0], "dividends": [0.0, 30.0, 60.0, 90.0],
})  # fmt: skip
CASE_1 = _case(
    {"opening_cash": 150.0, "opening_fixed_assets": 1000.0, "opening_working_capital": 80.0, "opening_debt": 600.0,
     "opening_tax_payable": 20.0, "opening_share_capital": 400.0, "opening_retained_earnings": 210.0},
    {"revenue": [800.0, 900.0, 1000.0, 1100.0], "operating_cost": [400.0, 430.0, 450.0, 470.0],
     "depreciation": [100.0, 100.0, 100.0, 100.0], "interest": [60.0, 52.0, 44.0, 36.0],
     "tax_charge": [48.0, 64.0, 80.0, 96.0], "tax_paid": [20.0, 56.0, 72.0, 88.0],
     "capital_additions": [200.0, 50.0, 0.0, 0.0], "working_capital_movement": [20.0, 10.0, 10.0, -5.0],
     "debt_drawdown": [100.0, 0.0, 0.0, 0.0], "debt_repayment": [40.0, 80.0, 80.0, 100.0],
     "equity_contribution": [0.0, 50.0, 0.0, 0.0], "dividends": [0.0, 60.0, 120.0, 160.0]},
)  # fmt: skip

#: the golden case: case 1 with two supplied balances mis-stated, so the balance check must fail (P2 debt, P3 fixed assets)
GOLDEN_INPUTS = {
    **CASE_1,
    "fa_nbv_closing": [1100.0, 1050.0, 960.0, 850.0],
    "debt_closing": [660.0, 590.0, 500.0, 400.0],
}

THREE_STATEMENTS = Module(
    name="three_statements",
    version="0.1.0",
    scope={
        "in": [
            "A profit and loss from revenue, operating cost, depreciation, interest and the tax charge",
            "A cash flow statement by the indirect method, with the tax payable movement",
            "A balance sheet: cash, fixed assets, working capital, debt, tax payable, share capital, retained earnings",
            "Balances for fixed assets, working capital and debt taken from the modules that own them, so the balance check can fail",
            "A balance difference row and a check that reads non-zero when the sheet does not balance",
        ],
        "out": [
            "Accrued interest, interest income on cash, deferred tax, and capitalised interest as a separate line (it goes in capital additions)",
            "VAT, minority interests, other comprehensive income and FX translation reserves",
            "Disposals and impairments of fixed assets",
            "Presentation formats (line order and subtotals beyond those listed)",
        ],
    },
    inputs=INPUTS,
    outputs=OUTPUTS,
    oracle=oracle,
    build=build,
    checks=checks,
    example=EXAMPLE,
    golden=Golden(
        inputs=GOLDEN_INPUTS,
        outputs={
            "ebitda": [400.0, 470.0, 550.0, 630.0],
            "ebit": [300.0, 370.0, 450.0, 530.0],
            "profit_before_tax": [240.0, 318.0, 406.0, 494.0],
            "net_income": [192.0, 254.0, 326.0, 398.0],
            "cash_from_operations": [300.0, 352.0, 424.0, 511.0],
            "cash_from_investing": [-200.0, -50.0, 0.0, 0.0],
            "cash_from_financing": [60.0, -90.0, -200.0, -260.0],
            "net_cash_flow": [160.0, 212.0, 224.0, 251.0],
            "cash_closing": [310.0, 522.0, 746.0, 997.0],
            "tax_payable_closing": [48.0, 56.0, 64.0, 72.0],
            "share_capital_closing": [400.0, 450.0, 450.0, 450.0],
            "retained_earnings_closing": [402.0, 596.0, 802.0, 1040.0],
            "total_assets": [1510.0, 1682.0, 1826.0, 1962.0],
            "total_liabilities_equity": [1510.0, 1692.0, 1816.0, 1962.0],
            "balance_difference": [0.0, -10.0, 10.0, 0.0],
        },
        source="Independent hand calculation by a reviewer agent that did not see the code (2026-10-23); two supplied balances are mis-stated on purpose so the balance difference is non-zero; working in docs/golden-cases/three_statements_2.answer.md",
        kind="hand-calculation",
    ),
)
MODULE = THREE_STATEMENTS
