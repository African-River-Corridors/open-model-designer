"""Standard line names. A module's ports wire to these by default; a model overrides only the
unusual wiring (two shippers, three sites). Each line has a dimension that a port's unit must match.
"""

from __future__ import annotations

import re

#: line name -> dimension
STANDARD_LINES: dict[str, str] = {
    "revenue": "currency",
    "operating_cost": "currency",
    "capital_additions": "currency",
    "depreciation": "currency",
    "interest": "currency",
    "tax_paid": "currency",
    "net_income": "currency",
    "cfads": "currency",
    "debt_service": "currency",
    "debt_opening": "currency",
    "debt_drawdown": "currency",
    "debt_repayment": "currency",
    "debt_closing": "currency",
    "cash_opening": "currency",
    "cash_closing": "currency",
    "equity_contribution": "currency",
    "dividends": "currency",
    "vat_output": "currency",
    "vat_input": "currency",
    "working_capital": "currency",
}

_CURRENCY = re.compile(r"^[A-Z]{3}$")
_UNIT = re.compile(r"^[A-Za-z%][A-Za-z0-9%^.*/ ()-]*$")
RATIOS = {"ratio", "%", "ratio/year", "ratio/period"}
COUNTS = {"count", "units", "periods"}


def valid_unit(unit: object) -> bool:
    return isinstance(unit, str) and bool(unit.strip()) and bool(_UNIT.match(unit.strip()))


def dimension_of(unit: str) -> str:
    """currency (a three-letter code), ratio, count, or other."""
    u = unit.strip()
    if _CURRENCY.match(u):
        return "currency"
    if u in RATIOS:
        return "ratio"
    if u in COUNTS:
        return "count"
    return "other"
