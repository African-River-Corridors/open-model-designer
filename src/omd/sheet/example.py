"""A self-contained synthetic reference model — proof that the builder is domain-agnostic.

This is a made-up 4-month "widget workshop" cash model (NOT real accounts, no confidential
data). It exercises every part of the builder — shaded Inputs, a SUMIFS source Table, Calcs
lines with per-period formulas + known ``values``, the ``roll`` roll-forward helper, and an
IB-style Statement — and ships a Python source-of-truth so :func:`omd.sheet.verify.verify`
can confirm the live formulas reproduce it. If this passes on CI, the engine is generic.
"""

from __future__ import annotations

from .verify import verify
from .workbook import Calcs, Workbook

PERIODS = ["Jan", "Feb", "Mar", "Apr"]

# --- synthetic ledger: signed amounts; kinds sale / cost / draw --------------------------------
LEDGER = [
    # month, kind, amount
    ("Jan", "sale", 1200.00),
    ("Jan", "sale", 800.50),
    ("Jan", "cost", -300.00),
    ("Jan", "draw", 5000.00),
    ("Feb", "sale", 1500.00),
    ("Feb", "cost", -450.75),
    ("Mar", "sale", 2000.00),
    ("Mar", "cost", -600.00),
    ("Mar", "draw", 2500.00),
    ("Apr", "sale", 1750.25),
    ("Apr", "cost", -500.00),
]

CASH_OPEN = 5000.0
LOAN_OPEN = 10000.0


def source_of_truth() -> dict[str, list[float]]:
    """Compute the model in plain Python — the reference the workbook formulas must reproduce."""
    rev = [sum(a for m, k, a in LEDGER if m == p and k == "sale") for p in PERIODS]
    cost = [sum(a for m, k, a in LEDGER if m == p and k == "cost") for p in PERIODS]
    draw = [sum(a for m, k, a in LEDGER if m == p and k == "draw") for p in PERIODS]
    profit = [rev[i] + cost[i] for i in range(len(PERIODS))]

    cash, loan = [], []
    c, ln = CASH_OPEN, LOAN_OPEN
    for i in range(len(PERIODS)):
        c += profit[i] + draw[i]
        ln += draw[i]
        cash.append(c)
        loan.append(ln)
    return {
        "rev": rev,
        "cost": cost,
        "draw": draw,
        "profit": profit,
        "cash": cash,
        "loan": loan,
    }


def build_reference(path: str, style=None) -> tuple[Workbook, Calcs, dict[str, list[float]]]:
    """Build the reference workbook at ``path`` in ``style``; return (workbook, calcs, source-of-truth)."""
    sot = source_of_truth()
    wb = Workbook(
        "Widget Workshop — cash model (synthetic)",
        PERIODS,
        opening=True,
        subtitle="Synthetic demonstration model — not real accounts.",
        style=style,
    )
    ins = wb.inputs(
        "Opening balances",
        {
            "cash_open": ("Opening cash", CASH_OPEN),
            "loan_open": ("Opening loan", LOAN_OPEN),
        },
    )
    led = wb.table(
        "Ledger", ["month", "kind", "amount"], LEDGER, title="Ledger — synthetic transactions"
    )

    calc = wb.calcs()
    calc.section("Flows (SUMIFS from Ledger)")
    calc.row(
        "rev",
        "  Revenue",
        lambda c: c.sumifs(
            led.col("amount"), f'{led.col("kind")},"sale"', f"{led.col('month')},{c.critcell}"
        ),
        values=sot["rev"],
    )
    calc.row(
        "cost",
        "  Costs",
        lambda c: c.sumifs(
            led.col("amount"), f'{led.col("kind")},"cost"', f"{led.col('month')},{c.critcell}"
        ),
        values=sot["cost"],
    )
    calc.row(
        "draw",
        "  Loan drawdowns",
        lambda c: c.sumifs(
            led.col("amount"), f'{led.col("kind")},"draw"', f"{led.col('month')},{c.critcell}"
        ),
        values=sot["draw"],
    )
    calc.section("Profit & balances")
    calc.row(
        "profit", "  Profit", lambda c: f"={c.here('rev')}+{c.here('cost')}", values=sot["profit"]
    )
    calc.roll(
        "cash", "  Cash", opening=f"={ins['cash_open']}", add=["profit", "draw"], values=sot["cash"]
    )
    calc.roll(
        "loan", "  Loan balance", opening=f"={ins['loan_open']}", add=["draw"], values=sot["loan"]
    )

    wb.statement(
        "Accounts",
        [
            (
                "Profit & Loss",
                [
                    ("Revenue", "rev"),
                    ("Costs", "cost"),
                    ("Profit", "profit", {"grand": True}),
                ],
            ),
            (
                "Balances",
                [
                    ("Cash", "cash"),
                    ("Loan balance", "loan", {"total": True}),
                ],
            ),
        ],
        title="Widget Workshop",
        subtitle="Management accounts (synthetic) · demo currency",
    )
    wb.autosize()
    wb.save(path)
    return wb, calc, sot


def verify_reference(path: str) -> None:
    """Build + verify the reference model end-to-end (raises on any drift)."""
    _wb, calc, sot = build_reference(path)
    verify(path, calc, sot, tol=0.01)


__all__ = ["PERIODS", "build_reference", "source_of_truth", "verify_reference"]
